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

# --- GESTIÓN DE HISTORIAL DE CONVERSACIÓN ---
conversation_history = []

# --- CLASE AUXILIAR PARA JSON ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def invoke_nova_pro(system_prompt, user_message, use_history=False):
    """
    Función genérica para invocar a Amazon Nova Pro con soporte para historial de conversación.
    
    Args:
        system_prompt: Instrucciones del sistema
        user_message: Mensaje del usuario actual
        use_history: Si True, incluye el historial de conversación
    """
    # Construir mensajes con historial si está habilitado
    messages = []
    
    if use_history and conversation_history:
        # Agregar mensajes históricos (limitado a los últimos 10 para no exceder tokens)
        messages.extend(conversation_history[-10:])
    
    # Agregar mensaje actual del usuario
    messages.append({
        "role": "user",
        "content": [{"text": user_message}]
    })
    
    payload = {
        "system": [{"text": system_prompt}],
        "messages": messages,
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
        assistant_response = response_body['output']['message']['content'][0]['text']
        
        # Si usamos historial, guardar este intercambio
        if use_history:
            conversation_history.append({
                "role": "user",
                "content": [{"text": user_message}]
            })
            conversation_history.append({
                "role": "assistant",
                "content": [{"text": assistant_response}]
            })
        
        return assistant_response
    except Exception as e:
        print(f"Error invocando Bedrock: {e}")
        raise e

def construir_contexto_conversacion():
    """
    Construye un resumen del contexto de la conversación para ayudar al LLM.
    """
    if not conversation_history:
        return "PRIMERA PREGUNTA (sin contexto previo)"
    
    # Construir resumen de los últimos intercambios
    contexto = "CONTEXTO DE CONVERSACIÓN PREVIA:\n"
    for i, msg in enumerate(conversation_history[-6:]):  # Últimos 3 intercambios (6 mensajes)
        role = "Usuario" if msg["role"] == "user" else "Asistente"
        text = msg["content"][0]["text"]
        contexto += f"{role}: {text[:200]}...\n" if len(text) > 200 else f"{role}: {text}\n"
    
    return contexto

def limpiar_historial():
    """
    Limpia el historial de conversación. Útil para iniciar una nueva sesión.
    """
    global conversation_history
    conversation_history = []
    print("🧹 Historial de conversación limpiado")

def paso_1_generar_query(pregunta_usuario):
    """
    Usa Nova Pro para decidir qué índice GSI usar y generar los parámetros.
    Utiliza el contexto de conversación para entender preguntas de seguimiento.
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
    
    # Obtener contexto de conversación
    contexto_previo = construir_contexto_conversacion()

    system_prompt = f"""
    Eres un experto en DynamoDB. Analiza la pregunta ACTUAL y el CONTEXTO PREVIO de la conversación para devolver ÚNICAMENTE un JSON con estos campos:

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
    - Si la pregunta usa pronombres ("ese", "esa", "el mismo", etc.) o referencias implícitas, extrae los valores del contexto previo
    - Si la pregunta es de seguimiento (ej: "¿y con 30,000 kg?"), reutiliza origen/destino/proveedor del contexto previo
    - Extrae el peso si se menciona
    - Devuelve SOLO el JSON, sin texto adicional
    
    {contexto_previo}
    """
    
    respuesta_llm = invoke_nova_pro(system_prompt, pregunta_usuario, use_history=False)
    
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

def busqueda_flexible_destino(destino_buscado):
    """
    Realiza búsqueda flexible por destino cuando no hay coincidencia exacta.
    Busca coincidencias parciales (ej: "zona 17" encuentra "Zona 6,16,17,18").
    """
    print(f"🔍 Búsqueda flexible activada para destino: '{destino_buscado}'")
    
    # Hacer scan de la tabla para buscar coincidencias parciales
    response = table.scan()
    items_todos = response.get('Items', [])
    
    # Normalizar búsqueda (minúsculas, sin espacios extra)
    destino_normalizado = destino_buscado.lower().strip()
    
    # Filtrar items que contengan el destino buscado
    items_coincidentes = []
    for item in items_todos:
        destino_item = item.get('destino', '').lower()
        
        # Coincidencia parcial: "zona 17" coincide con "zona 6,16,17,18"
        if destino_normalizado in destino_item:
            items_coincidentes.append(item)
            continue
        
        # Coincidencia por palabras individuales: "17" coincide con "Zona 6,16,17,18"
        palabras_buscadas = destino_normalizado.replace(',', ' ').split()
        palabras_item = destino_item.replace(',', ' ').split()
        
        if any(palabra in palabras_item for palabra in palabras_buscadas if palabra):
            items_coincidentes.append(item)
    
    print(f"✅ Encontrados {len(items_coincidentes)} items con búsqueda flexible")
    return items_coincidentes

def paso_2_ejecutar_dynamo(params):
    """
    Ejecuta la query usando boto3.dynamodb.conditions correctamente.
    Incluye búsqueda flexible para destinos parciales.
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
        items = []
        busqueda_exacta_fallo = False
        
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
            print("⚠️ No se pudo construir query con índices")
            query_params = None
        
        # Ejecutar la consulta
        if query_params:
            print(f"Query params construidos correctamente")
            response = table.query(**query_params)
            items = response.get('Items', [])
            print(f"Items recuperados de DynamoDB con query: {len(items)}")
            
            # Si no hay resultados y hay un destino, intentar búsqueda flexible
            if len(items) == 0 and destino:
                busqueda_exacta_fallo = True
                print("⚠️ No se encontraron coincidencias exactas, intentando búsqueda flexible...")
                items = busqueda_flexible_destino(destino)
        else:
            # Si no hay índice válido pero hay destino, usar búsqueda flexible
            if destino:
                items = busqueda_flexible_destino(destino)
            else:
                print("⚠️ Haciendo scan completo (no recomendado)")
                response = table.scan()
                items = response.get('Items', [])
        
        # FILTRADO EN PYTHON (post-query)
        # 1. Filtrar por origen si se hizo búsqueda flexible y se especificó origen
        if busqueda_exacta_fallo and origen and len(items) > 0:
            items_antes = len(items)
            items = [item for item in items if origen.lower() in item.get('origen', '').lower()]
            print(f"Filtrado por origen '{origen}': {items_antes} → {len(items)} items")
        
        # 2. Filtrar por proveedor si se especificó
        if proveedor_filter and index_name in ["RutaIndex", "DestinoIndex", "OrigenIndex"]:
            items_antes = len(items)
            items = [item for item in items if proveedor_filter.lower() in item.get('proveedor', '').lower()]
            print(f"Filtrado por proveedor '{proveedor_filter}': {items_antes} → {len(items)} items")
        
        # 3. Filtrar por peso si se especificó
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

def paso_3_generar_respuesta_natural(pregunta, items):
    """
    Toma los datos crudos y responde la pregunta original usando lógica de negocio.
    Utiliza el historial de conversación para mantener el contexto.
    """
    if not items:
        respuesta = "Lo siento, busqué en la base de datos pero no encontré registros que coincidan con tu solicitud."
        
        # Guardar en historial incluso si no hay resultados
        conversation_history.append({
            "role": "user",
            "content": [{"text": pregunta}]
        })
        conversation_history.append({
            "role": "assistant",
            "content": [{"text": respuesta}]
        })
        
        return respuesta

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
    
    # Usar historial en la respuesta final para mantener coherencia conversacional
    respuesta = invoke_nova_pro(system_prompt, user_content, use_history=True)
    
    return respuesta

def lambda_handler(event, context):
    try:
        # 1. Obtener pregunta
        #body = json.loads(event.get('body', '{}'))
        #user_query = body.get('query')
        user_query = event
        
        if not user_query:
            return {"statusCode": 400, "body": "Falta el campo 'query'."}

        print(f"Pregunta recibida: {user_query}")

        #Analizar si es una pregunta de seguimiento o nueva pregunta con IA


        

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
    print("\n" + "="*60)
    print("🤖 ASISTENTE DE LOGÍSTICA - Modo Conversacional")
    print("="*60)
    print("Comandos especiales:")
    print("  - 'limpiar' o 'reset': Limpiar historial de conversación")
    print("  - 'exit' o 'quit': Salir del programa")
    print("="*60 + "\n")
    
    user_input = input("¿Tienes alguna pregunta? ")
    print(f"DEBUG: Pregunta del usuario capturada: {user_input}")
    
    while user_input.strip().lower() not in ['exit', 'quit']:
        # Verificar comandos especiales
        if user_input.strip().lower() in ['limpiar', 'reset', 'clear']:
            limpiar_historial()
            user_input = input("\n¿Tienes alguna pregunta? ")
            continue
        
        test_event = user_input
        response = lambda_handler(test_event, None)
        
        if response["statusCode"] == 200:
            body_data = json.loads(response["body"])
            print("\n" + "="*60)
            print("🤖 RESPUESTA DEL ASISTENTE:")
            print("="*60 + "\n")
            print(body_data["respuesta"])
            print("\n" + "="*60)
            print(f"DEBUG: Registros encontrados: {body_data['debug_items_found']}")
            print(f"DEBUG: Mensajes en historial: {len(conversation_history)}")
            print("="*60 + "\n")
        else:
            print(f"❌ ERROR: {response}")
        
        user_input = input("¿Tienes alguna otra pregunta? ")
        print(f"DEBUG: Pregunta del usuario capturada: {user_input}")