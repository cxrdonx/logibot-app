import boto3
import json
import os
import re
import copy
from datetime import date as _date, timedelta
from decimal import Decimal
from boto3.dynamodb.conditions import Key

# --- CONFIGURACION ---
TABLE_NAME = os.environ.get('MARITIME_TABLE_NAME', 'MaritimeQuotations')
REGION = os.environ.get('REGION', 'us-east-1')
MODEL_ID = os.environ.get('MODEL_ID', 'amazon.nova-pro-v1:0')

dynamodb = boto3.resource('dynamodb', region_name=REGION)
table = dynamodb.Table(TABLE_NAME)
bedrock = boto3.client('bedrock-runtime', region_name=REGION)

# --- CORS HEADERS ---
CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
}

# --- NORMALIZACION DE PUERTOS CONOCIDOS ---
_PORT_NORMALIZATION = {
    "rotterdam": "NLRTM - ROTTERDAM, NETHERLANDS",
    "hamburgo": "DEHAM - HAMBURG, GERMANY",
    "hamburg": "DEHAM - HAMBURG, GERMANY",
    "amberes": "BEANR - ANTWERP, BELGIUM",
    "antwerp": "BEANR - ANTWERP, BELGIUM",
    "antwerpen": "BEANR - ANTWERP, BELGIUM",
    "puerto barrios": "GTPBR - PUERTO BARRIOS, GUATEMALA",
    "puerto quetzal": "GTQUE - PUERTO QUETZAL, GUATEMALA",
    "santo tomas de castilla": "GTSTC - SANTO TOMAS DE CASTILLA, GUATEMALA",
    "santo tomas": "GTSTC - SANTO TOMAS DE CASTILLA, GUATEMALA",
    "kingston": "JMKIN - KINGSTON, JAMAICA",
}

# --- CLASE AUXILIAR PARA JSON ---
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


# --- SCHEMA DE LA TABLA MARITIMA ---
_MARITIME_SCHEMA_INFO = """
ESTRUCTURA DE TABLA DYNAMODB ('MaritimeQuotations'):
- Partition Key: id (String, UUID)
- Atributos clave: origin_port, destination_port, shipping_line
- Atributos de fechas: dates.quote_date, dates.valid_from, dates.valid_till (ISO 8601)
- Routing: routing.origin_port, routing.destination_port, routing.via_port (transbordo, opcional)
- Logistics: logistics.shipping_line, logistics.transit_time_days
- Carga: commodities[] con fields: description, container_type, gross_weight, volume_cbm, hs_code, country_of_origin
- Precios: line_items[] con fields: description, quantity, unit, currency, unit_price, amount
- Total: total_amount (Number), currency (String, código ISO: EUR, USD, GBP, etc.)
- Contacto: prepared_by, requested_by, company.name, company.contact, company.address
- Términos: terms_and_conditions.exclusions[], carrier_conditions[], currency_notes, general_notes

ÍNDICES SECUNDARIOS GLOBALES (GSIs) DISPONIBLES:
1. IndexName: 'OriginPortIndex'      -> PK: 'origin_port'
2. IndexName: 'DestinationPortIndex' -> PK: 'destination_port'
3. IndexName: 'ShippingLineIndex'    -> PK: 'shipping_line'
"""

# --- SYSTEM PROMPT PRINCIPAL PARA ALCE ---
_ALCE_SYSTEM_PROMPT = """
Eres ALCE (AI Logistics & Customs Expert), un experto en logística marítima y análisis de tarifas.
Actúas como Forwarder/Pricing Analyst especializado en cotizaciones marítimas internacionales.

## TUS CAPACIDADES:

1. **EXTRACCIÓN Y ESTRUCTURACIÓN**: Extraes y estructuras cotizaciones marítimas de forma detallada.
2. **ANÁLISIS DE TEMPORALIDAD**: Validas fechas y períodos de vigencia de tarifas.
3. **DETECCIÓN DE TRANSBORDOS**: Identificas rutas con via_port y explicas el impacto en tiempos de tránsito.
4. **CÁLCULO DE TOTALES**: Aplicás la fórmula Total = Σ(Qi × Pi) + F_fijos para verificar y calcular montos.
5. **MANEJO MULTI-MONEDA**: Respetas la moneda declarada (EUR, USD, GBP, etc.) sin forzar conversiones.
6. **GENERACIÓN DE ALERTAS**: Detectas inconsistencias en fechas, montos y reglas de negocio.

## REGLAS DE NEGOCIO CRÍTICAS:

- **Fechas**: valid_till DEBE ser posterior a valid_from y a quote_date. Si no, generar ALERTA.
- **Cantidades**: quantity > 0 siempre. unit_price >= 0 siempre.
- **Total**: Debe ser la suma exacta de todos los line_items (Σ quantity × unit_price). Si hay discrepancia, alertar.
- **Transbordo**: Si existe via_port, la ruta NO es directa y los tiempos de tránsito deben reflejarlo.
- **Monedas**: NO forzar conversión EUR→USD. Respetar la moneda declarada. Solo convertir si se solicita explícitamente.
- **Códigos HS**: Identificar y validar códigos del Sistema Armonizado en commodities.

## FÓRMULA DE CÁLCULO:

Total = Σ(Qi × Pi) + F_fijos

Donde:
- Qi = Quantity del item i (número de contenedores, etc.)
- Pi = Unit Price aplicable a esa unidad
- F_fijos = Tarifas fijas por embarque (Handling Fee, Bill of Lading Fee, Documentation Fee)

## ALERTAS QUE DEBES GENERAR:

- ⚠️ ALERTA FECHA: "valid_till [fecha] es anterior a valid_from [fecha] → INCONSISTENCIA DETECTADA"
- ⚠️ ALERTA MONTO: "Line item [descripción]: quantity × unit_price = X pero amount = Y → DISCREPANCIA"
- ⚠️ ALERTA TOTAL: "Suma de line_items = X pero total_amount = Y → DISCREPANCIA"
- ⚠️ ALERTA MONEDA: "Moneda [código] no es un código ISO válido"
- ⚠️ ALERTA TRÁNSITO: "Transit time [N] días es [muy largo/muy corto] para esta ruta"

## FORMATO DE RESPUESTA:

- Usa Markdown para estructura y claridad
- NUNCA uses etiquetas XML en las respuestas conversacionales
- Presenta tablas de precios de forma clara cuando corresponda
- Sé preciso con los números (2 decimales mínimo para montos)
- Incluye alertas de validación cuando detectes inconsistencias
- Si hay transbordo (via_port), mencionarlo explícitamente

## INSTRUCCIONES ESPECIALES:

- Si el usuario pregunta por una ruta específica, muestra las tarifas disponibles en la base de datos
- Si el usuario pide calcular un total, verifica contra la fórmula y alerta si hay discrepancia
- Si el usuario pide comparar navieras, presenta tabla comparativa con tiempos y costos
- Si no hay datos disponibles para la consulta, indica claramente y sugiere qué información proporcionar
"""


# --- RESPUESTAS DRY ---

def success_response(body_dict):
    """Construye una respuesta HTTP 200 con CORS headers."""
    return {
        "statusCode": 200,
        "headers": CORS_HEADERS,
        "body": json.dumps(body_dict, cls=DecimalEncoder),
    }


def error_response(status_code, message):
    """Construye una respuesta HTTP de error con CORS headers."""
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps({"error": message}),
    }


# --- UTILIDADES DE FORMATO ---

def _respuesta_sin_resultados(tipo, filtros):
    """
    Genera un mensaje contextual cuando no se encuentran resultados.
    Describe qué filtros se aplicaron para orientar al usuario.
    """
    filtros_desc = _describir_filtros_aplicados(filtros)
    base = "No encontré tarifas marítimas"

    if filtros_desc:
        base += f" que cumplan los siguientes criterios:\n{filtros_desc}\n"
    else:
        base += " que coincidan con tu consulta.\n"

    if tipo == "generacion_cotizacion":
        base += (
            "\nPara generar una cotización necesito al menos:\n"
            "- Puerto de origen y destino\n"
            "- Naviera (o puedo sugerir opciones disponibles)\n"
            "- Tipo de contenedor (20FT, 40HC, etc.)\n"
        )
    else:
        base += (
            "\nPuedes buscar por:\n"
            "- Puerto de origen (ej. Rotterdam, Hamburgo, Amberes)\n"
            "- Puerto de destino (ej. Puerto Barrios, Puerto Quetzal, Santo Tomás de Castilla)\n"
            "- Naviera (ej. CMA CGM, MAERSK, MSC)\n"
        )

    base += "\n¿Qué información puedes proporcionarme?"
    return base


def _describir_filtros_aplicados(filtros):
    """Lista los filtros activos como viñetas Markdown."""
    if not filtros:
        return ""
    lineas = []
    mapeo = {
        "origin": "Origen",
        "destination": "Destino",
        "shipping_line": "Naviera",
        "container_type": "Tipo de contenedor",
        "num_containers": "Número de contenedores",
        "max_flete": "Flete máximo",
        "min_flete": "Flete mínimo",
        "moneda_filtro": "Moneda",
        "max_transit_days": "Tránsito máximo (días)",
        "max_peso_kg": "Peso máximo (kg)",
        "shipment_term": "Término de embarque",
        "movement_type": "Tipo de movimiento",
        "via_port": "Puerto de transbordo",
        "validity_days": "Vigencia (días)",
    }
    for key, label in mapeo.items():
        val = filtros.get(key)
        if val is not None:
            lineas.append(f"- **{label}:** {val}")
    return "\n".join(lineas)


def _formatear_multiples_tarifas(datos_list, alertas, tipo):
    """
    Genera respuesta Markdown comparativa para múltiples tarifas.
    Ordena por total_amount si tipo es busqueda_cuantitativa.
    """
    count = len(datos_list)
    encabezado = f"Encontré **{count} tarifas marítimas**:"

    bloques = []
    for i, datos in enumerate(datos_list, start=1):
        titulo = f"### Tarifa #{i}"
        bloques.append(titulo + "\n" + _formatear_cotizacion(datos))

    respuesta = encabezado + "\n\n" + "\n\n---\n\n".join(bloques)

    if alertas:
        respuesta += "\n\n---\n\n**Alertas de validación:**\n"
        for alerta in alertas:
            respuesta += f"- {alerta}\n"

    return respuesta


# --- BEDROCK ---

def invoke_nova_pro(system_prompt, user_message, conversation_history=None):
    """
    Función genérica para invocar a Amazon Nova Pro con soporte para historial de conversación.

    Args:
        system_prompt: Instrucciones del sistema
        user_message: Mensaje del usuario actual
        conversation_history: Lista de mensajes previos (opcional, manejado por frontend)
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
    except Exception as exc:
        print(f"Error invocando Bedrock: {exc}")
        raise exc


# --- CONTEXTO DE CONVERSACION ---

def construir_contexto_conversacion(conversation_history):
    """
    Construye un resumen del contexto de la conversación marítima.
    Extrae información clave: puertos (nombres y códigos), navieras, tipos de contenedor.

    Args:
        conversation_history: Lista de mensajes previos del frontend
    """
    if not conversation_history:
        return "PRIMERA PREGUNTA (sin contexto previo)"

    contexto_enriquecido = {
        "puertos_mencionados": [],
        "navieras_mencionadas": [],
        "tipos_contenedor": [],
    }

    for msg in conversation_history[-10:]:
        text = msg["content"][0]["text"]

        # Extraer navieras conocidas
        navieras = re.findall(
            r'\b(CMA CGM|MAERSK|MSC|EVERGREEN|COSCO|HAPAG-LLOYD|ONE|YANG MING|ZIM)\b',
            text, re.IGNORECASE
        )
        if navieras:
            contexto_enriquecido["navieras_mencionadas"].extend(navieras)

        # Extraer códigos de puerto (patrón de 5 letras mayúsculas como NLRTM, GTPBR)
        codigos_puerto = re.findall(r'\b[A-Z]{5}\b', text)
        if codigos_puerto:
            contexto_enriquecido["puertos_mencionados"].extend(codigos_puerto)

        # Extraer nombres de puertos conocidos del texto
        text_lower = text.lower()
        for nombre_puerto, codigo_completo in _PORT_NORMALIZATION.items():
            if nombre_puerto in text_lower:
                contexto_enriquecido["puertos_mencionados"].append(codigo_completo)

        # Extraer tipos de contenedor
        tipos = re.findall(r'\b(20FT|40FT|40HC|45HC|20RF|40RF|20OT|40OT)\b', text, re.IGNORECASE)
        if tipos:
            contexto_enriquecido["tipos_contenedor"].extend([t.upper() for t in tipos])

    contexto = "CONTEXTO DE CONVERSACION MARITIMA:\n\n"

    if contexto_enriquecido["navieras_mencionadas"]:
        navieras_unicas = list(set(contexto_enriquecido["navieras_mencionadas"][-3:]))
        contexto += f"Navieras mencionadas: {', '.join(navieras_unicas)}\n"

    if contexto_enriquecido["puertos_mencionados"]:
        puertos_unicos = list(set(contexto_enriquecido["puertos_mencionados"][-5:]))
        contexto += f"Puertos mencionados: {', '.join(puertos_unicos)}\n"

    if contexto_enriquecido["tipos_contenedor"]:
        tipos_unicos = list(set(contexto_enriquecido["tipos_contenedor"][-3:]))
        contexto += f"Tipos de contenedor mencionados: {', '.join(tipos_unicos)}\n"

    contexto += "\nULTIMOS MENSAJES:\n"
    for msg in conversation_history[-6:]:
        role = "Usuario" if msg["role"] == "user" else "ALCE"
        text = msg["content"][0]["text"]
        contexto += f"{role}: {text[:300]}...\n" if len(text) > 300 else f"{role}: {text}\n"

    return contexto


# --- PASO 0: CLASIFICACION Y EXTRACCION DE FILTROS ---

def paso_0_clasificar_y_extraer_filtros(pregunta_usuario, conversation_history=None):
    """
    Clasifica la intención del usuario en 4 tipos Y extrae filtros estructurados
    en una única llamada al LLM.

    Intent types:
        - conversacional: Preguntas de seguimiento, cálculos sobre datos ya mostrados, saludos.
        - busqueda_simple: Búsqueda por ruta/naviera sin filtros numéricos.
        - busqueda_cuantitativa: Búsqueda CON filtros numéricos (precio, tránsito, peso)
                                 o comparaciones "más económica/rápida".
        - generacion_cotizacion: Usuario provee TODOS los datos para generar un documento
                                 de cotización específico (verbos: genera, cotiza, necesito
                                 una cotización para).

    Returns:
        dict: {
            "tipo": str,
            "requiere_db": bool,
            "razon": str,
            "ordenar_por": "precio_asc" | "precio_desc" | "transito_asc" | null,
            "filtros": { ... }
        }
    """
    contexto_previo = construir_contexto_conversacion(conversation_history)

    system_prompt = f"""
Eres un clasificador inteligente para un chatbot de logística MARITIMA (ALCE).

TU MISION: Clasificar la intención del usuario y extraer filtros estructurados de búsqueda.

TIPOS DE INTENCIÓN:

1. "conversacional" (requiere_db=false):
   - Preguntas de seguimiento sobre información YA mostrada en el historial
   - Cálculos o verificaciones de totales de cotizaciones ya presentadas
   - Saludos, agradecimientos, preguntas generales de logística marítima
   - Ejemplos: "¿Cuál es el total?", "Verifica el cálculo", "Gracias", "¿Qué es un 40HC?"

2. "busqueda_simple" (requiere_db=true):
   - Búsqueda de tarifas por ruta o naviera SIN filtros numéricos de precio, tiempo o peso
   - Ejemplos: "¿Tarifas desde Rotterdam a Puerto Barrios?", "¿Qué navieras operan hacia Guatemala?"

3. "busqueda_cuantitativa" (requiere_db=true):
   - Búsqueda CON al menos uno de: precio máximo/mínimo, tiempo de tránsito máximo,
     peso máximo, número de contenedores
   - O comparaciones: "más económica", "menor precio", "más barata", "más rápida",
     "menor tiempo de tránsito", "más cara"
   - Ejemplos: "¿Cotizaciones 40HC desde Rotterdam con flete menor a EUR 2500?",
     "¿Cuál es la más económica desde Hamburgo?"

4. "generacion_cotizacion" (requiere_db=true):
   - El usuario quiere un DOCUMENTO de cotización específico, no solo buscar tarifas
   - Verbos indicadores: "genera", "cotiza", "necesito una cotización para", "quiero una cotización",
     "puedes generarme", "hazme una cotización"
   - Generalmente provee: origen, destino, naviera, tipo contenedor, términos
   - Ejemplos: "Genera una cotización para un 40HC desde Rotterdam a Puerto Barrios con CMA CGM FOB"

REGLAS PARA ordenar_por:
- "precio_asc" si usuario dice: "más económica", "menor precio", "más barata", "menor costo"
- "precio_desc" si usuario dice: "más cara", "mayor precio"
- "transito_asc" si usuario dice: "más rápida", "menor tiempo de tránsito", "más veloz"
- null en cualquier otro caso

EXTRACCIÓN DE FILTROS:
- origin: nombre o código del puerto de origen (null si no se menciona)
- destination: nombre o código del puerto de destino (null si no se menciona)
- shipping_line: nombre de la naviera exactamente como se menciona (null si no)
- container_type: tipo de contenedor en formato estándar como "40HC", "20FT" (null si no)
- num_containers: número entero de contenedores si se menciona (null si no)
- max_flete: número máximo del flete si se menciona (null si no)
- min_flete: número mínimo del flete si se menciona (null si no)
- moneda_filtro: código de moneda ISO si se menciona junto a max_flete/min_flete (null si no)
- max_transit_days: número máximo de días de tránsito si se menciona (null si no)
- max_peso_kg: peso máximo en kg si se menciona (null si no)
- shipment_term: término de embarque como "FOB", "CIF", "EXW" (null si no)
- movement_type: tipo de movimiento como "Door to Port", "Port to Port", "Door to Door" (null si no)
- via_port: puerto de transbordo si se menciona explícitamente (null si no)
- validity_days: número de días de vigencia si se solicita explícitamente (null si no)

FORMATO DE SALIDA (solo JSON, sin explicaciones):
{{
    "tipo": "busqueda_cuantitativa",
    "requiere_db": true,
    "razon": "Usuario pide filtro por precio máximo EUR 2500 en contenedor 40HC",
    "ordenar_por": null,
    "filtros": {{
        "origin": "Rotterdam",
        "destination": "Puerto Barrios",
        "shipping_line": null,
        "container_type": "40HC",
        "num_containers": null,
        "max_flete": 2500,
        "min_flete": null,
        "moneda_filtro": "EUR",
        "max_transit_days": null,
        "max_peso_kg": null,
        "shipment_term": null,
        "movement_type": null,
        "via_port": null,
        "validity_days": null
    }}
}}

IMPORTANTE: Devuelve SOLO el JSON, sin texto adicional.

{contexto_previo}
"""

    try:
        respuesta_llm = invoke_nova_pro(system_prompt, pregunta_usuario)
        clean_json = respuesta_llm.replace("```json", "").replace("```", "").strip()
        clasificacion = json.loads(clean_json)

        # Asegurar estructura mínima
        if "filtros" not in clasificacion:
            clasificacion["filtros"] = {}
        if "ordenar_por" not in clasificacion:
            clasificacion["ordenar_por"] = None

        print(f"\n{'='*60}")
        print("CLASIFICACION Y FILTROS (maritimo):")
        print(f"{'='*60}")
        print(json.dumps(clasificacion, indent=2, ensure_ascii=False))
        print(f"{'='*60}\n")

        return clasificacion

    except Exception as exc:
        print(f"Error en clasificacion maritima: {exc}")
        return {
            "tipo": "busqueda_simple",
            "requiere_db": True,
            "razon": "Error en clasificacion, ejecutando flujo completo por seguridad",
            "ordenar_por": None,
            "filtros": {},
        }


# --- CONVERSACIONAL ---

def manejar_pregunta_conversacional(pregunta_usuario, conversation_history=None):
    """
    Responde preguntas usando SOLO el contexto de conversación previo.
    No consulta la base de datos.
    """
    system_prompt = _ALCE_SYSTEM_PROMPT + """

    MODO CONVERSACIONAL ACTIVO:
    Responde basándote EXCLUSIVAMENTE en el contexto de conversación previo.
    NO tienes acceso a nueva información de la base de datos en este momento.

    REGLAS ADICIONALES:
    1. Si el usuario pide verificar un total, aplica la fórmula Total = Σ(Qi × Pi) + F_fijos
    2. Si hay discrepancia entre el total calculado y el declarado, genera una ALERTA
    3. Si el usuario pide convertir monedas, indica el tipo de cambio aproximado o pide que lo especifique
    4. Si la información no está en el contexto, indica que necesitas más detalles
    """

    user_content = f"""
PREGUNTA ACTUAL: "{pregunta_usuario}"

Responde usando SOLO la información del contexto de conversación previo.
Si necesitas información nueva de la base de datos, indica al usuario que especifique
número de cotización, puerto de origen/destino, o naviera.
"""

    respuesta = invoke_nova_pro(system_prompt, user_content, conversation_history)

    print(f"\n{'='*60}")
    print("RESPUESTA CONVERSACIONAL MARITIMA (sin consulta DB)")
    print(f"{'='*60}\n")

    return respuesta


# --- PASO 1: GENERAR QUERY DYNAMODB ---

def paso_1_generar_query(pregunta_usuario, filtros=None, conversation_history=None):
    """
    Usa Nova Pro para decidir qué índice GSI usar y generar los parámetros de consulta.
    Recibe filtros extraídos por paso_0 para mejorar la estrategia de búsqueda.

    Args:
        pregunta_usuario: Texto de la pregunta del usuario
        filtros: dict de filtros extraídos por paso_0_clasificar_y_extraer_filtros
        conversation_history: Historial de conversación

    Returns:
        dict con fields: index, origin_port, destination_port, shipping_line, busqueda_amplia
    """
    filtros = filtros or {}
    contexto_previo = construir_contexto_conversacion(conversation_history)

    # Construir pista de filtros ya extraídos para ayudar al LLM
    filtros_hint = ""
    if filtros:
        filtros_serializables = {k: v for k, v in filtros.items() if v is not None}
        if filtros_serializables:
            filtros_hint = (
                f"\nFILTROS YA EXTRAÍDOS (usa estos para elegir el índice):\n"
                f"{json.dumps(filtros_serializables, ensure_ascii=False, indent=2)}\n"
            )

    system_prompt = f"""
Eres un experto en DynamoDB y análisis de contexto conversacional para logística MARITIMA.

TU MISION: Analizar la pregunta y el contexto para generar la mejor estrategia de consulta
en la tabla MaritimeQuotations.

{_MARITIME_SCHEMA_INFO}

NORMALIZACION DE PUERTOS (usa el formato completo cuando reconozcas el nombre):
- Rotterdam → "NLRTM - ROTTERDAM, NETHERLANDS"
- Hamburgo / Hamburg → "DEHAM - HAMBURG, GERMANY"
- Amberes / Antwerp / Antwerpen → "BEANR - ANTWERP, BELGIUM"
- Puerto Barrios → "GTPBR - PUERTO BARRIOS, GUATEMALA"
- Puerto Quetzal → "GTQUE - PUERTO QUETZAL, GUATEMALA"
- Santo Tomás de Castilla / Santo Tomas → "GTSTC - SANTO TOMAS DE CASTILLA, GUATEMALA"
- Kingston → "JMKIN - KINGSTON, JAMAICA"

REGLAS DE SELECCION DE INDICE:
1. Si menciona origen Y destino → "OriginPortIndex" (y filtra destino en Python)
2. Si SOLO menciona puerto de origen → "OriginPortIndex"
3. Si SOLO menciona puerto de destino → "DestinationPortIndex"
4. Si SOLO menciona naviera → "ShippingLineIndex"
5. Si NO hay criterio específico → busqueda_amplia: true (scan completo)

REGLAS ADICIONALES:
- Si el usuario pide "todas las tarifas disponibles" → busqueda_amplia: true
- Si menciona una naviera sin puerto → "ShippingLineIndex"
- Si el contexto tiene información de puertos/navieras previas, usar esa información
- Prioriza el GSI más selectivo según los filtros disponibles

FORMATO DE SALIDA (solo JSON, sin explicaciones):
{{
    "index": "OriginPortIndex",
    "origin_port": "NLRTM - ROTTERDAM, NETHERLANDS",
    "destination_port": null,
    "shipping_line": null,
    "busqueda_amplia": false
}}

{filtros_hint}
{contexto_previo}

Devuelve SOLO el JSON, sin texto adicional.
"""

    respuesta_llm = invoke_nova_pro(system_prompt, pregunta_usuario)

    print(f"\n{'='*60}")
    print("RESPUESTA CRUDA DEL LLM (paso_1 maritimo):")
    print(f"{'='*60}")
    print(respuesta_llm)
    print(f"{'='*60}\n")

    clean_json = respuesta_llm.replace("```json", "").replace("```", "").strip()
    parsed = json.loads(clean_json)

    print(f"\n{'='*60}")
    print("PARAMETROS PARSEADOS (maritimo):")
    print(f"{'='*60}")
    print(json.dumps(parsed, indent=2))
    print(f"{'='*60}\n")

    return parsed


# --- PASO 2: EJECUTAR DYNAMO (sin cambios) ---

def paso_2_ejecutar_dynamo(params):
    """
    Ejecuta la query en MaritimeQuotations usando los parámetros generados.
    Nunca devuelve vacío — hace scan completo como último recurso.
    """
    index_name = params.get("index")
    origin_port = params.get("origin_port")
    destination_port = params.get("destination_port")
    shipping_line = params.get("shipping_line")
    busqueda_amplia = params.get("busqueda_amplia", False)

    print(f"\n{'='*60}")
    print(f"EJECUTANDO QUERY MARITIMA EN INDICE: {index_name}")
    print(f"{'='*60}")
    print(f"Origin: {origin_port}, Destination: {destination_port}")
    print(f"Naviera: {shipping_line}")
    print(f"Busqueda amplia: {busqueda_amplia}")
    print(f"{'='*60}\n")

    try:
        items = []

        # ESTRATEGIA 1: Query con índice específico
        if not busqueda_amplia:
            query_params = None

            if index_name == "OriginPortIndex" and origin_port:
                query_params = {
                    "IndexName": index_name,
                    "KeyConditionExpression": Key("origin_port").eq(origin_port),
                }
            elif index_name == "DestinationPortIndex" and destination_port:
                query_params = {
                    "IndexName": index_name,
                    "KeyConditionExpression": Key("destination_port").eq(destination_port),
                }
            elif index_name == "ShippingLineIndex" and shipping_line:
                query_params = {
                    "IndexName": index_name,
                    "KeyConditionExpression": Key("shipping_line").eq(shipping_line),
                }

            if query_params:
                response = table.query(**query_params)
                items = response.get("Items", [])
                print(f"Items recuperados por query directa: {len(items)}")

        # ESTRATEGIA 2: Búsqueda parcial por destino si no hay resultados exactos
        if len(items) == 0 and destination_port and not busqueda_amplia:
            print("Sin coincidencias exactas en destino, intentando busqueda parcial...")
            scan_response = table.scan()
            all_items = scan_response.get("Items", [])
            dest_lower = destination_port.lower()
            items = [
                item for item in all_items
                if dest_lower in item.get("destination_port", "").lower()
            ]
            print(f"Encontrados {len(items)} items con busqueda parcial de destino")

        # ESTRATEGIA 3: Scan completo como último recurso
        if len(items) == 0:
            print("Haciendo SCAN COMPLETO de MaritimeQuotations...")
            response = table.scan()
            items = response.get("Items", [])
            print(f"Scan completo recupero {len(items)} registros totales")

        # FILTRADO POST-QUERY en Python
        if destination_port and len(items) > 0:
            dest_lower = destination_port.lower()
            filtered = [
                item for item in items
                if dest_lower in item.get("destination_port", "").lower()
                or item.get("destination_port", "").lower() in dest_lower
            ]
            if filtered:
                items = filtered
                print(f"Filtrado por destination_port '{destination_port}': {len(items)} items")

        if shipping_line and len(items) > 0:
            line_lower = shipping_line.lower()
            filtered = [
                item for item in items
                if line_lower in item.get("shipping_line", "").lower()
            ]
            if filtered:
                items = filtered
                print(f"Filtrado por shipping_line '{shipping_line}': {len(items)} items")

        print(f"\n{'='*60}")
        print(f"RESULTADO FINAL MARITIMO: {len(items)} cotizaciones encontradas")
        print(f"{'='*60}\n")

        return items

    except Exception as exc:
        print(f"Error ejecutando DynamoDB maritimo: {exc}")
        import traceback
        traceback.print_exc()
        try:
            print("Intentando scan de emergencia...")
            response = table.scan()
            return response.get("Items", [])
        except Exception:
            return []


# --- EXTRACCION Y VALIDACION ---

def extraer_datos_relevantes_maritimos(items):
    """
    Extrae y simplifica los datos de las cotizaciones marítimas para enviar al LLM.
    Convierte Decimals a float para serialización JSON.
    """
    datos_simplificados = []

    for item in items:
        line_items_converted = []
        for li in item.get("line_items", []):
            line_items_converted.append({
                "description": li.get("description", ""),
                "quantity": float(li.get("quantity", 0)),
                "unit": li.get("unit", ""),
                "currency": li.get("currency", ""),
                "unit_price": float(li.get("unit_price", 0)),
                "amount": float(li.get("amount", 0)),
            })

        commodities_converted = []
        for c in item.get("commodities", []):
            comm = {
                "description": c.get("description", ""),
                "container_type": c.get("container_type", ""),
                "hs_code": c.get("hs_code", ""),
                "country_of_origin": c.get("country_of_origin", ""),
            }
            if c.get("gross_weight") is not None:
                comm["gross_weight"] = float(c["gross_weight"])
            if c.get("volume_cbm") is not None:
                comm["volume_cbm"] = float(c["volume_cbm"])
            commodities_converted.append(comm)

        logistics = item.get("logistics", {})
        logistics_converted = {
            "shipping_line": logistics.get("shipping_line", ""),
        }
        if logistics.get("transit_time_days") is not None:
            logistics_converted["transit_time_days"] = float(logistics["transit_time_days"])

        datos_simplificados.append({
            "id": item.get("id"),
            "dates": item.get("dates", {}),
            "routing": item.get("routing", {}),
            "logistics": logistics_converted,
            "shipment_type": item.get("shipment_type", ""),
            "movement_type": item.get("movement_type", ""),
            "shipment_term": item.get("shipment_term", ""),
            "prepared_by": item.get("prepared_by", ""),
            "requested_by": item.get("requested_by", ""),
            "company": item.get("company", {}),
            "commodities": commodities_converted,
            "line_items": line_items_converted,
            "total_amount": float(item["total_amount"]) if item.get("total_amount") is not None else None,
            "currency": item.get("currency", ""),
            "terms_and_conditions": item.get("terms_and_conditions", {}),
        })

    return datos_simplificados


def calcular_total_cotizacion(line_items: list) -> float:
    """
    Calcula el total de una cotización usando la fórmula ALCE V2:
    Total = Σ(Qi × Pi) + F_fijos

    Los ítems con unit == "PER SHIPMENT" o "PER BL" son F_fijos.
    Los demás son variables (Qi × Pi).
    """
    total = 0.0
    for item in line_items:
        quantity = float(item.get("quantity", 0))
        unit_price = float(item.get("unit_price", 0))
        total += quantity * unit_price
    return round(total, 2)


def validar_cotizacion(datos_cotizacion: dict) -> list:
    """
    Ejecuta todas las validaciones de negocio ALCE V2 sobre una cotización.
    Devuelve lista de alertas (strings). Lista vacía = sin problemas.
    """
    alertas = []

    # Validar fechas
    dates = datos_cotizacion.get("dates", {})
    try:
        valid_from_str = dates.get("valid_from")
        valid_till_str = dates.get("valid_till")
        quote_date_str = dates.get("quote_date")

        if valid_from_str and valid_till_str:
            valid_from = _date.fromisoformat(valid_from_str)
            valid_till = _date.fromisoformat(valid_till_str)
            if valid_till <= valid_from:
                alertas.append(
                    f"ALERTA FECHA: valid_till ({valid_till_str}) es anterior o igual a "
                    f"valid_from ({valid_from_str}) → INCONSISTENCIA DETECTADA"
                )

        if quote_date_str and valid_till_str:
            quote_date = _date.fromisoformat(quote_date_str)
            valid_till = _date.fromisoformat(valid_till_str)
            if valid_till <= quote_date:
                alertas.append(
                    f"ALERTA FECHA: valid_till ({valid_till_str}) es anterior o igual a "
                    f"quote_date ({quote_date_str}) → INCONSISTENCIA DETECTADA"
                )
    except (ValueError, TypeError):
        alertas.append("ALERTA FECHA: Formato de fecha inválido. Use ISO 8601 (YYYY-MM-DD)")

    # Validar line_items
    line_items = datos_cotizacion.get("line_items", [])
    for idx, item in enumerate(line_items):
        quantity = float(item.get("quantity", 0))
        unit_price = float(item.get("unit_price", 0))
        declared_amount = float(item.get("amount", 0))
        expected_amount = round(quantity * unit_price, 2)

        if quantity <= 0:
            alertas.append(
                f"ALERTA CANTIDAD: Line item #{idx + 1} '{item.get('description', '')}': "
                f"quantity = {quantity} debe ser > 0"
            )
        if unit_price < 0:
            alertas.append(
                f"ALERTA PRECIO: Line item #{idx + 1} '{item.get('description', '')}': "
                f"unit_price = {unit_price} no puede ser negativo"
            )
        if abs(expected_amount - declared_amount) > 0.01:
            alertas.append(
                f"ALERTA MONTO: Line item #{idx + 1} '{item.get('description', '')}': "
                f"{quantity} × {unit_price} = {expected_amount} pero amount declarado = {declared_amount} "
                f"→ DISCREPANCIA"
            )

    # Validar total
    if line_items:
        calculated_total = calcular_total_cotizacion(line_items)
        declared_total = datos_cotizacion.get("total_amount")
        if declared_total is not None:
            declared_total_float = float(declared_total)
            if abs(calculated_total - declared_total_float) > 0.01:
                alertas.append(
                    f"ALERTA TOTAL: Suma de line_items calculada = {calculated_total} "
                    f"pero total_amount declarado = {declared_total_float} → DISCREPANCIA"
                )

    # Validar transit_time
    logistics = datos_cotizacion.get("logistics", {})
    transit_time = logistics.get("transit_time_days")
    if transit_time is not None:
        transit_float = float(transit_time)
        if transit_float < 1:
            alertas.append(
                f"ALERTA TRANSITO: transit_time_days = {transit_float} es demasiado corto (< 1 día)"
            )
        elif transit_float > 60:
            alertas.append(
                f"ALERTA TRANSITO: transit_time_days = {transit_float} es muy largo (> 60 días). "
                f"Verificar si hay transbordo."
            )

    # Validar transbordo
    routing = datos_cotizacion.get("routing", {})
    if routing.get("via_port"):
        alertas.append(
            f"INFO TRANSBORDO: Ruta con transbordo vía {routing['via_port']}. "
            f"Verificar tiempos de tránsito parciales (origen→via y via→destino)."
        )

    return alertas


# --- FILTROS CUANTITATIVOS ---

def aplicar_filtros_cuantitativos(items, filtros):
    """
    Aplica filtros numéricos en Python después de obtener items de DynamoDB.

    Filtros soportados:
    - container_type: Coincidencia contra commodities[].container_type
    - max_flete / min_flete: Compara contra total_amount respetando moneda
    - max_transit_days: Compara contra logistics.transit_time_days
    - max_peso_kg: Compara contra commodities[].gross_weight

    Principio de seguridad: si un filtro produciría cero resultados, se omite
    para no dejar al usuario sin respuesta.

    Args:
        items: Lista de items (dicts) ya extraídos con extraer_datos_relevantes_maritimos
        filtros: dict de filtros extraídos por paso_0

    Returns:
        list: Subconjunto filtrado (nunca vacío si items no estaba vacío)
    """
    if not filtros or not items:
        return items

    resultado = list(items)

    # Filtro: container_type
    container_type = filtros.get("container_type")
    if container_type:
        norm = re.sub(r'[\s\-]', '', container_type).upper()
        candidatos = [
            item for item in resultado
            if any(
                re.sub(r'[\s\-]', '', c.get("container_type", "")).upper() == norm
                for c in item.get("commodities", [])
            )
        ]
        if candidatos:
            resultado = candidatos
            print(f"Filtro container_type '{container_type}': {len(resultado)} items")
        else:
            print(f"Filtro container_type '{container_type}' no produjo resultados, omitiendo")

    # Filtro: max_flete
    max_flete = filtros.get("max_flete")
    moneda_filtro = (filtros.get("moneda_filtro") or "").upper()
    if max_flete is not None:
        candidatos = [
            item for item in resultado
            if item.get("total_amount") is not None
            and float(item["total_amount"]) <= float(max_flete)
            and (
                not moneda_filtro
                or item.get("currency", "").upper() == moneda_filtro
            )
        ]
        if candidatos:
            resultado = candidatos
            print(f"Filtro max_flete {max_flete} {moneda_filtro}: {len(resultado)} items")
        else:
            print(f"Filtro max_flete {max_flete} no produjo resultados, omitiendo")

    # Filtro: min_flete
    min_flete = filtros.get("min_flete")
    if min_flete is not None:
        candidatos = [
            item for item in resultado
            if item.get("total_amount") is not None
            and float(item["total_amount"]) >= float(min_flete)
            and (
                not moneda_filtro
                or item.get("currency", "").upper() == moneda_filtro
            )
        ]
        if candidatos:
            resultado = candidatos
            print(f"Filtro min_flete {min_flete} {moneda_filtro}: {len(resultado)} items")
        else:
            print(f"Filtro min_flete {min_flete} no produjo resultados, omitiendo")

    # Filtro: max_transit_days
    max_transit_days = filtros.get("max_transit_days")
    if max_transit_days is not None:
        candidatos = [
            item for item in resultado
            if item.get("logistics", {}).get("transit_time_days") is not None
            and float(item["logistics"]["transit_time_days"]) <= float(max_transit_days)
        ]
        if candidatos:
            resultado = candidatos
            print(f"Filtro max_transit_days {max_transit_days}: {len(resultado)} items")
        else:
            print(f"Filtro max_transit_days {max_transit_days} no produjo resultados, omitiendo")

    # Filtro: max_peso_kg
    max_peso_kg = filtros.get("max_peso_kg")
    if max_peso_kg is not None:
        candidatos = [
            item for item in resultado
            if any(
                c.get("gross_weight") is not None
                and float(c["gross_weight"]) <= float(max_peso_kg)
                for c in item.get("commodities", [])
            )
        ]
        if candidatos:
            resultado = candidatos
            print(f"Filtro max_peso_kg {max_peso_kg}: {len(resultado)} items")
        else:
            print(f"Filtro max_peso_kg {max_peso_kg} no produjo resultados, omitiendo")

    return resultado


# --- MEJOR COINCIDENCIA PARA GENERACION DE COTIZACION ---

def encontrar_mejor_coincidencia(items, filtros):
    """
    Puntúa cada item contra los filtros para seleccionar el más adecuado
    en el flujo de generacion_cotizacion.

    Scoring:
    - container_type match: +4
    - shipping_line match: +3
    - shipment_term match: +2
    - movement_type match: +1

    Args:
        items: Lista de dicts ya procesados con extraer_datos_relevantes_maritimos
        filtros: dict de filtros de paso_0

    Returns:
        tuple: (best_item, notes_list) donde notes describe diferencias importantes
    """
    if not items:
        return None, []

    if len(items) == 1:
        return items[0], []

    filtros = filtros or {}
    container_type_req = re.sub(r'[\s\-]', '', (filtros.get("container_type") or "")).upper()
    shipping_line_req = (filtros.get("shipping_line") or "").lower().strip()
    shipment_term_req = (filtros.get("shipment_term") or "").upper().strip()
    movement_type_req = (filtros.get("movement_type") or "").lower().strip()

    def score_item(item):
        pts = 0
        # container_type
        if container_type_req:
            for c in item.get("commodities", []):
                if re.sub(r'[\s\-]', '', c.get("container_type", "")).upper() == container_type_req:
                    pts += 4
                    break
        # shipping_line
        if shipping_line_req:
            item_sl = item.get("logistics", {}).get("shipping_line", "").lower()
            if shipping_line_req in item_sl or item_sl in shipping_line_req:
                pts += 3
        # shipment_term
        if shipment_term_req:
            item_st = (item.get("shipment_term") or "").upper().strip()
            if shipment_term_req == item_st:
                pts += 2
        # movement_type
        if movement_type_req:
            item_mt = (item.get("movement_type") or "").lower().strip()
            if movement_type_req in item_mt or item_mt in movement_type_req:
                pts += 1
        return pts

    scored = sorted(items, key=score_item, reverse=True)
    best = scored[0]

    # Generar notas sobre diferencias respecto a lo solicitado
    notes = []
    best_sl = best.get("logistics", {}).get("shipping_line", "")
    if shipping_line_req and shipping_line_req not in best_sl.lower():
        notes.append(
            f"Nota: la naviera disponible es **{best_sl}** "
            f"(se solicitó '{filtros.get('shipping_line')}')."
        )

    best_st = (best.get("shipment_term") or "").upper()
    if shipment_term_req and shipment_term_req != best_st:
        notes.append(
            f"Nota: el término de embarque disponible es **{best_st or 'no especificado'}** "
            f"(se solicitó '{shipment_term_req}')."
        )

    best_mt = (best.get("movement_type") or "")
    if movement_type_req and movement_type_req not in best_mt.lower():
        notes.append(
            f"Nota: el tipo de movimiento disponible es **{best_mt or 'no especificado'}** "
            f"(se solicitó '{filtros.get('movement_type')}')."
        )

    if container_type_req:
        tipos_disponibles = [
            c.get("container_type", "") for c in best.get("commodities", [])
        ]
        if not any(
            re.sub(r'[\s\-]', '', t).upper() == container_type_req
            for t in tipos_disponibles
        ):
            notes.append(
                f"Nota: el tipo de contenedor disponible es "
                f"**{', '.join(tipos_disponibles) or 'no especificado'}** "
                f"(se solicitó '{filtros.get('container_type')}')."
            )

    return best, notes


# --- ENRIQUECIMIENTO DE DATOS ---

def _enriquecer_datos_con_requisitos(datos, filtros):
    """
    Combina los datos del mejor item de DB con los requisitos del usuario.
    Modifica una copia profunda del item original para no mutar el original.

    Transformaciones:
    - Sobreescribe movement_type si se especificó en filtros
    - Sobreescribe shipment_term si se especificó en filtros
    - Agrega via_port al routing si se especificó y no está ya
    - Si validity_days: recalcula valid_from (hoy) y valid_till (hoy + validity_days)
    - Si num_containers > 1: escala line_items con unidad PER CONTAINER/CTR/CNT y
      recalcula total_amount

    Args:
        datos: dict de cotización (resultado de extraer_datos_relevantes_maritimos)
        filtros: dict de filtros de paso_0

    Returns:
        dict: Copia enriquecida del item
    """
    if not filtros:
        return datos

    enriched = copy.deepcopy(datos)
    filtros = filtros or {}

    # movement_type
    movement_type = filtros.get("movement_type")
    if movement_type:
        enriched["movement_type"] = movement_type

    # shipment_term
    shipment_term = filtros.get("shipment_term")
    if shipment_term:
        enriched["shipment_term"] = shipment_term

    # via_port
    via_port = filtros.get("via_port")
    if via_port:
        routing = enriched.get("routing", {})
        if not routing.get("via_port"):
            routing["via_port"] = via_port
            enriched["routing"] = routing

    # validity_days
    validity_days = filtros.get("validity_days")
    if validity_days is not None:
        try:
            validity_int = int(validity_days)
            today = _date.today()
            valid_till = today + timedelta(days=validity_int)
            dates = enriched.get("dates", {})
            dates["valid_from"] = today.isoformat()
            dates["valid_till"] = valid_till.isoformat()
            enriched["dates"] = dates
        except (ValueError, TypeError):
            pass

    # num_containers: escalar line_items por unidad tipo "PER CONTAINER", "CTR", "CNT"
    num_containers = filtros.get("num_containers")
    if num_containers is not None:
        try:
            n = int(num_containers)
            if n > 1:
                _unidad_patron = re.compile(
                    r'\b(PER CONTAINER|PER CTR|PER CNT|CTR|CNT)\b', re.IGNORECASE
                )
                new_line_items = []
                for li in enriched.get("line_items", []):
                    li_copy = dict(li)
                    if _unidad_patron.search(li_copy.get("unit", "")):
                        li_copy["quantity"] = float(li_copy.get("quantity", 1)) * n
                        li_copy["amount"] = li_copy["quantity"] * float(li_copy.get("unit_price", 0))
                    new_line_items.append(li_copy)
                enriched["line_items"] = new_line_items
                # Recalcular total
                enriched["total_amount"] = calcular_total_cotizacion(new_line_items)
        except (ValueError, TypeError):
            pass

    return enriched


# --- FORMATEADORES ---

def _formatear_cotizacion(datos: dict) -> str:
    """
    Formatea una cotización mostrando solo los campos requeridos para el chat.
    Los datos completos siguen disponibles en memoria para validaciones.
    """
    routing = datos.get("routing", {})
    logistics = datos.get("logistics", {})

    proveedor = datos.get("prepared_by") or datos.get("company", {}).get("name") or "N/D"
    origen = routing.get("origin_port") or datos.get("origin_port") or "N/D"
    destino = routing.get("destination_port") or datos.get("destination_port") or "N/D"
    naviera = logistics.get("shipping_line") or datos.get("shipping_line") or "N/D"

    total = datos.get("total_amount")
    currency = datos.get("currency", "")
    precio = f"{total:,.2f} {currency}" if total is not None else "N/D"

    transit = logistics.get("transit_time_days")
    transito = f"{int(transit)} días" if transit is not None else "N/D"

    via = routing.get("via_port")
    transbordo_nota = f" _(vía {via})_" if via else ""

    lineas = [
        f"**Proveedor:** {proveedor}",
        f"**Puerto de origen:** {origen}",
        f"**Puerto de destino:** {destino}{transbordo_nota}",
        f"**Precio flete marítimo:** {precio}",
        f"**Tiempo en tránsito:** {transito}",
        f"**Naviera:** {naviera}",
    ]
    return "\n".join(lineas)


def _escape_xml(value: str) -> str:
    """Escapa caracteres especiales para XML."""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def generar_xml_maritimo(datos: dict, peso_usuario=None) -> str:
    """
    Genera XML en formato compatible con el frontend para una cotización marítima.
    Usa la misma estructura que el chatbot terrestre para que el frontend pueda
    renderizar la misma tarjeta xml-quotation.
    """
    routing = datos.get("routing", {})
    logistics = datos.get("logistics", {})
    commodities = datos.get("commodities", [])
    line_items = datos.get("line_items", [])

    proveedor = logistics.get("shipping_line") or datos.get("prepared_by") or "N/D"
    origen = routing.get("origin_port") or datos.get("origin_port") or "N/D"
    destino = routing.get("destination_port") or datos.get("destination_port") or "N/D"
    moneda = datos.get("currency", "USD")
    total_amount = float(datos.get("total_amount") or 0)

    tipo_unidad = "Contenedor Marítimo"
    peso_solicitado = 0
    if commodities:
        tipo_unidad = commodities[0].get("container_type") or tipo_unidad
        peso_solicitado = float(commodities[0].get("gross_weight") or 0)

    # Override with user-requested weight if provided
    if peso_usuario is not None:
        peso_solicitado = float(peso_usuario)

    tarifa_base_monto = 0.0
    tarifa_base_rango = "Flete Marítimo"
    costos_adicionales_items = []

    for i, item in enumerate(line_items):
        cantidad = float(item.get("quantity") or 1)
        precio_unitario = float(item.get("unit_price") or 0)
        monto_item = float(item.get("amount") or (cantidad * precio_unitario))
        descripcion_item = item.get("description", "")
        moneda_item = item.get("currency") or moneda
        unidad_item = item.get("unit", "")
        desc_detalle = f"{cantidad} {unidad_item}".strip() if unidad_item else ""

        if i == 0:
            tarifa_base_monto = monto_item
            tarifa_base_rango = descripcion_item or "Flete Marítimo"
        else:
            costos_adicionales_items.append({
                "concepto": descripcion_item,
                "valor": monto_item,
                "unidad": moneda_item,
                "descripcion": desc_detalle,
            })

    transit = logistics.get("transit_time_days")
    detalles_parts = []
    if transit is not None:
        detalles_parts.append(f"Tiempo de tránsito: {int(float(transit))} días")
    via_port = routing.get("via_port", "")
    if via_port:
        detalles_parts.append(f"Transbordo vía: {via_port}")
    detalles = " | ".join(detalles_parts)

    dates = datos.get("dates", {})
    valid_till = dates.get("valid_till", "")
    nota_base = f"Válida hasta {valid_till}" if valid_till else ""
    notas_adicionales = datos.get("_notas_adicionales", [])
    nota = " | ".join(filter(None, [nota_base] + notas_adicionales))

    costos_xml = ""
    for costo in costos_adicionales_items:
        costos_xml += f"""
        <costo>
          <concepto>{_escape_xml(costo['concepto'])}</concepto>
          <valor>{costo['valor']:.2f}</valor>
          <unidad>{_escape_xml(costo['unidad'])}</unidad>
          <descripcion>{_escape_xml(costo['descripcion'])}</descripcion>
        </costo>"""

    xml = f"""<respuesta>
  <cotizacion>
    <proveedor>{_escape_xml(proveedor)}</proveedor>
    <ruta>
      <origen>{_escape_xml(origen)}</origen>
      <destino>{_escape_xml(destino)}</destino>
    </ruta>
    <unidad>
      <tipo>{_escape_xml(tipo_unidad)}</tipo>
      <peso_solicitado>{peso_solicitado:.0f}</peso_solicitado>
      <peso_unidad>kg</peso_unidad>
    </unidad>
    <tarifa_base>
      <monto>{tarifa_base_monto:.2f}</monto>
      <moneda>{_escape_xml(moneda)}</moneda>
      <rango>{_escape_xml(tarifa_base_rango)}</rango>
    </tarifa_base>
    <sobrepeso>
      <aplica>false</aplica>
      <monto>0</monto>
      <moneda>{_escape_xml(moneda)}</moneda>
      <descripcion></descripcion>
    </sobrepeso>
    <costos_adicionales>{costos_xml}
    </costos_adicionales>
    <resumen_costos>
      <total>{total_amount:.2f}</total>
      <moneda>{_escape_xml(moneda)}</moneda>
      <detalles>{_escape_xml(detalles)}</detalles>
      <condiciones_aduana></condiciones_aduana>
      <condiciones_cominter></condiciones_cominter>
      <nota>{_escape_xml(nota)}</nota>
    </resumen_costos>
    <tarifa_id>{_escape_xml(datos.get('id', ''))}</tarifa_id>
    <tipo>maritimo</tipo>
  </cotizacion>
</respuesta>"""

    return xml


# --- PASO 3: GENERAR RESPUESTA ---

def paso_3_generar_respuesta_maritima(pregunta, items, clasificacion, conversation_history=None):
    """
    Genera la respuesta final basada en los datos de cotizaciones marítimas
    y el tipo de intención clasificado.

    Lógica por tipo:
    - generacion_cotizacion: Filtra, selecciona mejor coincidencia, enriquece y devuelve XML.
    - busqueda_cuantitativa: Filtra, ordena y devuelve XML (1) o Markdown (varios).
    - busqueda_simple: Sin filtrado numérico, XML (1) o Markdown (varios).

    Args:
        pregunta: Texto de la pregunta del usuario
        items: Lista de items crudos de DynamoDB
        clasificacion: dict resultado de paso_0_clasificar_y_extraer_filtros
        conversation_history: Historial de conversación (opcional)

    Returns:
        str: XML (1 resultado) o Markdown (múltiples resultados) o mensaje de error
    """
    tipo = clasificacion.get("tipo", "busqueda_simple")
    filtros = clasificacion.get("filtros") or {}
    ordenar_por = clasificacion.get("ordenar_por")
    peso_usuario = filtros.get("max_peso_kg")

    if not items:
        return _respuesta_sin_resultados(tipo, filtros)

    # Extraer y convertir datos
    datos_optimizados = extraer_datos_relevantes_maritimos(items)

    # Validaciones de negocio sobre todos los items
    todas_las_alertas = []
    for datos in datos_optimizados:
        alertas = validar_cotizacion(datos)
        if alertas:
            item_id = datos.get("id", "N/A")
            for alerta in alertas:
                todas_las_alertas.append(f"[{item_id}] {alerta}")

    print(f"\n{'='*60}")
    print(f"VALIDACIONES MARITIMAS: {len(todas_las_alertas)} alertas detectadas")
    for alerta in todas_las_alertas:
        print(f"  - {alerta}")
    print(f"{'='*60}\n")

    # ---- FLUJO: generacion_cotizacion ----
    if tipo == "generacion_cotizacion":
        print("FLUJO: generacion_cotizacion")

        # Aplicar filtros cuantitativos primero
        candidatos = aplicar_filtros_cuantitativos(datos_optimizados, filtros)

        if not candidatos:
            return _respuesta_sin_resultados(tipo, filtros)

        # Seleccionar mejor coincidencia
        best_item, notas = encontrar_mejor_coincidencia(candidatos, filtros)

        if best_item is None:
            return _respuesta_sin_resultados(tipo, filtros)

        # Enriquecer con requisitos del usuario
        enriched = _enriquecer_datos_con_requisitos(best_item, filtros)

        # Embed mismatch notes inside the XML <nota> field (no Markdown after XML)
        if notas:
            enriched["_notas_adicionales"] = notas

        # Generar XML limpio para que el frontend pueda parsearlo
        respuesta = generar_xml_maritimo(enriched, peso_usuario)

        print(f"{'='*60}")
        print("XML MARITIMO generado para generacion_cotizacion")
        print(f"{'='*60}\n")
        return respuesta

    # ---- FLUJO: busqueda_cuantitativa ----
    if tipo == "busqueda_cuantitativa":
        print("FLUJO: busqueda_cuantitativa")

        candidatos = aplicar_filtros_cuantitativos(datos_optimizados, filtros)

        if not candidatos:
            filtros_desc = _describir_filtros_aplicados(filtros)
            return (
                "No encontré tarifas marítimas que cumplan todos los criterios especificados.\n\n"
                f"Criterios aplicados:\n{filtros_desc}\n\n"
                "Considera flexibilizar los filtros o consultar sin restricciones numéricas."
            )

        # Ordenar si se especificó
        if ordenar_por == "precio_asc":
            candidatos = sorted(
                candidatos,
                key=lambda x: float(x.get("total_amount") or 0)
            )
        elif ordenar_por == "precio_desc":
            candidatos = sorted(
                candidatos,
                key=lambda x: float(x.get("total_amount") or 0),
                reverse=True
            )
        elif ordenar_por == "transito_asc":
            candidatos = sorted(
                candidatos,
                key=lambda x: float(x.get("logistics", {}).get("transit_time_days") or 9999)
            )

        if len(candidatos) == 1:
            print("XML MARITIMO: resultado único en busqueda_cuantitativa")
            return generar_xml_maritimo(candidatos[0], peso_usuario)

        respuesta = _formatear_multiples_tarifas(candidatos, todas_las_alertas, tipo)
        print(f"Markdown comparativo: {len(candidatos)} tarifas en busqueda_cuantitativa")
        return respuesta

    # ---- FLUJO: busqueda_simple (default) ----
    print("FLUJO: busqueda_simple")

    if len(datos_optimizados) == 1:
        print("XML MARITIMO: resultado único en busqueda_simple")
        return generar_xml_maritimo(datos_optimizados[0], peso_usuario)

    respuesta = _formatear_multiples_tarifas(datos_optimizados, todas_las_alertas, tipo)
    print(f"Markdown comparativo: {len(datos_optimizados)} tarifas en busqueda_simple")
    return respuesta


# --- HANDLER PRINCIPAL ---

def handler(event, context):
    """
    Handler del chatbot marítimo ALCE V2.
    Procesamiento inteligente con clasificación de intención y consulta a DynamoDB.

    REQUEST FORMAT:
    {
        "query": "¿Cotizaciones disponibles desde Rotterdam a Puerto Barrios?",
        "conversation_history": [
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
        "tipo": "busqueda_simple" | "busqueda_cuantitativa" | "generacion_cotizacion" | "conversacional",
        "items_found": 1,
        "requiere_db": true | false,
        "razon": "...",
        "alertas": ["..."]
    }
    """
    try:
        body = json.loads(event.get('body', '{}'))
        user_query = body.get('query')
        conversation_history = body.get('conversation_history', [])

        if not user_query:
            return error_response(400, "Falta el campo 'query'")

        print(f"\n{'='*80}")
        print("NUEVA PETICION MARITIMA (ALCE V2)")
        print(f"{'='*80}")
        print(f"Pregunta: {user_query}")
        print(f"Historial: {len(conversation_history)} mensajes")
        print(f"{'='*80}\n")

        # PASO 0: CLASIFICACION Y EXTRACCION DE FILTROS
        clasificacion = paso_0_clasificar_y_extraer_filtros(user_query, conversation_history)
        tipo_pregunta = clasificacion.get("tipo", "busqueda_simple")
        requiere_db = clasificacion.get("requiere_db", True)
        filtros = clasificacion.get("filtros") or {}

        # RUTA 1: PREGUNTA CONVERSACIONAL (sin consulta DB)
        if tipo_pregunta == "conversacional" and not requiere_db:
            print("RUTA CONVERSACIONAL MARITIMA ACTIVADA (sin consulta DB)")
            respuesta_final = manejar_pregunta_conversacional(user_query, conversation_history)

            return success_response({
                "respuesta": respuesta_final,
                "tipo": tipo_pregunta,
                "items_found": 0,
                "requiere_db": False,
                "razon": clasificacion.get("razon", ""),
                "alertas": [],
            })

        # RUTA 2: BUSQUEDA O GENERACION (consulta DB completa)
        print(f"RUTA {tipo_pregunta.upper()} MARITIMA ACTIVADA (consulta DynamoDB)")

        # 1. Generar estrategia de query con filtros extraídos
        db_params = paso_1_generar_query(user_query, filtros, conversation_history)
        print(f"Estrategia DB maritima: {db_params}")

        # 2. Recuperar datos de DynamoDB
        items = paso_2_ejecutar_dynamo(db_params)
        print(f"Cotizaciones encontradas: {len(items)}")

        # 3. Generar respuesta con flujo según tipo de intención
        respuesta_final = paso_3_generar_respuesta_maritima(
            user_query,
            items,
            clasificacion,
            conversation_history,
        )

        # 4. Calcular alertas + extraer datos_completos
        alertas_respuesta = []
        datos_completos = None
        todos_datos = extraer_datos_relevantes_maritimos(items)
        for datos_item in todos_datos:
            alertas_respuesta.extend(validar_cotizacion(datos_item))

        # When response is XML, extract tarifa_id to find the exact matching record.
        # This handles generacion_cotizacion where best match is 1 of N fetched items.
        if respuesta_final.strip().startswith("<respuesta>"):
            import re as _re
            tid_match = _re.search(r'<tarifa_id>([^<]+)</tarifa_id>', respuesta_final)
            if tid_match:
                tarifa_id_xml = tid_match.group(1).strip()
                matched = [d for d in todos_datos if d.get("id") == tarifa_id_xml]
                if matched:
                    datos_completos = matched[0]
            if datos_completos is None and len(todos_datos) == 1:
                datos_completos = todos_datos[0]

        return success_response({
            "respuesta": respuesta_final,
            "tipo": tipo_pregunta,
            "items_found": len(items),
            "requiere_db": True,
            "razon": clasificacion.get("razon", ""),
            "alertas": alertas_respuesta,
            "datos_completos": datos_completos,
        })

    except Exception as exc:
        print(f"Error en handler maritimo: {exc}")
        import traceback
        traceback.print_exc()
        return error_response(500, str(exc))
