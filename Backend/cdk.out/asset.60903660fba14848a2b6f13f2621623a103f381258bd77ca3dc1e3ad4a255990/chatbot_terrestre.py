import boto3
import json
import os
import re
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr

# --- CONFIGURACIÓN ---
TABLE_NAME = os.environ.get('TABLE_NAME', 'TarifasLogistica')
REGION = os.environ.get('REGION', 'us-east-1')
MODEL_ID = os.environ.get('MODEL_ID', 'amazon.nova-pro-v1:0') 

dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table(TABLE_NAME)
bedrock = boto3.client('bedrock-runtime', region_name=REGION)

# --- CLASE AUXILIAR PARA JSON ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def invoke_nova_pro(system_prompt, user_message, conversation_history=None):
    """
    Función genérica para invocar a Amazon Nova Pro con soporte para historial de conversación.
    
    Args:
        system_prompt: Instrucciones del sistema
        user_message: Mensaje del usuario actual
        conversation_history: Lista de mensajes previos (opcional, manejado por frontend)
    """
    messages = []
    
    # Si hay historial proporcionado por el frontend, incluirlo
    if conversation_history:
        messages.extend(conversation_history[-10:])  # Últimos 10 para no exceder tokens
    
    # Agregar mensaje actual del usuario
    messages.append({
        "role": "user",
        "content": [{"text": user_message}]
    })
    
    payload = {
        "system": [{"text": system_prompt}],
        "messages": messages,
        "inferenceConfig": {
            "max_new_tokens": 4000,
            "temperature": 0,
            "top_p": 0
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
    Construye un resumen ENRIQUECIDO del contexto de la conversación.
    Extrae información clave: rutas, pesos, proveedores mencionados.
    
    Args:
        conversation_history: Lista de mensajes previos del frontend
    """
    if not conversation_history:
        return "PRIMERA PREGUNTA (sin contexto previo)"

    # Información clave extraída del historial
    contexto_enriquecido = {
        "rutas_mencionadas": [],
        "proveedores_mencionados": [],
        "pesos_mencionados": [],
        "ultimas_cotizaciones": []
    }
    
    # Analizar historial para extraer datos clave
    for msg in conversation_history[-10:]:  # Últimos 5 intercambios
        text = msg["content"][0]["text"]
        
        # Extraer rutas (origen → destino)
        rutas = re.findall(r'(Puerto [A-Za-zá-úÁ-Ú]+|[A-Za-zá-úÁ-Ú]+)\s*(?:→|->|a|hacia)\s*([A-Za-zá-úÁ-Ú,\s\d]+)', text, re.IGNORECASE)
        if rutas:
            contexto_enriquecido["rutas_mencionadas"].extend(rutas)
        
        # Extraer proveedores conocidos
        proveedores = re.findall(r'\b(Nixon Larios|Angel Paiz|Transportes RAC|RAC)\b', text, re.IGNORECASE)
        if proveedores:
            contexto_enriquecido["proveedores_mencionados"].extend(proveedores)
        
        # Extraer pesos
        pesos = re.findall(r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*kg', text)
        if pesos:
            contexto_enriquecido["pesos_mencionados"].extend(pesos)
    
    # Construir contexto textual mejorado
    contexto = "CONTEXTO DE CONVERSACIÓN ENRIQUECIDO:\n\n"
    
    if contexto_enriquecido["rutas_mencionadas"]:
        rutas_unicas = list(set([f"{r[0]} → {r[1]}" for r in contexto_enriquecido["rutas_mencionadas"][-3:]]))
        contexto += f"📍 Rutas discutidas: {', '.join(rutas_unicas)}\n"
    
    if contexto_enriquecido["proveedores_mencionados"]:
        proveedores_unicos = list(set(contexto_enriquecido["proveedores_mencionados"][-3:]))
        contexto += f"🚛 Proveedores mencionados: {', '.join(proveedores_unicos)}\n"
    
    if contexto_enriquecido["pesos_mencionados"]:
        contexto += f"⚖️ Pesos discutidos: {', '.join(contexto_enriquecido['pesos_mencionados'][-3:])} kg\n"
    
    contexto += "\n📝 ÚLTIMOS MENSAJES:\n"
    for msg in conversation_history[-6:]:  # Últimos 3 intercambios
        role = "Usuario" if msg["role"] == "user" else "Asistente"
        text = msg["content"][0]["text"]
        contexto += f"{role}: {text[:300]}...\n" if len(text) > 300 else f"{role}: {text}\n"
    
    return contexto

def paso_0_clasificar_intencion(pregunta_usuario, conversation_history=None):
    """
    Clasifica si la pregunta requiere consultar DynamoDB o puede responderse con el historial.
    
    LÓGICA OPTIMIZADA:
    - Si la pregunta puede responderse con el contexto previo → "conversacional" (sin DB)
    - Si requiere información nueva de tarifas/rutas → "cotizacion" (con DB)
    
    Args:
        pregunta_usuario: Pregunta actual del usuario
        conversation_history: Historial de mensajes del frontend
    
    Returns:
        dict: {
            "tipo": "cotizacion" | "conversacional",
            "requiere_db": bool,
            "razon": str
        }
    """
    contexto_previo = construir_contexto_conversacion(conversation_history)
    
    system_prompt = f"""
    Eres un clasificador inteligente para un chatbot de logística.
    
    TU MISIÓN: Determinar si la pregunta NECESITA consultar la base de datos o puede responderse con el contexto de conversación.
    
    REGLAS DE CLASIFICACIÓN:
    
    1. **COTIZACIÓN** (requiere_db=true) → Si:
       - Usuario pregunta por tarifas, precios, costos de una ruta NUEVA (no mencionada antes)
       - Usuario cambia origen, destino o proveedor comparado con el contexto
       - Usuario pregunta por información que NO está en el historial previo
       - Ejemplos: "¿Cuánto cuesta enviar a Antigua?", "Precio de Puerto Barrios a Mixco"
    
    2. **CONVERSACIONAL** (requiere_db=false) → Si:
       - Usuario pregunta sobre información YA PROPORCIONADA en el historial
       - Usuario hace preguntas de seguimiento sobre la MISMA cotización (cambio de peso, comparación)
       - Saludos, agradecimientos, confirmaciones
       - Ejemplos: "¿Y con 30,000 kg?", "¿Cuál es más barato?", "Gracias", "¿Me repites el precio?"
    
    FORMATO DE SALIDA (solo JSON, sin explicaciones):
    {{
        "tipo": "cotizacion",
        "requiere_db": true,
        "razon": "Nueva ruta solicitada: Puerto Barrios → Antigua"
    }}
    
    IMPORTANTE:
    - Analiza si la información para responder YA EXISTE en el contexto previo
    - Si el usuario pregunta lo mismo con diferente peso → "conversacional" (usa datos previos)
    - Si el usuario cambia ruta/proveedor → "cotizacion" (necesita datos nuevos)
    - Devuelve SOLO el JSON, sin texto adicional
    
    {contexto_previo}
    """
    
    try:
        respuesta_llm = invoke_nova_pro(system_prompt, pregunta_usuario)
        clean_json = respuesta_llm.replace("```json", "").replace("```", "").strip()
        clasificacion = json.loads(clean_json)
        
        print(f"\n{'='*60}")
        print(f"🔍 CLASIFICACIÓN DE INTENCIÓN:")
        print(f"{'='*60}")
        print(json.dumps(clasificacion, indent=2, ensure_ascii=False))
        print(f"{'='*60}\n")
        
        return clasificacion
    
    except Exception as e:
        print(f"Error en clasificación de intención: {e}")
        # Por defecto, asumir que necesita DB para no perder información
        return {
            "tipo": "cotizacion",
            "requiere_db": True,
            "razon": "Error en clasificación, ejecutando flujo completo por seguridad"
        }

def manejar_pregunta_conversacional(pregunta_usuario, conversation_history=None):
    """
    Responde preguntas usando SOLO el contexto de conversación previo.
    No consulta la base de datos.
    
    Args:
        pregunta_usuario: Pregunta del usuario
        conversation_history: Historial de mensajes
    
    Returns:
        str: Respuesta generada con el contexto disponible
    """
    system_prompt = """
    Eres un Asistente Experto en Logística y Tarifas.
    
    IMPORTANTE: Responde basándote EXCLUSIVAMENTE en el contexto de conversación previo.
    NO tienes acceso a nueva información de la base de datos en este momento.
    
    REGLAS:
    1. Si el usuario pregunta sobre tarifas/rutas YA MENCIONADAS → Responde con esa información
    2. Si el usuario cambia el peso → Recalcula usando los rangos ya conocidos
    3. Si el usuario compara opciones → Usa las opciones ya proporcionadas
    4. Si es un saludo/agradecimiento → Responde amablemente
    5. Si pide información que NO está en el contexto → Indica que necesitas más detalles
    
    FORMATO:
    - Usa Markdown para listas y negritas
    - NUNCA USES ETIQUETAS XML
    - Sé conciso y profesional
    - Si faltan datos, pide aclaración al usuario
    """
    
    user_content = f"""
PREGUNTA ACTUAL: "{pregunta_usuario}"

Responde usando SOLO la información del contexto de conversación previo.
Si necesitas información nueva de la base de datos, indícale al usuario que especifique origen/destino.
"""
    
    respuesta = invoke_nova_pro(system_prompt, user_content, conversation_history)
    
    print(f"\n{'='*60}")
    print(f"💬 RESPUESTA CONVERSACIONAL (sin consulta DB)")
    print(f"{'='*60}\n")
    
    return respuesta

def paso_1_generar_query(pregunta_usuario, conversation_history=None):
    """
    Usa Nova Pro para decidir qué índice GSI usar y generar los parámetros.
    MEJORADO: Más inteligente al extraer información del contexto.
    
    Args:
        pregunta_usuario: Pregunta actual del usuario
        conversation_history: Historial de mensajes (opcional, del frontend)
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
    
    # Obtener contexto enriquecido de conversación
    contexto_previo = construir_contexto_conversacion(conversation_history)

    system_prompt = f"""
    Eres un experto en DynamoDB y análisis de contexto conversacional.
    
    TU MISIÓN: Analizar la pregunta y el CONTEXTO COMPLETO para generar la mejor estrategia de consulta.

    {schema_info}

    FORMATO DE SALIDA (solo JSON, sin explicaciones):
    {{
        "index": "DestinoIndex",
        "origen": "Puerto Quetzal",
        "destino": "Mixco",
        "proveedor_filter": null,
        "peso_kg": 22000,
        "busqueda_amplia": false
    }}

    REGLAS MEJORADAS:
    
    1. **EXTRACCIÓN INTELIGENTE DE CONTEXTO:**
       - Si el usuario menciona "ese proveedor", "esa ruta", "el mismo", etc. → Extrae del contexto previo
       - Si cambia solo el peso → Mantén la ruta y proveedor del contexto
       - Si pregunta "¿y con X proveedor?" → Mantén la ruta, cambia proveedor
    
    2. **ESTRATEGIA DE ÍNDICES:**
       - Si menciona origen Y destino → "RutaIndex"
       - Si SOLO menciona destino → "DestinoIndex" 
       - Si SOLO menciona origen → "OrigenIndex"
       - Si SOLO menciona proveedor → "ProveedorIndex"
       - Si NO menciona proveedor específico → NO pongas proveedor_filter (null)
    
    3. **BÚSQUEDA AMPLIA:**
       - Si el usuario dice "opciones", "mejores tarifas", "recomiéndame", "compara" → busqueda_amplia: true
       - Si NO especifica proveedor → busqueda_amplia: true (para comparar opciones)
       - Si es pregunta general sin detalles → busqueda_amplia: true
    
    4. **NORMALIZACIÓN:**
       - Destinos: "z16" → "Zona 16", "Mixco" → "Mixco", etc.
       - Orígenes: "Puerto Quetzal", "Santo Tomás", etc.
       - Pesos: Extraer número sin comas (26000, no 26,000)
    
    5. **IMPORTANTE:**
       - Si el usuario NO menciona proveedor → proveedor_filter: null
       - Si pide "mejores opciones" → proveedor_filter: null, busqueda_amplia: true
       - SIEMPRE extrae el peso si se menciona en pregunta actual o contexto reciente
    
    {contexto_previo}
    
    Devuelve SOLO el JSON, sin texto adicional.
    """
    
    respuesta_llm = invoke_nova_pro(system_prompt, pregunta_usuario)
    
    print(f"\n{'='*60}")
    print("RESPUESTA CRUDA DEL LLM (paso_1):")
    print(f"{'='*60}")
    print(respuesta_llm)
    print(f"{'='*60}\n")
    
    clean_json = respuesta_llm.replace("```json", "").replace("```", "").strip()
    parsed = json.loads(clean_json)
    
    print(f"\n{'='*60}")
    print("PARÁMETROS PARSEADOS:")
    print(f"{'='*60}")
    print(json.dumps(parsed, indent=2))
    print(f"{'='*60}\n")
    
    return parsed

def busqueda_flexible_destino(destino_buscado, limite=10):
    """
    Realiza búsqueda flexible por destino cuando no hay coincidencia exacta.
    Busca coincidencias parciales (ej: "zona 17" encuentra "Zona 6,16,17,18").
    Soporta formatos abreviados: "z16", "z17" → "zona 16", "zona 17"
    OPTIMIZADO: Limita resultados para reducir consumo de tokens.
    """
    print(f"Búsqueda flexible activada para destino: '{destino_buscado}' (límite: {limite})")
    
    # Hacer scan con límite para reducir datos leídos
    response = table.scan(
        Limit=limite * 3  # Escanea 3x el límite para tener margen después de filtrar
    )
    items_todos = response.get('Items', [])
    
    # Normalizar búsqueda (minúsculas, sin espacios extra)
    destino_normalizado = destino_buscado.lower().strip()
    
    # Detectar y extraer números de zonas abreviadas (z16, z17, etc.)
    # Patrón: "z" seguido de uno o más dígitos
    zonas_abreviadas = re.findall(r'z(\d+)', destino_normalizado)
    
    # Crear variantes de búsqueda para zonas
    variantes_busqueda = [destino_normalizado]
    if zonas_abreviadas:
        # Agregar variantes: "zona 16", "16", etc.
        for zona_num in zonas_abreviadas:
            variantes_busqueda.append(f"zona {zona_num}")
            variantes_busqueda.append(zona_num)
        print(f"Zonas detectadas: {zonas_abreviadas} → Variantes: {variantes_busqueda}")
    
    # Filtrar items que contengan el destino buscado
    items_coincidentes = []
    for item in items_todos:
        # Detener cuando se alcanza el límite
        if len(items_coincidentes) >= limite:
            break
            
        destino_item = item.get('destino', '').lower()
        
        # 1. Coincidencia directa con cualquier variante
        if any(variante in destino_item for variante in variantes_busqueda):
            items_coincidentes.append(item)
            continue
        
        # 2. Coincidencia por palabras individuales
        palabras_buscadas = destino_normalizado.replace(',', ' ').split()
        palabras_item = destino_item.replace(',', ' ').split()
        
        if any(palabra in palabras_item for palabra in palabras_buscadas if palabra):
            items_coincidentes.append(item)
            continue
        
        # 3. Coincidencia específica para números de zona
        # Si el usuario busca "z16" y el item tiene "zona 6,16,17,18"
        if zonas_abreviadas:
            # Extraer todos los números del destino del item
            numeros_en_item = re.findall(r'\d+', destino_item)
            if any(zona_num in numeros_en_item for zona_num in zonas_abreviadas):
                items_coincidentes.append(item)
                continue
    
    print(f"Encontrados {len(items_coincidentes)} items con búsqueda flexible")
    return items_coincidentes

def paso_2_ejecutar_dynamo(params):
    """
    Ejecuta la query usando boto3.dynamodb.conditions correctamente.
    MEJORADO: Nunca devuelve vacío, hace scan completo como último recurso.
    Incluye búsqueda flexible para destinos parciales.
    """
    index_name = params.get("index")
    origen = params.get("origen")
    destino = params.get("destino")
    proveedor_filter = params.get("proveedor_filter")
    peso_kg = params.get("peso_kg")
    busqueda_amplia = params.get("busqueda_amplia", False)
    
    print(f"\n{'='*60}")
    print(f"🎯 EJECUTANDO QUERY EN ÍNDICE: {index_name}")
    print(f"{'='*60}")
    print(f"Origen: {origen}, Destino: {destino}, Proveedor: {proveedor_filter}, Peso: {peso_kg}")
    print(f"Búsqueda amplia: {busqueda_amplia}")
    print(f"{'='*60}\n")
    
    try:
        items = []
        busqueda_exacta_fallo = False
        metodo_busqueda = ""
        
        # ESTRATEGIA 1: Query con índice específico
        if not busqueda_amplia:
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
            
            # Ejecutar la consulta con índice
            if query_params:
                print(f"✅ Query con índice {index_name}")
                response = table.query(**query_params)
                items = response.get('Items', [])
                metodo_busqueda = f"Query directa ({index_name})"
                print(f"Items recuperados: {len(items)}")
        
        # ESTRATEGIA 2: Si no hay resultados exactos, búsqueda flexible por destino
        if len(items) == 0 and destino and not busqueda_amplia:
            busqueda_exacta_fallo = True
            print("🔍 No se encontraron coincidencias exactas, intentando búsqueda flexible...")
            items = busqueda_flexible_destino(destino, limite=20)
            metodo_busqueda = "Búsqueda flexible por destino"
        
        # ESTRATEGIA 3: Si todavía no hay resultados, hacer SCAN COMPLETO (último recurso)
        if len(items) == 0:
            print("⚠️ Búsqueda específica sin resultados. Haciendo SCAN COMPLETO de la tabla...")
            response = table.scan()
            items = response.get('Items', [])
            metodo_busqueda = "Scan completo de tabla (fallback inteligente)"
            print(f"📊 Scan completo recuperó {len(items)} registros totales")
        
        # FILTRADO INTELIGENTE EN PYTHON (post-query)
        items_originales = len(items)
        
        # 1. Filtrar por origen si se especificó y se hizo búsqueda flexible
        if (busqueda_exacta_fallo or busqueda_amplia or "Scan" in metodo_busqueda) and origen and len(items) > 0:
            items_antes = len(items)
            items = [item for item in items if origen.lower() in item.get('origen', '').lower()]
            print(f"🔍 Filtrado por origen '{origen}': {items_antes} → {len(items)} items")
        
        # 2. Filtrar por destino si se especificó y es scan completo
        if "Scan" in metodo_busqueda and destino and len(items) > 0:
            items_antes = len(items)
            # Búsqueda flexible en destino
            items_filtrados = []
            for item in items:
                destino_item = item.get('destino', '').lower()
                destino_busqueda = destino.lower()
                # Coincidencia parcial
                if destino_busqueda in destino_item or any(palabra in destino_item for palabra in destino_busqueda.split()):
                    items_filtrados.append(item)
            items = items_filtrados if items_filtrados else items  # Si no hay coincidencias, mantener todos
            print(f"🔍 Filtrado por destino '{destino}': {items_antes} → {len(items)} items")
        
        # 3. Filtrar por proveedor SOLO si se especificó
        if proveedor_filter and len(items) > 0:
            items_antes = len(items)
            items = [item for item in items if proveedor_filter.lower() in item.get('proveedor', '').lower()]
            print(f"🔍 Filtrado por proveedor '{proveedor_filter}': {items_antes} → {len(items)} items")
        
        # 4. Verificar que tengan rangos de precios (no filtrar si no hay peso)
        if len(items) > 0:
            items_antes = len(items)
            items = [item for item in items if item.get('rango_base_precios')]
            if items_antes != len(items):
                print(f"🔍 Filtrado por existencia de rangos: {items_antes} → {len(items)} items")
        
        print(f"\n{'='*60}")
        print(f"✅ RESULTADO FINAL:")
        print(f"{'='*60}")
        print(f"Método usado: {metodo_busqueda}")
        print(f"Items encontrados: {len(items)}")
        if items:
            print(f"\n📋 MUESTRA DE RESULTADOS:")
            for i, item in enumerate(items[:3], 1):  # Mostrar hasta 3 primeros
                print(f"  {i}. {item.get('proveedor')} | {item.get('origen')} → {item.get('destino')}")
        print(f"{'='*60}\n")
        
        return items
        
    except Exception as e:
        print(f"❌ Error ejecutando DynamoDB: {e}")
        import traceback
        traceback.print_exc()
        # ÚLTIMO RECURSO: Intentar scan básico
        try:
            print("🆘 Intentando scan de emergencia...")
            response = table.scan()
            return response.get('Items', [])
        except:
            return []

def extraer_datos_relevantes(items, peso_kg=None):
    """
    OPTIMIZACIÓN: Extrae solo los campos necesarios para reducir tokens enviados al LLM.
    Filtra rangos de precios según el peso especificado.
    """
    datos_simplificados = []
    
    for item in items:
        # Extraer solo rangos relevantes si hay peso
        rangos_relevantes = item.get('rango_base_precios', [])
        
        if peso_kg and rangos_relevantes:
            # Filtrar solo rangos aplicables al peso + tarifa base
            rangos_filtrados = []
            for rango in rangos_relevantes:
                min_kg = float(rango.get('min_kg', 0))
                max_kg = float(rango.get('max_kg', float('inf')))
                
                # Incluir tarifa base + rango donde cae el peso
                if rango.get('concepto') == 'Tarifa Base' or (min_kg <= peso_kg <= max_kg):
                    rangos_filtrados.append({
                        'min_kg': min_kg,
                        'max_kg': max_kg,
                        'costo': float(rango.get('costo', 0)),
                        'concepto': rango.get('concepto')
                    })
            rangos_relevantes = rangos_filtrados
        else:
            # Sin peso, convertir todos los rangos pero simplificados
            rangos_relevantes = [
                {
                    'min_kg': float(r.get('min_kg', 0)),
                    'max_kg': float(r.get('max_kg', 0)),
                    'costo': float(r.get('costo', 0)),
                    'concepto': r.get('concepto')
                }
                for r in rangos_relevantes
            ]
        
        # Construir objeto simplificado
        datos_simplificados.append({
            'origen': item.get('origen'),
            'destino': item.get('destino'),
            'proveedor': item.get('proveedor'),
            'dias_libres': float(item.get('dias_libres', 0)),
            'estadia': float(item.get('estadia', 0)),
            'fianza': float(item.get('fianza', 0)),
            'rangos': rangos_relevantes,
            'custodio_comsi': float(item.get('custodio_comsi', 0)),
            'custodio_yantarni': float(item.get('custodio_yantarni', 0)),
            'condiciones_aduana': item.get('condiciones_aduana', ''),
            'costo_tramite_aduana': float(item.get('tramite_aduana', 0)),
            'condiciones_cominter': item.get('condiciones_de_aduana_cominter', ''),
            'costo_tramite_cominter': float(item.get('tramite_de_aduana_cominter', 0))

        })
    
    return datos_simplificados

def calcular_costos_cotizacion(item, peso_kg=None, custodio_tipo=None, custodio_cantidad=0, dias_estadia=0):
    """
    Calcula programáticamente todos los costos de una cotización.
    NO delega cálculos matemáticos a la IA para evitar errores.
    
    Args:
        item: Diccionario con datos de la tarifa
        peso_kg: Peso solicitado (opcional)
        custodio_tipo: Tipo de custodio solicitado: "comsi" o "yantarni" (opcional)
        custodio_cantidad: Cantidad de unidades de custodio (opcional)
        dias_estadia: Días de estadía que exceden los días libres (opcional)
    
    Returns:
        dict: {
            "tarifa_base": float,
            "sobrepeso": float,
            "sobrepeso_concepto": str,
            "custodio": float,
            "custodio_detalle": dict,
            "dias_libres": int,
            "costo_estadia_diario": float,
            "dias_estadia": int,
            "estadia": float,
            "fianza": float,
            "tramite_aduana": float,
            "tramite_cominter": float,
            "total": float,
            "desglose": str
        }
    """
    resultado = {
        "tarifa_base": 0.0,
        "sobrepeso": 0.0,
        "sobrepeso_concepto": "",
        "custodio": 0.0,
        "custodio_detalle": {},
        "dias_libres": int(item.get('dias_libres', 0)),
        "costo_estadia_diario": float(item.get('estadia', 0.0)),
        "dias_estadia": dias_estadia,
        "estadia": 0.0,
        "fianza": item.get('fianza', 0.0),
        "tramite_aduana": item.get('costo_tramite_aduana', 0.0),
        "tramite_cominter": item.get('costo_tramite_cominter', 0.0),
        "total": 0.0,
        "desglose": ""
    }
    
    rangos = item.get('rangos', [])
    
    # 1. CALCULAR TARIFA BASE Y SOBREPESO
    if rangos:
        tarifa_base_encontrada = False
        sobrepeso_encontrado = False
        
        for rango in rangos:
            min_kg = rango.get('min_kg', 0)
            max_kg = rango.get('max_kg', float('inf'))
            costo = rango.get('costo', 0)
            concepto = rango.get('concepto', '')
            
            # Identificar tarifa base (SIEMPRE, con o sin peso)
            if concepto == 'Tarifa Base':
                resultado["tarifa_base"] = float(costo)
                tarifa_base_encontrada = True
            
            # Identificar sobrepeso (SOLO si hay peso especificado y cae en ese rango)
            elif peso_kg and min_kg <= peso_kg <= max_kg and 'Sobrepeso' in concepto:
                resultado["sobrepeso"] = float(costo)
                resultado["sobrepeso_concepto"] = concepto
                sobrepeso_encontrado = True
        
        # Si hay peso pero no se encontró sobrepeso, significa que está en tarifa base
        if peso_kg and not sobrepeso_encontrado:
            resultado["sobrepeso"] = 0.0
            resultado["sobrepeso_concepto"] = "No aplica (dentro de tarifa base)"
        
        # Si NO hay peso, buscar el rango base que corresponda al peso mínimo
        if not peso_kg and not tarifa_base_encontrada:
            # Buscar el primer rango disponible
            for rango in rangos:
                costo = rango.get('costo', 0)
                if costo > 0:
                    resultado["tarifa_base"] = float(costo)
                    break
    
    # 2. CALCULAR CUSTODIO
    if custodio_tipo and custodio_cantidad > 0:
        costo_unitario = 0.0
        if custodio_tipo.lower() == 'comsi':
            costo_unitario = item.get('custodio_comsi', 0.0)
        elif custodio_tipo.lower() == 'yantarni':
            costo_unitario = item.get('custodio_yantarni', 0.0)
        
        resultado["custodio"] = float(costo_unitario) * custodio_cantidad
        resultado["custodio_detalle"] = {
            "tipo": custodio_tipo,
            "costo_unitario": float(costo_unitario),
            "cantidad": custodio_cantidad,
            "total": resultado["custodio"]
        }
    
    # 3. CALCULAR ESTADÍA (solo si excede días libres)
    if dias_estadia > 0:
        resultado["estadia"] = float(resultado["costo_estadia_diario"]) * dias_estadia
    
    # 4. CALCULAR TOTAL
    resultado["total"] = (
        resultado["tarifa_base"] +
        resultado["sobrepeso"] +
        resultado["custodio"] +
        resultado["estadia"] +
        resultado["fianza"] +
        resultado["tramite_aduana"] +
        resultado["tramite_cominter"]
    )
    
    # 5. GENERAR DESGLOSE
    componentes = []
    if resultado["tarifa_base"] > 0:
        componentes.append(f"Tarifa Base (Q{resultado['tarifa_base']:.2f})")
    if resultado["sobrepeso"] > 0:
        componentes.append(f"Sobrepeso (Q{resultado['sobrepeso']:.2f})")
    if resultado["custodio"] > 0:
        componentes.append(f"Custodio (Q{resultado['custodio']:.2f})")
    if resultado["estadia"] > 0:
        componentes.append(f"Estadía {dias_estadia} días (Q{resultado['estadia']:.2f})")
    if resultado["fianza"] > 0:
        componentes.append(f"Fianza (Q{resultado['fianza']:.2f})")
    if resultado["tramite_aduana"] > 0:
        componentes.append(f"Trámite Aduana (Q{resultado['tramite_aduana']:.2f})")
    if resultado["tramite_cominter"] > 0:
        componentes.append(f"Trámite Cominter (Q{resultado['tramite_cominter']:.2f})")
    
    resultado["desglose"] = " + ".join(componentes)

    print(f"\n{'='*60}")
    print(f"💰 CÁLCULO PROGRAMÁTICO DE COSTOS:")
    print(f"{'='*60}")
    print(f"Tarifa Base: Q{resultado['tarifa_base']:.2f}")
    print(f"Sobrepeso: Q{resultado['sobrepeso']:.2f} ({resultado['sobrepeso_concepto']})")
    print(f"Custodio: Q{resultado['custodio']:.2f}")
    print(f"Días libres: {resultado['dias_libres']} días")
    print(f"Estadía: Q{resultado['estadia']:.2f} ({dias_estadia} días x Q{resultado['costo_estadia_diario']:.2f}/día)")
    print(f"Fianza: Q{resultado['fianza']:.2f}")
    print(f"Trámite Aduana: Q{resultado['tramite_aduana']:.2f}")
    print(f"Trámite Cominter: Q{resultado['tramite_cominter']:.2f}")
    print(f"{'='*60}")
    print(f"TOTAL: Q{resultado['total']:.2f}")
    print(f"{'='*60}\n")

    return resultado

def seleccionar_mejor_opcion(datos_optimizados, peso_kg=None):
    """
    Selecciona el mejor proveedor basándose en precio y condiciones.
    
    Args:
        datos_optimizados: Lista de opciones de tarifas
        peso_kg: Peso para calcular costos
    
    Returns:
        dict: La mejor opción seleccionada
    """
    if len(datos_optimizados) == 1:
        return datos_optimizados[0]
    
    print(f"\n🤖 SELECCIÓN INTELIGENTE DE PROVEEDOR:")
    print(f"{'='*60}")
    
    # Calcular costo total estimado para cada opción
    opciones_con_costo = []
    
    for opcion in datos_optimizados:
        costo_estimado = 0.0
        
        # Tarifa base
        for rango in opcion.get('rangos', []):
            if rango.get('concepto') == 'Tarifa Base':
                costo_estimado += rango.get('costo', 0)
                break
        
        # Sobrepeso si aplica
        if peso_kg:
            for rango in opcion.get('rangos', []):
                if 'Sobrepeso' in rango.get('concepto', ''):
                    min_kg = rango.get('min_kg', 0)
                    max_kg = rango.get('max_kg', float('inf'))
                    if min_kg <= peso_kg <= max_kg:
                        costo_estimado += rango.get('costo', 0)
                        break
        
        # Costos adicionales
        costo_estimado += opcion.get('fianza', 0)
        costo_estimado += opcion.get('costo_tramite_aduana', 0)
        costo_estimado += opcion.get('costo_tramite_cominter', 0)
        
        opciones_con_costo.append({
            'opcion': opcion,
            'costo_total': costo_estimado,
            'proveedor': opcion.get('proveedor'),
            'dias_libres': opcion.get('dias_libres', 0)
        })
    
    # Ordenar por costo total (menor a mayor)
    opciones_con_costo.sort(key=lambda x: x['costo_total'])
    
    # Mostrar comparación
    for i, opc in enumerate(opciones_con_costo[:3], 1):
        print(f"{i}. {opc['proveedor']}: Q{opc['costo_total']:.2f} ({opc['dias_libres']} días libres)")
    
    mejor_opcion = opciones_con_costo[0]['opcion']
    print(f"\n✅ SELECCIONADO: {opciones_con_costo[0]['proveedor']} (más económico)")
    print(f"{'='*60}\n")
    
    return mejor_opcion

def generar_recomendacion_inteligente(pregunta, datos_optimizados, peso_kg=None):
    """
    Genera una recomendación comparativa inteligente entre múltiples proveedores.
    
    Args:
        pregunta: Pregunta del usuario
        datos_optimizados: Lista de opciones
        peso_kg: Peso especificado
    
    Returns:
        str: Recomendación en formato Markdown
    """
    print(f"\n📊 GENERANDO RECOMENDACIÓN COMPARATIVA")
    
    # Calcular costos para cada opción
    comparativas = []
    
    for opcion in datos_optimizados[:5]:  # Máximo 5 opciones
        # Calcular costo básico (sin custodio ni estadía extra)
        costos = calcular_costos_cotizacion(opcion, peso_kg, None, 0, 0)
        
        comparativas.append({
            'proveedor': opcion.get('proveedor'),
            'origen': opcion.get('origen'),
            'destino': opcion.get('destino'),
            'tarifa_base': costos['tarifa_base'],
            'sobrepeso': costos['sobrepeso'],
            'total_basico': costos['total'],
            'dias_libres': costos['dias_libres'],
            'estadia_diaria': costos['costo_estadia_diario'],
            'fianza': costos['fianza']
        })
    
    # Ordenar por total (menor a mayor)
    comparativas.sort(key=lambda x: x['total_basico'])
    
    # Generar respuesta en Markdown
    respuesta = f"# 🚛 Comparativa de Opciones\n\n"
    respuesta += f"Encontré **{len(comparativas)} opciones** para tu ruta"
    
    if peso_kg:
        respuesta += f" con **{peso_kg:,} kg**"
    
    respuesta += ":\n\n"
    
    for i, comp in enumerate(comparativas, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📦"
        respuesta += f"## {emoji} {i}. {comp['proveedor']}\n"
        respuesta += f"**Ruta:** {comp['origen']} → {comp['destino']}\n\n"
        respuesta += f"- **Tarifa base:** Q{comp['tarifa_base']:,.2f}\n"
        
        if comp['sobrepeso'] > 0:
            respuesta += f"- **Sobrepeso:** Q{comp['sobrepeso']:,.2f}\n"
        
        respuesta += f"- **Fianza:** Q{comp['fianza']:,.2f}\n"
        respuesta += f"- **Días libres:** {int(comp['dias_libres'])} días\n"
        respuesta += f"- **Estadía:** Q{comp['estadia_diaria']:,.2f}/día\n"
        respuesta += f"- **💰 TOTAL:** Q{comp['total_basico']:,.2f}\n\n"
    
    # Recomendación final
    mejor = comparativas[0]
    respuesta += f"---\n\n"
    respuesta += f"### ✅ Recomendación\n\n"
    respuesta += f"**{mejor['proveedor']}** ofrece la tarifa más competitiva con un total de **Q{mejor['total_basico']:,.2f}**"
    
    if mejor['dias_libres'] > 0:
        respuesta += f", incluyendo {int(mejor['dias_libres'])} días libres de estadía"
    
    respuesta += ".\n\n"
    respuesta += f"¿Te gustaría que genere una cotización formal con **{mejor['proveedor']}**? 📋"
    
    return respuesta

def paso3_1_generar_resumen_respuesta_natural(pregunta, items):
    """
    Genera un resumen en lenguaje natural de los datos encontrados.
    Útil para cuando hay múltiples opciones y se necesita un resumen comparativo.
    
    Args:
        pregunta: Pregunta del usuario
        items: Lista de datos simplificados de tarifas
    
    Returns:
        str: Resumen en lenguaje natural sin XML
    """
    data_context = json.dumps(items, indent=2)
    
    system_prompt = """
    Eres un Asistente Experto en Logística y Tarifas. 
    
    El usuario ha solicitado información que coincide con MÚLTIPLES opciones de tarifas.
    Tu trabajo es generar un RESUMEN COMPARATIVO claro y conciso en lenguaje natural.
    
    FORMATO DE SALIDA:
    - Usa Markdown para listas y negritas
    - NUNCA uses etiquetas XML
    - Presenta las opciones de forma comparativa
    - Destaca diferencias clave: precio, proveedor, condiciones
    - Sé conciso pero informativo
    
    REGLAS:
    1. Identifica las principales diferencias entre las opciones
    2. Si hay diferentes proveedores, compáralos
    3. Si hay diferentes rutas, menciónalas
    4. Incluye rangos de precios relevantes
    5. Si el usuario especificó un peso, calcula costos para ese peso
    6. Menciona condiciones importantes (días libres, estadía, etc.)
    
    EJEMPLO DE FORMATO:
    Encontré **3 opciones** para tu ruta:
    
    **1. Proveedor A** - Puerto Quetzal → Mixco
    - Tarifa base: Q2,800 (hasta 25,000 kg)
    - Días libres: 5 días
    - Estadía: Q50/día
    
    **2. Proveedor B** - Puerto Quetzal → Mixco  
    - Tarifa base: Q2,650 (hasta 24,000 kg)
    - Días libres: 3 días
    - Estadía: Q75/día
    
    La opción más económica es **Proveedor B** si entregas en los primeros 3 días.
    """
    
    user_content = f"""
PREGUNTA DEL USUARIO: "{pregunta}"

DATOS RECUPERADOS (múltiples opciones):
{data_context}

Genera un resumen comparativo claro en lenguaje natural.
NO uses formato XML, solo texto con Markdown.
"""
    
    respuesta = invoke_nova_pro(system_prompt, user_content)
    
    print(f"\n{'='*60}")
    print(f"📊 RESUMEN COMPARATIVO GENERADO (múltiples opciones)")
    print(f"{'='*60}\n")
    
    return respuesta


_SYSTEM_PROMPT_COTIZACION = """
    Eres un Asistente Experto en Logística y Tarifas. Tu trabajo es generar un XML de cotización usando los datos y COSTOS YA CALCULADOS proporcionados.

    IMPORTANTE: Los cálculos matemáticos YA ESTÁN HECHOS en el campo 'costos_calculados'. NO recalcules, solo usa esos valores.

    FORMATO DE SALIDA (XML ESTRUCTURADO):

    <respuesta>
        <cotizacion>
            <proveedor>Nombre del Proveedor</proveedor>

            <ruta>
                <origen>Puerto Quetzal</origen>
                <destino>Mixco</destino>
            </ruta>

            <unidad>
                <tipo>Contenedor</tipo>
                <peso_solicitado>26000</peso_solicitado>
                <peso_unidad>kg</peso_unidad>
            </unidad>

            <tarifa_base>
                <monto>2800.00</monto>
                <moneda>GTQ</moneda>
                <rango>0 - 20999 kg</rango>
            </tarifa_base>

            <sobrepeso>
                <aplica>true</aplica>
                <monto>350.00</monto>
                <moneda>GTQ</moneda>
                <descripcion>Sobrepeso nivel 1</descripcion>
            </sobrepeso>

            <custodio>
                <tipo>Comsi</tipo>
                <costo_unitario>150.00</costo_unitario>
                <cantidad_unidades>2</cantidad_unidades>
                <costo_total>300.00</costo_total>
                <moneda>GTQ</moneda>
            </custodio>

            <costos_adicionales>
                <costo>
                    <concepto>Días libres</concepto>
                    <valor>5</valor>
                    <unidad>días</unidad>
                </costo>
                <costo>
                    <concepto>Estadía</concepto>
                    <valor>50.00</valor>
                    <unidad>GTQ/día</unidad>
                </costo>
                <costo>
                    <concepto>Fianza</concepto>
                    <valor>500.00</valor>
                    <unidad>GTQ</unidad>
                </costo>
                <costo>
                    <concepto>Trámite de aduana</concepto>
                    <valor>200.00</valor>
                    <unidad>GTQ</unidad>
                </costo>
                <costo>
                    <concepto>Trámite Cominter</concepto>
                    <valor>150.00</valor>
                    <unidad>GTQ</unidad>
                </costo>
            </costos_adicionales>

            <resumen_costos>
                <total>4000.00</total>
                <moneda>GTQ</moneda>
                <detalles>Tarifa Base + Sobrepeso + Custodio + Estadía + Fianza + Trámites</detalles>
                <condiciones_aduana>HASTA 10 LINEAS Q0.75 ADICIONALES</condiciones_aduana>
                <condiciones_cominter>HASTA 50 LINEAS ADICIONALES Q2.50</condiciones_cominter>
            </resumen_costos>
        </cotizacion>
    </respuesta>

    REGLAS IMPORTANTES:
    1. USA EXACTAMENTE los valores de 'costos_calculados'
    2. El <total> DEBE ser igual a costos_calculados["total"]
    3. NO recalcules, solo estructura el XML
    4. Si sobrepeso es 0, pon <aplica>false</aplica>
    5. Si no hay custodio, omite <custodio>
    6. Incluye condiciones_aduana y condiciones_cominter
    7. NUNCA inventes datos
    8. Devuelve SOLO el XML, sin texto adicional
    """


def _detectar_custodio(pregunta_lower: str) -> tuple:
    """Detecta tipo y cantidad de custodio mencionados en la pregunta."""
    if 'custodio' not in pregunta_lower:
        return None, 0

    if 'comsi' in pregunta_lower:
        tipo = 'comsi'
    elif 'yantarni' in pregunta_lower:
        tipo = 'yantarni'
    else:
        tipo = 'comsi'

    numeros = re.findall(r'\b\d+\b', pregunta_lower)
    cantidad = next((int(n) for n in reversed(numeros) if int(n) < 100), 0)
    return tipo, cantidad


def _detectar_dias_estadia(pregunta_lower: str, dias_libres: int) -> int:
    """Devuelve días de estadía que exceden los días libres del proveedor."""
    if not any(kw in pregunta_lower for kw in ('estadia', 'días', 'dia')):
        return 0

    match = re.search(r'(\d+)\s*d[ií]as?', pregunta_lower)
    if not match:
        return 0

    dias = int(match.group(1))
    return max(0, dias - dias_libres)


def _seleccionar_item_cotizacion(pregunta_lower: str, datos_optimizados: list, peso_kg) -> dict:
    """Devuelve el item a cotizar: el proveedor mencionado explícitamente o el más económico."""
    for opcion in datos_optimizados:
        if opcion.get('proveedor', '').lower() in pregunta_lower:
            print(f"✅ Proveedor específico detectado: {opcion.get('proveedor')}")
            return opcion
    return seleccionar_mejor_opcion(datos_optimizados, peso_kg)


def paso_3_generar_respuesta_natural(pregunta, items, peso_kg=None, conversation_history=None):
    """
    Toma los datos crudos y responde la pregunta original usando lógica de negocio.
    MEJORADO: Recomienda proveedores, compara opciones, nunca dice "no encontrado".
    Los cálculos matemáticos se realizan programáticamente, no por la IA.
    
    Args:
        pregunta: Pregunta del usuario
        items: Resultados de DynamoDB
        peso_kg: Peso especificado (opcional)
        conversation_history: Historial de mensajes (opcional, del frontend)
    
    Returns:
        str: Respuesta en formato XML o comparativa según el caso
    """
    # MANEJO INTELIGENTE DE RESULTADOS VACÍOS
    if not items:
        return """Estoy analizando todas las opciones disponibles en nuestra base de datos para encontrar la mejor alternativa para tu solicitud. ¿Podrías darme más detalles sobre la ruta que necesitas (origen y destino)?"""

    # OPTIMIZACIÓN: Extraer solo datos relevantes
    datos_optimizados = extraer_datos_relevantes(items, peso_kg)
    
    # DECISIÓN INTELIGENTE: ¿Una cotización específica o comparación de opciones?
    pregunta_lower = pregunta.lower()
    
    # Detectar si el usuario solicita una COTIZACIÓN FORMAL (XML)
    solicita_cotizacion_xml = any(keyword in pregunta_lower for keyword in [
        'cotización', 'cotizacion', 'genera', 'dame la cotización', 'quiero cotización',
        'cotiza', 'genera cotización', 'cotización formal', 'cotización de', 'cotización para',
        'dame cotización', 'hazme cotización', 'xml', 'formal'
    ])
    
    # Detectar si el usuario solicita COMPARACIÓN
    solicita_comparacion = any(keyword in pregunta_lower for keyword in [
        'mejor', 'opciones', 'compara', 'recomienda', 'cual', 'más barato', 'más económico', 
        'diferencia', 'comparativa', 'compárame', 'cuál es mejor'
    ])
    
    # LÓGICA DE DECISIÓN MEJORADA:
    # 1. Si pide cotización XML explícitamente → Generar XML (aunque haya múltiples opciones)
    # 2. Si hay 1 sola opción → Generar XML siempre
    # 3. Si hay múltiples opciones Y pide comparación → Generar comparativa
    # 4. Si hay muchas opciones (>3) Y NO pide cotización específica → Generar comparativa
    
    generar_comparativa = (
        len(datos_optimizados) > 1 and 
        not solicita_cotizacion_xml and 
        (solicita_comparacion or len(datos_optimizados) > 3)
    )
    
    if generar_comparativa:
        print(f"🔀 MÚLTIPLES OPCIONES ({len(datos_optimizados)}): Generando comparativa inteligente")
        return generar_recomendacion_inteligente(pregunta, datos_optimizados, peso_kg)
    
    # Si llega aquí, generar cotización XML
    print(f"📋 GENERANDO COTIZACIÓN XML (solicitud específica o única opción)")
    
    # PASO 1: SELECCIONAR PROVEEDOR Y CALCULAR COSTOS
    item_principal = _seleccionar_item_cotizacion(pregunta_lower, datos_optimizados, peso_kg)
    dias_libres = item_principal.get('dias_libres', 0)
    custodio_tipo, custodio_cantidad = _detectar_custodio(pregunta_lower)
    dias_estadia = _detectar_dias_estadia(pregunta_lower, dias_libres)

    costos_calculados = calcular_costos_cotizacion(
        item_principal,
        peso_kg,
        custodio_tipo,
        custodio_cantidad,
        dias_estadia,
    )
    
    # PASO 2: Preparar datos para la IA con costos ya calculados
    data_context = json.dumps([item_principal], indent=2)  # Solo el seleccionado
    costos_context = json.dumps(costos_calculados, indent=2)
    
    print(f"\n{'='*60}")
    print(f"DATOS ENVIADOS AL LLM:")
    print(f"{'='*60}")
    print(f"Proveedor seleccionado: {item_principal.get('proveedor')}")
    print(f"Peso especificado: {peso_kg} kg" if peso_kg else "Peso: No especificado")
    print(f"Custodio: {custodio_tipo} x {custodio_cantidad}" if custodio_tipo else "Custodio: No solicitado")
    print(f"Días estadía: {dias_estadia} días" if dias_estadia > 0 else "Estadía: No aplica")
    print(f"Total calculado: Q{costos_calculados['total']:.2f}")
    print(f"{'='*60}\n")

    user_content = f"""
PREGUNTA DEL USUARIO: "{pregunta}"

DATOS DEL PROVEEDOR SELECCIONADO:
{data_context}

COSTOS YA CALCULADOS (USA ESTOS VALORES EXACTOS):
{costos_context}

Genera el XML de cotización usando EXACTAMENTE los valores calculados.
"""
    
    # Generar respuesta
    respuesta = invoke_nova_pro(_SYSTEM_PROMPT_COTIZACION, user_content, conversation_history)
    
    # Limpiar respuesta
    respuesta_limpia = respuesta.strip()
    if respuesta_limpia.startswith("```xml"):
        respuesta_limpia = respuesta_limpia.replace("```xml", "").replace("```", "").strip()

    # Inyectar tarifa_id y tipo en el XML para poder guardar la cotización
    item_id = item_principal.get('id', '')
    if '</cotizacion>' in respuesta_limpia:
        inject = f'  <tarifa_id>{item_id}</tarifa_id>\n    <tipo>terrestre</tipo>\n  </cotizacion>'
        respuesta_limpia = respuesta_limpia.replace('</cotizacion>', inject, 1)

    print(f"\n{'='*60}")
    print(f"RESPUESTA XML GENERADA:")
    print(f"{'='*60}")
    print(respuesta_limpia[:500] + "..." if len(respuesta_limpia) > 500 else respuesta_limpia)
    print(f"{'='*60}\n")
    
    return respuesta_limpia


def handler(event, context):
    """
    Handler optimizado para API Gateway con clasificación inteligente de intención.
    El frontend maneja la persistencia de sesiones y el historial de mensajes.
    
    REQUEST FORMAT:
    {
        "query": "¿Cuánto cuesta enviar 26,000 kg de Puerto Quetzal a Mixco?",
        "conversation_history": [  // REQUERIDO para clasificación inteligente
            {
                "role": "user",
                "content": [{"text": "pregunta anterior"}]
            },
            {
                "role": "assistant",
                "content": [{"text": "respuesta anterior"}]
            }
        ]
    }
    
    RESPONSE FORMAT:
    {
        "respuesta": "...",
        "tipo": "cotizacion" | "conversacional",
        "items_found": 1,
        "requiere_db": true | false
    }
    """
    try:
        # Parsear el body del request
        body = json.loads(event.get('body', '{}'))
        user_query = body.get('query')
        conversation_history = body.get('conversation_history', [])
        
        if not user_query:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
                    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
                },
                "body": json.dumps({"error": "Falta el campo 'query'"})
            }

        print(f"\n{'='*80}")
        print(f"📥 NUEVA PETICIÓN")
        print(f"{'='*80}")
        print(f"Pregunta: {user_query}")
        print(f"Historial: {len(conversation_history)} mensajes")
        print(f"{'='*80}\n")

        # **PASO 0: CLASIFICACIÓN INTELIGENTE DE INTENCIÓN**
        clasificacion = paso_0_clasificar_intencion(user_query, conversation_history)
        tipo_pregunta = clasificacion.get('tipo')
        requiere_db = clasificacion.get('requiere_db')
        
        # **RUTA 1: PREGUNTA CONVERSACIONAL (sin consulta DB)**
        if tipo_pregunta == "conversacional" and not requiere_db:
            print(f"\n🔄 RUTA CONVERSACIONAL ACTIVADA (ahorro de costos DB)")
            respuesta_final = manejar_pregunta_conversacional(user_query, conversation_history)
            
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
                    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
                },
                "body": json.dumps({
                    "respuesta": respuesta_final,
                    "tipo": tipo_pregunta,
                    "items_found": 0,
                    "requiere_db": False,
                    "razon": clasificacion.get('razon', '')
                }, cls=DecimalEncoder)
            }
        
        # **RUTA 2: COTIZACIÓN (consulta DB completa)**
        print(f"\n🔍 RUTA COTIZACIÓN ACTIVADA (consulta DynamoDB)")
        
        # 1. INTELIGENCIA DE BASE DE DATOS (Text-to-Query)
        db_params = paso_1_generar_query(user_query, conversation_history)
        print(f"Estrategia DB generada: {db_params}")
        
        # 2. OPTIMIZACIÓN: Extraer peso para filtrado inteligente
        peso_kg = db_params.get('peso_kg')

        # 3. RECUPERACIÓN DE DATOS
        items = paso_2_ejecutar_dynamo(db_params)
        print(f"Registros encontrados: {len(items)}")

        # 4. INTELIGENCIA DE NEGOCIO (Data-to-Answer)
        respuesta_final = paso_3_generar_respuesta_natural(
            user_query, 
            items, 
            peso_kg,
            conversation_history
        )

        # Respuesta exitosa
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "respuesta": respuesta_final,
                "tipo": tipo_pregunta,
                "items_found": len(items),
                "requiere_db": True,
                "razon": clasificacion.get('razon', '')
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