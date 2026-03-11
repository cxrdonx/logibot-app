import boto3
import json
import os
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr

# --- CONFIGURACIÓN ---
TABLE_NAME = os.environ.get('TABLE_NAME', 'TarifasLogistica')
REGION = os.environ.get('REGION', 'us-east-1')
# Verifica el ID exacto de Nova Pro en tu consola de Bedrock
MODEL_ID = os.environ.get('MODEL_ID', 'amazon.nova-pro-v1:0') 

dynamodb = boto3.resource('dynamodb', region_name=REGION, aws_access_key_id='AKIAZBPHMNMQ3F6IU76U', aws_secret_access_key='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')

table = dynamodb.Table(TABLE_NAME)
bedrock = boto3.client('bedrock-runtime', region_name=REGION)

# --- CLASE AUXILIAR PARA JSON ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def invoke_nova_pro(system_prompt, user_message):
    """
    Función genérica para invocar a Amazon Nova Pro usando la API Converse (o invoke_model estándar).
    Aquí usamos la estructura de payload típica para modelos Nova.
    """
    payload = {
        "system": [{"text": system_prompt}],
        "messages": [
            {
                "role": "user",
                "content": [{"text": user_message}]
            }
        ],
        "inferenceConfig": {
            "max_new_tokens": 1000,
            "temperature": 0.1, # Bajo para precisión técnica
            "top_p": 0.9
        }
    }

    try:
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json"
        )
        response_body = json.loads(response.get("body").read())
        # Ajustar según la estructura de respuesta exacta de Nova:
        return response_body['output']['message']['content'][0]['text']
    except Exception as e:
        print(f"Error invocando Bedrock: {e}")
        raise e

def paso_1_generar_query(pregunta_usuario):
    """
    Usa Nova Pro para decidir qué índice GSI usar y generar los parámetros.
    """
    schema_info = """
    ESTRUCTURA DE TABLA DYNAMODB ('TarifasLogistica'):
    - Partition Key: id (String)
    - Atributos: origen (String), destino (String), proveedor (String), dias_libres (Number), estadia (Number).
    - Atributo Complejo: 'rango_base_precios' es una LISTA de MAPAS [{'min_kg', 'max_kg', 'costo', 'concepto'}].
    - Atributos Fijos: tramite_aduana_cominter, custodio_comsi, etc.

    ÍNDICES SECUNDARIOS GLOBALES (GSIs) DISPONIBLES:
    1. IndexName: 'RutaIndex' -> PK: 'origen', SK: 'destino'. (USAR SIEMPRE que la pregunta tenga Origen y Destino).
    2. IndexName: 'OrigenIndex' -> PK: 'origen'.
    3. IndexName: 'DestinoIndex' -> PK: 'destino'.
    4. IndexName: 'ProveedorIndex' -> PK: 'proveedor'.
    """

    system_prompt = f"""
    Eres un Arquitecto de Bases de Datos DynamoDB experto. Tu objetivo es traducir lenguaje natural a parámetros de consulta JSON para Boto3.
    
    {schema_info}
    
    INSTRUCCIONES:
    1. Analiza la pregunta del usuario.
    2. Selecciona la estrategia MÁS eficiente (Query sobre Scan siempre que sea posible).
    3. Si el usuario menciona Origen Y Destino, DEBES usar 'RutaIndex'.
    4. Devuelve UNICAMENTE un objeto JSON válido con las claves necesarias para ejecutar `table.query()` o `table.scan()`.
    5. NO incluyas explicaciones, solo el JSON.
    
    EJEMPLO DE SALIDA (Query):
    {{
        "operation": "query",
        "IndexName": "RutaIndex",
        "KeyConditionExpression": "origen = :o AND destino = :d",
        "ExpressionAttributeValues": {{":o": "Puerto Quetzal", ":d": "Mixco"}}
    }}
    
    EJEMPLO DE SALIDA (Scan - solo si no hay criterios indexados):
    {{
        "operation": "scan",
        "FilterExpression": "contains(proveedor, :p)",
        "ExpressionAttributeValues": {{":p": "Nixon"}}
    }}
    """
    
    respuesta_llm = invoke_nova_pro(system_prompt, pregunta_usuario)
    
    # Limpieza básica por si el modelo devuelve bloques de código markdown
    clean_json = respuesta_llm.replace("```json", "").replace("```", "").strip()
    return json.loads(clean_json)

def paso_2_ejecutar_dynamo(params):
    """
    Ejecuta la operación sugerida por el LLM.
    """
    op = params.pop("operation")
    
    # Convertir valores simples a formato DynamoDB si es necesario o usar directamente
    # Boto3 maneja gran parte, pero ExpressionAttributeValues necesita cuidado.
    
    try:
        if op == "query":
            response = table.query(**params)
        else:
            response = table.scan(**params)
            
        return response.get('Items', [])
    except Exception as e:
        print(f"Error ejecutando DynamoDB: {e}")
        return []

def paso_3_generar_respuesta_natural(pregunta, items):
    """
    Toma los datos crudos y responde la pregunta original usando lógica de negocio.
    """
    if not items:
        return "Lo siento, busqué en la base de datos pero no encontré registros que coincidan con tu solicitud."

    data_context = json.dumps(items, cls=DecimalEncoder, indent=2)

    system_prompt = """
    Eres un Asistente Experto en Logística y Tarifas. Tu trabajo es responder preguntas sobre costos de fletes basándote EXCLUSIVAMENTE en los datos JSON proporcionados.

    REGLAS DE NEGOCIO Y ANÁLISIS:
    
    1. El campo 'rango_base_precios' contiene los costos según el peso.
    2. Si el usuario pregunta por un peso específico (ej. "26,000 kg"), busca en qué rango cae (min_kg <= peso <= max_kg) y da ESE precio.
    3. Si el usuario no da peso, menciona la tarifa base y advierte sobre los sobrepesos.
    4. Menciona siempre el Proveedor, Origen y Destino para mayor claridad.
    5. Si hay costos adicionales fijos (fianza, tramite_aduana, custodio), menciónalos si son relevantes o si el usuario pregunta por "costo total".
    6. Sé amable, profesional y conciso. Usa formato Markdown para listas o negritas.
    """

    user_content = f"""
    PREGUNTA DEL USUARIO: "{pregunta}"
    
    DATOS RECUPERADOS DE LA BASE DE DATOS:
    {data_context}
    
    Responde a la pregunta basándote en estos datos.
    """
    
    return invoke_nova_pro(system_prompt, user_content)

def lambda_handler(event, context):
    try:
        # 1. Obtener pregunta
        #body = json.loads(event.get('body', '{}'))
        #user_query = body.get('query')
        user_query = event
        
        if not user_query:
            return {"statusCode": 400, "body": "Falta el campo 'query'."}

        print(f"Pregunta recibida: {user_query}")

        # 2. INTELIGENCIA DE BASE DE DATOS (Text-to-Query)
        db_params = paso_1_generar_query(user_query)
        print(f"Estrategia DB generada: {db_params}")

        # 3. RECUPERACIÓN DE DATOS
        items = paso_2_ejecutar_dynamo(db_params)
        print(f"Registros encontrados: {len(items)}")

        # 4. INTELIGENCIA DE NEGOCIO (Data-to-Answer)
        respuesta_final = paso_3_generar_respuesta_natural(user_query, items)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "respuesta": respuesta_final,
                "debug_items_found": len(items)
            })
        }

    except Exception as e:
        print(e)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
    
if __name__ == "__main__":
    # Simulación de evento local
    # test_event = "Viaje a Mixco con Angel paiz 22,000 kg"
    # response = lambda_handler(test_event, None)
    
    # if response["statusCode"] == 200:
    #     # Parseamos el body que viene como string JSON para mostrarlo limpio
    #     body_data = json.loads(response["body"])
    #     print("\n" + "="*60)
    #     print("🤖 RESPUESTA DEL ASISTENTE:")
    #     print("="*60 + "\n")
    #     print(body_data["respuesta"])
    #     print("\n" + "="*60)
    #     print(f"DEBUG: Registros encontrados en DynamoDB: {body_data['debug_items_found']}")
    #     #read terminal and capture input prompt for user
    user_input = input("¿Tienes alguna pregunta? ")
    print(f"DEBUG: Pregunta del usuario capturada: {user_input}")
    while user_input.strip().lower() not in ['exit', 'quit']:
        test_event = user_input
        response = lambda_handler(test_event, None)
        if response["statusCode"] == 200:
            body_data = json.loads(response["body"])
            print("\n" + "="*60)
            print("🤖 RESPUESTA DEL ASISTENTE:")
            print("="*60 + "\n")
            print(body_data["respuesta"])
            print("\n" + "="*60)
            print(f"DEBUG: Registros encontrados en DynamoDB: {body_data['debug_items_found']}")
        else:
            print(f"❌ ERROR: {response}")
        user_input = input("¿Tienes alguna otra pregunta? ")
        print(f"DEBUG: Pregunta del usuario capturada: {user_input}")

    #else:
    #    print(f"❌ ERROR: {response}")