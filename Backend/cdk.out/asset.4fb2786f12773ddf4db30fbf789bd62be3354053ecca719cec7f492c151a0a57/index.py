import boto3
import json
import os
from decimal import Decimal
from boto3.dynamodb.conditions import Key

# --- CONFIGURACIÓN ---
TABLE_NAME = os.environ.get('TABLE_NAME', 'TarifasLogistica')
REGION = os.environ.get('REGION', 'us-east-1')
MODEL_ID = os.environ.get('MODEL_ID', 'amazon.nova-pro-v1:0')

dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table(TABLE_NAME)
bedrock = boto3.client('bedrock-runtime', region_name=REGION)

# --- GESTIÓN DE HISTORIAL DE CONVERSACIÓN EN MEMORIA ---
# Nota: En producción, considera usar DynamoDB o ElastiCache para persistir sesiones
conversation_sessions = {}

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def invoke_nova_pro(system_prompt, user_message, conversation_history=None):
    """
    Función genérica para invocar a Amazon Nova Pro con soporte para historial de conversación.
    """
    messages = []
    
    if conversation_history:
        messages.extend(conversation_history[-10:])
    
    messages.append({
        "role": "user",
        "content": [{"text": user_message}]
    })
    
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
        assistant_response = response_body['output']['message']['content'][0]['text']
        
        return assistant_response
    except Exception as e:
        print(f"Error invocando Bedrock: {e}")
        raise e

def construir_contexto_conversacion(conversation_history):
    """
    Construye un resumen del contexto de la conversación para ayudar al LLM.
    """
    if not conversation_history:
        return "PRIMERA PREGUNTA (sin contexto previo)"
    
    contexto = "CONTEXTO DE CONVERSACIÓN PREVIA:\n"
    for msg in conversation_history[-6:]:
        role = "Usuario" if msg["role"] == "user" else "Asistente"
        text = msg["content"][0]["text"]
        contexto += f"{role}: {text[:200]}...\n" if len(text) > 200 else f"{role}: {text}\n"
    
    return contexto

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
    
    contexto_previo = construir_contexto_conversacion(conversation_history)

    system_prompt = f"""
    Eres un experto en DynamoDB. Analiza la pregunta ACTUAL y el CONTEXTO PREVIO de la conversación para devolver ÚNICAMENTE un JSON con estos campos:

    {schema_info}

    FORMATO DE SALIDA (solo JSON, sin explicaciones):
    {{
        "index": "RutaIndex",
        "origen": "Puerto Quetzal",
        "destino": "Mixco",
        "proveedor_filter": "Angel Paiz",
        "peso_kg": 22000
    }}

    REGLAS:
    - Si la pregunta menciona origen Y destino: usa "RutaIndex" con ambos valores
    - Si solo menciona destino: usa "DestinoIndex" con destino
    - Si solo menciona proveedor: usa "ProveedorIndex" con proveedor
    - Si la pregunta usa pronombres ("ese", "esa", "el mismo", etc.) o referencias implícitas, extrae los valores del contexto previo
    - Si la pregunta es de seguimiento (ej: "¿y con 30,000 kg?"), reutiliza origen/destino/proveedor del contexto previo
    - Extrae el peso si se menciona
    - Devuelve SOLO el JSON, sin texto adicional
    
    {contexto_previo}
    """
    
    respuesta_llm = invoke_nova_pro(system_prompt, pregunta_usuario)
    clean_json = respuesta_llm.replace("```json", "").replace("```", "").strip()
    parsed = json.loads(clean_json)
    
    return parsed

def busqueda_flexible_destino(destino_buscado, limite=10):
    """
    Realiza búsqueda flexible por destino cuando no hay coincidencia exacta.
    """
    print(f"Búsqueda flexible activada para destino: '{destino_buscado}'")
    
    response = table.scan(Limit=limite * 3)
    items_todos = response.get('Items', [])
    
    destino_normalizado = destino_buscado.lower().strip()
    
    items_coincidentes = []
    for item in items_todos:
        if len(items_coincidentes) >= limite:
            break
            
        destino_item = item.get('destino', '').lower()
        
        if destino_normalizado in destino_item:
            items_coincidentes.append(item)
            continue
        
        palabras_buscadas = destino_normalizado.replace(',', ' ').split()
        palabras_item = destino_item.replace(',', ' ').split()
        
        if any(palabra in palabras_item for palabra in palabras_buscadas if palabra):
            items_coincidentes.append(item)
    
    return items_coincidentes

def paso_2_ejecutar_dynamo(params):
    """
    Ejecuta la query usando boto3.dynamodb.conditions.
    """
    index_name = params.get("index")
    origen = params.get("origen")
    destino = params.get("destino")
    proveedor_filter = params.get("proveedor_filter")
    
    try:
        items = []
        busqueda_exacta_fallo = False
        
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
            query_params = None
        
        if query_params:
            response = table.query(**query_params)
            items = response.get('Items', [])
            
            if len(items) == 0 and destino:
                busqueda_exacta_fallo = True
                items = busqueda_flexible_destino(destino)
        else:
            if destino:
                items = busqueda_flexible_destino(destino)
            else:
                response = table.scan()
                items = response.get('Items', [])
        
        # Filtrado post-query
        if busqueda_exacta_fallo and origen and len(items) > 0:
            items = [item for item in items if origen.lower() in item.get('origen', '').lower()]
        
        if proveedor_filter and index_name in ["RutaIndex", "DestinoIndex", "OrigenIndex"]:
            items = [item for item in items if proveedor_filter.lower() in item.get('proveedor', '').lower()]
        
        return items
        
    except Exception as e:
        print(f"Error ejecutando DynamoDB: {e}")
        return []

def extraer_datos_relevantes(items, peso_kg=None):
    """
    Extrae solo los campos necesarios para reducir tokens enviados al LLM.
    """
    datos_simplificados = []
    
    for item in items:
        rangos_relevantes = item.get('rango_base_precios', [])
        
        if peso_kg and rangos_relevantes:
            rangos_filtrados = []
            for rango in rangos_relevantes:
                min_kg = float(rango.get('min_kg', 0))
                max_kg = float(rango.get('max_kg', float('inf')))
                
                if rango.get('concepto') == 'Tarifa Base' or (min_kg <= peso_kg <= max_kg):
                    rangos_filtrados.append({
                        'min_kg': min_kg,
                        'max_kg': max_kg,
                        'costo': float(rango.get('costo', 0)),
                        'concepto': rango.get('concepto')
                    })
            rangos_relevantes = rangos_filtrados
        else:
            rangos_relevantes = [
                {
                    'min_kg': float(r.get('min_kg', 0)),
                    'max_kg': float(r.get('max_kg', 0)),
                    'costo': float(r.get('costo', 0)),
                    'concepto': r.get('concepto')
                }
                for r in rangos_relevantes
            ]
        
        datos_simplificados.append({
            'origen': item.get('origen'),
            'destino': item.get('destino'),
            'proveedor': item.get('proveedor'),
            'dias_libres': float(item.get('dias_libres', 0)),
            'estadia': float(item.get('estadia', 0)),
            'fianza': float(item.get('fianza', 0)),
            'rangos': rangos_relevantes
        })
    
    return datos_simplificados

def paso_3_generar_respuesta_natural(pregunta, items, peso_kg, conversation_history):
    """
    Toma los datos crudos y responde la pregunta original usando lógica de negocio.
    """
    if not items:
        respuesta = "Lo siento, busqué en la base de datos pero no encontré registros que coincidan con tu solicitud."
        
        conversation_history.append({
            "role": "user",
            "content": [{"text": pregunta}]
        })
        conversation_history.append({
            "role": "assistant",
            "content": [{"text": respuesta}]
        })
        
        return respuesta

    datos_optimizados = extraer_datos_relevantes(items, peso_kg)
    
    if len(datos_optimizados) > 5:
        datos_optimizados = datos_optimizados[:5]
    
    data_context = json.dumps(datos_optimizados, indent=2)

    system_prompt = """
    Eres un Asistente Experto en Logística y Tarifas. Tu trabajo es responder preguntas sobre costos de fletes basándote EXCLUSIVAMENTE en los datos JSON proporcionados.

    REGLAS DE NEGOCIO Y ANÁLISIS:
    
    1. El campo 'rangos' contiene los costos según el peso (min_kg, max_kg, costo, concepto).
    2. Si el usuario pregunta por un peso específico (ej. "26,000 kg"), busca en qué rango cae (min_kg <= peso <= max_kg). Si el peso clasifica en Tarifa Base da ese precio, si clasifica en otro nivel se debe de sumar ese sobre peso + la tarifa base, informar al usuario el detalle.
    3. Si el usuario no da peso, menciona la tarifa base y advierte sobre los sobrepesos.
    4. Menciona siempre el Proveedor, Origen y Destino para mayor claridad.
    5. Si hay costos adicionales fijos (fianza, estadia, dias_libres), menciónalos si son relevantes o si el usuario pregunta por "costo total".
    6. Sé amable, profesional y conciso. Usa formato Markdown para listas o negritas.
    """

    user_content = f"""
PREGUNTA DEL USUARIO: "{pregunta}"

DATOS RECUPERADOS DE LA BASE DE DATOS:
{data_context}

Responde a la pregunta basándote en estos datos.
"""
    
    # Añadir pregunta al historial
    conversation_history.append({
        "role": "user",
        "content": [{"text": pregunta}]
    })
    
    # Generar respuesta con historial
    respuesta = invoke_nova_pro(system_prompt, user_content, conversation_history)
    
    # Añadir respuesta al historial
    conversation_history.append({
        "role": "assistant",
        "content": [{"text": respuesta}]
    })
    
    return respuesta

def handler(event, context):
    """
    Handler optimizado para API Gateway.
    Recibe: {"query": "pregunta del usuario", "session_id": "opcional"}
    Devuelve: {"respuesta": "...", "session_id": "..."}
    """
    try:
        # Parsear el body del request
        body = json.loads(event.get('body', '{}'))
        user_query = body.get('query')
        session_id = body.get('session_id', 'default')
        
        if not user_query:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({"error": "Falta el campo 'query'"})
            }

        # Obtener o crear historial de conversación para esta sesión
        if session_id not in conversation_sessions:
            conversation_sessions[session_id] = []
        
        conversation_history = conversation_sessions[session_id]

        # Generar estrategia de búsqueda
        db_params = paso_1_generar_query(user_query, conversation_history)
        peso_kg = db_params.get('peso_kg')

        # Ejecutar búsqueda en DynamoDB
        items = paso_2_ejecutar_dynamo(db_params)

        # Generar respuesta natural
        respuesta_final = paso_3_generar_respuesta_natural(user_query, items, peso_kg, conversation_history)

        # Respuesta exitosa
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "respuesta": respuesta_final,
                "session_id": session_id,
                "items_found": len(items)
            }, cls=DecimalEncoder)
        }

    except Exception as e:
        print(f"Error en handler: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"error": str(e)})
        }
