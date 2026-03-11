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

def invoke_nova_pro(system_prompt, messages):
    """
    Función genérica para invocar a Amazon Nova Pro con soporte para mensajes conversacionales.
    
    Args:
        system_prompt: El prompt del sistema
        messages: Lista de mensajes en formato [{"role": "user/assistant", "content": [{"text": "..."}]}]
    """
    payload = {
        "system": [{"text": system_prompt}],
        "messages": messages,
        "inferenceConfig": {
            "max_new_tokens": 1000,
            "temperature": 0.1,
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
        return response_body['output']['message']['content'][0]['text']
    except Exception as e:
        print(f"Error invocando Bedrock: {e}")
        raise e

def analizar_necesidad_query(pregunta_usuario, conversation_history, datos_previos):
    """
    Determina si es necesario consultar DynamoDB o si se puede responder con el contexto existente.
    
    Returns:
        dict: {"necesita_query": True/False, "razon": "explicación"}
    """
    if not conversation_history or len(conversation_history) == 0:
        # Primera pregunta, siempre consultar
        return {"necesita_query": True, "razon": "Primera pregunta, no hay contexto previo"}
    
    # Construir el historial conversacional para el análisis
    messages = conversation_history + [
        {
            "role": "user",
            "content": [{"text": pregunta_usuario}]
        }
    ]
    
    system_prompt = """
    Eres un Analista de Contexto experto. Tu trabajo es determinar si una nueva pregunta puede responderse con la información ya disponible o si se necesita consultar la base de datos nuevamente.
    
    INSTRUCCIONES:
    1. Analiza la nueva pregunta del usuario en el contexto de la conversación previa.
    2. Revisa si los datos ya recuperados son suficientes para responder.
    3. Devuelve ÚNICAMENTE un JSON con tu decisión.
    4. NO agregues explicaciones, cálculos, ni texto adicional. SOLO el JSON.
    
    EJEMPLOS:
    
    Caso 1 - NO necesita query (pregunta de seguimiento sobre los mismos datos):
    Usuario anterior: "¿Cuánto cuesta de Puerto Quetzal a Mixco?"
    Respuesta anterior: "Te encontré 3 proveedores..."
    Nueva pregunta: "¿Cuál es el más barato?"
    Decisión: {"necesita_query": false, "razon": "La pregunta se refiere a los proveedores ya consultados"}
    
    Caso 2 - SÍ necesita query (nueva ruta o criterio):
    Usuario anterior: "¿Cuánto cuesta de Puerto Quetzal a Mixco?"
    Nueva pregunta: "¿Y a Villa Nueva?"
    Decisión: {"necesita_query": true, "razon": "Nuevo destino requiere consultar la base de datos"}
    
    Caso 3 - NO necesita query (pregunta de aclaración):
    Nueva pregunta: "¿Incluye la fianza?"
    Decisión: {"necesita_query": false, "razon": "Pregunta sobre detalles de los datos ya obtenidos"}
    
    Caso 4 - NO necesita query (pregunta sobre datos ya obtenidos):
    Usuario anterior: "¿Cuál es el viaje de Nixon Larios más económico?"
    Respuesta anterior: "Nixon Larios tiene 2 rutas disponibles..."
    Nueva pregunta: "¿Cuál es el precio con destino a la zona 18?"
    Decisión: {"necesita_query": false, "razon": "Los datos de Nixon Larios para Zona 18 ya fueron recuperados"}
    
    REGLA IMPORTANTE: 
    - Si hay duda, responde "necesita_query": true.
    - Si la pregunta cambia de proveedor, destino u origen significativamente diferente, responde true.
    - Si la pregunta es sobre datos ya mostrados en la conversación, responde false.
    
    FORMATO DE SALIDA:
    Devuelve EXCLUSIVAMENTE este formato JSON sin ningún texto adicional:
    {"necesita_query": true/false, "razon": "explicación breve"}
    """
    
    respuesta_llm = invoke_nova_pro(system_prompt, messages)
    
    print(f"\n{'='*60}")
    print("🔍 ANÁLISIS DE NECESIDAD DE QUERY:")
    print(f"{'='*60}")
    print(respuesta_llm)
    print(f"{'='*60}\n")
    
    # Limpiar la respuesta del LLM para extraer solo el JSON
    clean_json = respuesta_llm.replace("```json", "").replace("```", "").strip()
    
    # Intentar extraer el JSON si viene con texto adicional
    try:
        # Buscar el primer { y el último }
        start_idx = clean_json.find('{')
        end_idx = clean_json.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            clean_json = clean_json[start_idx:end_idx + 1]
        
        decision = json.loads(clean_json)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"⚠️ Error parseando JSON del análisis: {e}")
        print(f"Asumiendo que necesita query por seguridad...")
        decision = {"necesita_query": True, "razon": "Error parseando respuesta del LLM"}
    
    return decision

def paso_1_generar_query(pregunta_usuario, conversation_history):
    """
    Usa Nova Pro para decidir qué índice GSI usar y generar los parámetros.
    """
    schema_info = """
    ESTRUCTURA DE TABLA DYNAMODB ('TarifasLogistica'):
    - Partition Key: id (String)
    - Atributos: origen (String), destino (String), proveedor (String), dias_libres (Number), estadia (Number).
    - Atributo Complejo: 'rango_base_precios' es una LISTA de MAPAS [{'min_kg', 'max_kg', 'costo', 'concepto'}].

    ÍNDICES SECUNDARIOS GLOBALES (GSIs) DISPONIBLES:
    1. IndexName: 'RutaIndex' -> PK: 'origen', SK: 'destino'.
    2. IndexName: 'OrigenIndex' -> PK: 'origen'.
    3. IndexName: 'DestinoIndex' -> PK: 'destino'.
    4. IndexName: 'ProveedorIndex' -> PK: 'proveedor'.
    """

    system_prompt = f"""
    Eres un experto en DynamoDB. Analiza la pregunta y devuelve ÚNICAMENTE un JSON con estos campos:

    {schema_info}

    FORMATO DE SALIDA (solo JSON, sin explicaciones):
    {{
        "index": "RutaIndex",  // Nombre del índice a usar
        "origen": "Puerto Quetzal",  // Valor para PK (si aplica)
        "destino": "Mixco",  // Valor para SK (si aplica)
        "proveedor_filter": "Angel Paiz",  // Filtro adicional (opcional)
        "peso_kg": 22000  // Peso a buscar (opcional)
    }}

    REGLAS:
    - Si la pregunta menciona origen Y destino: usa "RutaIndex" con ambos valores
    - Si solo menciona destino: usa "DestinoIndex" con destino
    - Si solo menciona proveedor: usa "ProveedorIndex" con proveedor
    - Extrae el peso si se menciona
    - Devuelve SOLO el JSON, sin texto adicional
    """
    
    # Crear mensaje para el LLM
    messages = [
        {
            "role": "user",
            "content": [{"text": pregunta_usuario}]
        }
    ]
    
    respuesta_llm = invoke_nova_pro(system_prompt, messages)
    
    # 🔍 DEBUG: Ver la respuesta cruda del LLM
    print(f"\n{'='*60}")
    print("🔍 RESPUESTA CRUDA DEL LLM (paso_1):")
    print(f"{'='*60}")
    print(respuesta_llm)
    print(f"{'='*60}\n")
    
    # Limpieza básica por si el modelo devuelve bloques de código markdown
    clean_json = respuesta_llm.replace("```json", "").replace("```", "").strip()
    parsed = json.loads(clean_json)
    
    # 📊 DEBUG: Ver el JSON parseado
    print(f"\n{'='*60}")
    print("📊 PARÁMETROS PARSEADOS:")
    print(f"{'='*60}")
    print(json.dumps(parsed, indent=2))
    print(f"{'='*60}\n")
    
    return parsed

def paso_2_ejecutar_dynamo(params):
    """
    Ejecuta la query usando boto3.dynamodb.conditions correctamente.
    """
    index_name = params.get("index")
    origen = params.get("origen")
    destino = params.get("destino")
    proveedor_filter = params.get("proveedor_filter")
    peso_kg = params.get("peso_kg")
    
    print(f"\n{'='*60}")
    print(f"🎯 EJECUTANDO QUERY EN ÍNDICE: {index_name}")
    print(f"{'='*60}")
    print(f"Origen: {origen}, Destino: {destino}, Proveedor: {proveedor_filter}, Peso: {peso_kg}")
    print(f"{'='*60}\n")
    
    try:
        # Construir la KeyConditionExpression con objetos Key() de Boto3
        if index_name == "RutaIndex" and origen and destino:
            key_condition = Key('origen').eq(origen) & Key('destino').eq(destino)
            query_params = {
                "IndexName": index_name,
                "KeyConditionExpression": key_condition
            }
        elif index_name == "DestinoIndex" and destino:
            key_condition = Key('destino').eq(destino)
            query_params = {
                "IndexName": index_name,
                "KeyConditionExpression": key_condition
            }
        elif index_name == "ProveedorIndex" and proveedor_filter:
            key_condition = Key('proveedor').eq(proveedor_filter)
            query_params = {
                "IndexName": index_name,
                "KeyConditionExpression": key_condition
            }
        elif index_name == "OrigenIndex" and origen:
            key_condition = Key('origen').eq(origen)
            query_params = {
                "IndexName": index_name,
                "KeyConditionExpression": key_condition
            }
        else:
            print("⚠️ No se pudo construir query, haciendo scan")
            query_params = None
        
        # Ejecutar la consulta
        if query_params:
            print(f"Query params construidos correctamente")
            response = table.query(**query_params)
        else:
            response = table.scan()
        
        items = response.get('Items', [])
        print(f"Items recuperados de DynamoDB: {len(items)}")
        
        # FILTRADO EN PYTHON (post-query)
        # 1. Filtrar por proveedor si se usó RutaIndex o DestinoIndex
        if proveedor_filter and index_name in ["RutaIndex", "DestinoIndex", "OrigenIndex"]:
            items_antes = len(items)
            items = [item for item in items if proveedor_filter.lower() in item.get('proveedor', '').lower()]
            print(f"Filtrado por proveedor '{proveedor_filter}': {items_antes} → {len(items)} items")
        
        # 2. Filtrar por peso si se especificó
        if peso_kg and len(items) > 0:
            items_antes = len(items)
            filtered_items = []
            for item in items:
                rangos = item.get('rango_base_precios', [])
                # No filtramos, dejamos que el LLM interprete todos los rangos
                # Solo verificamos que existan rangos
                if rangos:
                    filtered_items.append(item)
            items = filtered_items
            print(f"Verificación de rangos de peso: {items_antes} → {len(items)} items")
        
        print(f"\n{'='*60}")
        print(f"📦 RESULTADO FINAL:")
        print(f"{'='*60}")
        print(f"Items encontrados: {len(items)}")
        if items:
            print("\nPrimer registro:")
            print(json.dumps(items[0], indent=2, cls=DecimalEncoder))
        print(f"{'='*60}\n")
        
        return items
        
    except Exception as e:
        print(f"❌ Error ejecutando DynamoDB: {e}")
        import traceback
        traceback.print_exc()
        return []

def paso_3_generar_respuesta_natural(pregunta, items, conversation_history):
    """
    Toma los datos crudos y responde la pregunta original usando lógica de negocio.
    Mantiene el contexto conversacional.
    """
    if not items:
        return "Lo siento, busqué en la base de datos pero no encontré registros que coincidan con tu solicitud."

    data_context = json.dumps(items, cls=DecimalEncoder, indent=2)

    system_prompt = """
    Eres un Asistente Experto en Logística y Tarifas. Tu trabajo es responder preguntas sobre costos de fletes basándote EXCLUSIVAMENTE en los datos JSON proporcionados.

    REGLAS DE NEGOCIO Y ANÁLISIS:
    
    1. El campo 'rango_base_precios' contiene los costos según el peso.
    2. Si el usuario pregunta por un peso específico (ej. "26,000 kg"), busca en qué rango cae (min_kg <= peso <= max_kg) Si el peso clasifica en Tarifa Base da ese precio, si clasifica en otro nivel se debe de sumar ese sobre peso + la tarifa base, informar al usuario el detalle.
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
    
    # Construir el historial de mensajes para mantener contexto
    messages = conversation_history + [
        {
            "role": "user",
            "content": [{"text": user_content}]
        }
    ]
    
    return invoke_nova_pro(system_prompt, messages)

def lambda_handler(event, context):
    try:
        # 1. Obtener pregunta y contexto conversacional
        body = json.loads(event.get('body', '{}')) if isinstance(event, dict) and 'body' in event else {}
        
        # Si se ejecuta localmente con string directo
        if isinstance(event, str):
            user_query = event
            conversation_history = []
            cached_data = None
        else:
            user_query = body.get('query')
            conversation_history = body.get('conversation_history', [])
            cached_data = body.get('cached_data')
        
        if not user_query:
            return {"statusCode": 400, "body": json.dumps({"error": "Falta el campo 'query'."})}

        print(f"Pregunta recibida: {user_query}")
        print(f"Historial de conversación: {len(conversation_history)} mensajes")

        # 2. ANALIZAR SI NECESITA CONSULTAR LA BASE DE DATOS
        decision = analizar_necesidad_query(user_query, conversation_history, cached_data)
        print(f"Decisión de consulta: {decision}")

        items = []
        
        if decision.get("necesita_query", True):
            # 3. INTELIGENCIA DE BASE DE DATOS (Text-to-Query)
            db_params = paso_1_generar_query(user_query, conversation_history)
            print(f"Estrategia DB generada: {db_params}")

            # 4. RECUPERACIÓN DE DATOS
            items = paso_2_ejecutar_dynamo(db_params)
            print(f"Registros encontrados: {len(items)}")
        else:
            # Usar datos del caché si existen
            print(f"ℹ️ Usando datos en caché. Razón: {decision.get('razon')}")
            items = cached_data if cached_data else []

        # 5. INTELIGENCIA DE NEGOCIO (Data-to-Answer)
        respuesta_final = paso_3_generar_respuesta_natural(user_query, items, conversation_history)

        # 6. ACTUALIZAR EL HISTORIAL DE CONVERSACIÓN
        # Agregar la pregunta del usuario
        conversation_history.append({
            "role": "user",
            "content": [{"text": user_query}]
        })
        
        # Agregar la respuesta del asistente
        conversation_history.append({
            "role": "assistant",
            "content": [{"text": respuesta_final}]
        })

        return {
            "statusCode": 200,
            "body": json.dumps({
                "respuesta": respuesta_final,
                "conversation_history": conversation_history,
                "cached_data": items,  # Mantener los datos para posibles preguntas de seguimiento
                "debug_items_found": len(items),
                "debug_used_cache": not decision.get("necesita_query", True)
            }, cls=DecimalEncoder)  # Usar DecimalEncoder para serializar Decimal
        }

    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
    
if __name__ == "__main__":
    # Simulación de evento local con conversación continua
    print("\n" + "="*60)
    print("💬 CHATBOT DE LOGÍSTICA - Modo Conversacional")
    print("="*60)
    print("Escribe 'exit' o 'quit' para salir\n")
    
    # Inicializar estado de la conversación
    conversation_state = {
        "conversation_history": [],
        "cached_data": None
    }
    
    # Primera pregunta
    user_input = input("👤 Tu pregunta: ")
    
    while user_input.strip().lower() not in ['exit', 'quit', 'salir']:
        # Crear evento simulado
        event = {
            "body": json.dumps({
                "query": user_input,
                "conversation_history": conversation_state["conversation_history"],
                "cached_data": conversation_state["cached_data"]
            })
        }
        
        # Procesar la pregunta
        response = lambda_handler(event, None)
        
        if response["statusCode"] == 200:
            body_data = json.loads(response["body"])
            
            print("\n" + "="*60)
            print("🤖 RESPUESTA DEL ASISTENTE:")
            print("="*60 + "\n")
            print(body_data["respuesta"])
            print("\n" + "="*60)
            print(f"📊 DEBUG INFO:")
            print(f"  - Registros en contexto: {body_data['debug_items_found']}")
            print(f"  - Usó caché: {'✅ Sí' if body_data.get('debug_used_cache') else '❌ No (consultó DB)'}")
            print(f"  - Mensajes en historial: {len(body_data['conversation_history'])}")
            print("="*60 + "\n")
            
            # Actualizar el estado de la conversación
            conversation_state["conversation_history"] = body_data["conversation_history"]
            conversation_state["cached_data"] = body_data["cached_data"]
        else:
            print(f"\n❌ ERROR: {response}\n")
        
        # Pedir siguiente pregunta
        user_input = input("👤 Tu pregunta: ")
    
    print("\n👋 ¡Hasta luego!\n")