import boto3
import json
import os
import re
from decimal import Decimal
from boto3.dynamodb.conditions import Key

# --- CONFIGURACIÓN ---
TABLE_NAME = os.environ.get('MARITIME_TABLE_NAME', 'MaritimeQuotations')
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


# --- SCHEMA DE LA TABLA MARITIMA ---
_MARITIME_SCHEMA_INFO = """
ESTRUCTURA DE TABLA DYNAMODB ('MaritimeQuotations'):
- Partition Key: id (String, UUID)
- Atributos clave: quotation_number, origin_port, destination_port, shipping_line
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
4. IndexName: 'QuotationNumberIndex' -> PK: 'quotation_number'
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

- Si el usuario pregunta por una ruta específica, muestra las cotizaciones disponibles en la base de datos
- Si el usuario pide calcular un total, verifica contra la fórmula y alerta si hay discrepancia
- Si el usuario pide comparar navieras, presenta tabla comparativa con tiempos y costos
- Si no hay datos disponibles para la consulta, indica claramente y sugiere qué información proporcionar
"""


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
    except Exception as exc:
        print(f"Error invocando Bedrock: {exc}")
        raise exc


def construir_contexto_conversacion(conversation_history):
    """
    Construye un resumen del contexto de la conversación marítima.
    Extrae información clave: puertos, navieras, números de cotización.

    Args:
        conversation_history: Lista de mensajes previos del frontend
    """
    if not conversation_history:
        return "PRIMERA PREGUNTA (sin contexto previo)"

    contexto_enriquecido = {
        "puertos_mencionados": [],
        "navieras_mencionadas": [],
        "cotizaciones_mencionadas": [],
    }

    for msg in conversation_history[-10:]:
        text = msg["content"][0]["text"]

        # Extraer números de cotización (patrón Q-XXXXXX)
        cotizaciones = re.findall(r'Q-\d+', text, re.IGNORECASE)
        if cotizaciones:
            contexto_enriquecido["cotizaciones_mencionadas"].extend(cotizaciones)

        # Extraer navieras conocidas
        navieras = re.findall(
            r'\b(CMA CGM|MAERSK|MSC|EVERGREEN|COSCO|HAPAG-LLOYD|ONE|YANG MING|ZIM)\b',
            text, re.IGNORECASE
        )
        if navieras:
            contexto_enriquecido["navieras_mencionadas"].extend(navieras)

        # Extraer códigos de puerto (patrón XXXXXCODE - PORT, COUNTRY)
        puertos = re.findall(r'\b[A-Z]{5}\b', text)
        if puertos:
            contexto_enriquecido["puertos_mencionados"].extend(puertos)

    contexto = "CONTEXTO DE CONVERSACION MARITIMA:\n\n"

    if contexto_enriquecido["cotizaciones_mencionadas"]:
        cotizaciones_unicas = list(set(contexto_enriquecido["cotizaciones_mencionadas"][-3:]))
        contexto += f"Cotizaciones discutidas: {', '.join(cotizaciones_unicas)}\n"

    if contexto_enriquecido["navieras_mencionadas"]:
        navieras_unicas = list(set(contexto_enriquecido["navieras_mencionadas"][-3:]))
        contexto += f"Navieras mencionadas: {', '.join(navieras_unicas)}\n"

    if contexto_enriquecido["puertos_mencionados"]:
        puertos_unicos = list(set(contexto_enriquecido["puertos_mencionados"][-5:]))
        contexto += f"Puertos mencionados: {', '.join(puertos_unicos)}\n"

    contexto += "\nULTIMOS MENSAJES:\n"
    for msg in conversation_history[-6:]:
        role = "Usuario" if msg["role"] == "user" else "ALCE"
        text = msg["content"][0]["text"]
        contexto += f"{role}: {text[:300]}...\n" if len(text) > 300 else f"{role}: {text}\n"

    return contexto


def paso_0_clasificar_intencion(pregunta_usuario, conversation_history=None):
    """
    Clasifica si la pregunta requiere consultar DynamoDB o puede responderse con el historial.

    Returns:
        dict: {
            "tipo": "cotizacion" | "conversacional",
            "requiere_db": bool,
            "razon": str
        }
    """
    contexto_previo = construir_contexto_conversacion(conversation_history)

    system_prompt = f"""
    Eres un clasificador inteligente para un chatbot de logística MARITIMA (ALCE).

    TU MISION: Determinar si la pregunta NECESITA consultar la base de datos de cotizaciones marítimas
    o puede responderse con el contexto de conversación previo.

    REGLAS DE CLASIFICACION:

    1. COTIZACION (requiere_db=true) cuando:
       - Usuario pregunta por cotizaciones de un puerto/naviera NUEVA (no mencionada antes)
       - Usuario pide buscar cotizaciones por número (Q-XXXXXX)
       - Usuario solicita información que NO está en el historial previo
       - Ejemplos: "¿Cotizaciones desde Rotterdam?", "Busca Q-000793", "¿Qué navieras van a Guatemala?"

    2. CONVERSACIONAL (requiere_db=false) cuando:
       - Usuario pregunta sobre información YA PROPORCIONADA en el historial
       - Usuario pide calcular o verificar totales de una cotización ya mostrada
       - Usuario hace preguntas de seguimiento sobre la MISMA cotización
       - Saludos, agradecimientos, preguntas generales sobre logística marítima
       - Ejemplos: "¿Cuál es el total?", "¿Qué navieras hay?", "Verifica el cálculo", "Gracias"

    FORMATO DE SALIDA (solo JSON, sin explicaciones):
    {{
        "tipo": "cotizacion",
        "requiere_db": true,
        "razon": "Nueva consulta de puerto: Rotterdam"
    }}

    IMPORTANTE: Devuelve SOLO el JSON, sin texto adicional.

    {contexto_previo}
    """

    try:
        respuesta_llm = invoke_nova_pro(system_prompt, pregunta_usuario)
        clean_json = respuesta_llm.replace("```json", "").replace("```", "").strip()
        clasificacion = json.loads(clean_json)

        print(f"\n{'='*60}")
        print("CLASIFICACION DE INTENCION (maritimo):")
        print(f"{'='*60}")
        print(json.dumps(clasificacion, indent=2, ensure_ascii=False))
        print(f"{'='*60}\n")

        return clasificacion

    except Exception as exc:
        print(f"Error en clasificacion de intencion maritima: {exc}")
        return {
            "tipo": "cotizacion",
            "requiere_db": True,
            "razon": "Error en clasificacion, ejecutando flujo completo por seguridad"
        }


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


def paso_1_generar_query(pregunta_usuario, conversation_history=None):
    """
    Usa Nova Pro para decidir qué índice GSI usar y generar los parámetros de consulta.

    Returns:
        dict con fields: index, origin_port, destination_port, shipping_line,
                         quotation_number, busqueda_amplia
    """
    contexto_previo = construir_contexto_conversacion(conversation_history)

    system_prompt = f"""
    Eres un experto en DynamoDB y análisis de contexto conversacional para logística MARITIMA.

    TU MISION: Analizar la pregunta y el contexto para generar la mejor estrategia de consulta
    en la tabla MaritimeQuotations.

    {_MARITIME_SCHEMA_INFO}

    FORMATO DE SALIDA (solo JSON, sin explicaciones):
    {{
        "index": "OriginPortIndex",
        "origin_port": "NLRTM - ROTTERDAM, NETHERLANDS",
        "destination_port": null,
        "shipping_line": null,
        "quotation_number": null,
        "busqueda_amplia": false
    }}

    REGLAS DE SELECCION DE INDICE:
    1. Si el usuario menciona número de cotización (Q-XXXXXX) → "QuotationNumberIndex"
    2. Si menciona origen Y destino → "OriginPortIndex" (y filtra destino en Python)
    3. Si SOLO menciona puerto de origen → "OriginPortIndex"
    4. Si SOLO menciona puerto de destino → "DestinationPortIndex"
    5. Si SOLO menciona naviera → "ShippingLineIndex"
    6. Si NO hay criterio específico → busqueda_amplia: true (scan completo)

    NORMALIZACION DE PUERTOS:
    - Usar formato completo si es posible: "NLRTM - ROTTERDAM, NETHERLANDS"
    - Si solo se menciona el nombre: "Rotterdam" → "NLRTM - ROTTERDAM, NETHERLANDS" (si se conoce)
    - Si no se conoce el código → usar el nombre tal como aparece en la pregunta

    REGLAS ADICIONALES:
    - Si el usuario pide "todas las cotizaciones" → busqueda_amplia: true
    - Si menciona una naviera sin puerto → "ShippingLineIndex"
    - Si el contexto tiene información de puertos/navieras previas, usar esa información

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


def paso_2_ejecutar_dynamo(params):
    """
    Ejecuta la query en MaritimeQuotations usando los parámetros generados.
    Nunca devuelve vacío — hace scan completo como último recurso.
    """
    index_name = params.get("index")
    origin_port = params.get("origin_port")
    destination_port = params.get("destination_port")
    shipping_line = params.get("shipping_line")
    quotation_number = params.get("quotation_number")
    busqueda_amplia = params.get("busqueda_amplia", False)

    print(f"\n{'='*60}")
    print(f"EJECUTANDO QUERY MARITIMA EN INDICE: {index_name}")
    print(f"{'='*60}")
    print(f"Origin: {origin_port}, Destination: {destination_port}")
    print(f"Naviera: {shipping_line}, Cotizacion: {quotation_number}")
    print(f"Busqueda amplia: {busqueda_amplia}")
    print(f"{'='*60}\n")

    try:
        items = []

        # ESTRATEGIA 1: Query con índice específico
        if not busqueda_amplia:
            query_params = None

            if index_name == "QuotationNumberIndex" and quotation_number:
                query_params = {
                    "IndexName": index_name,
                    "KeyConditionExpression": Key("quotation_number").eq(quotation_number),
                }
            elif index_name == "OriginPortIndex" and origin_port:
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


def extraer_datos_relevantes_maritimos(items):
    """
    Extrae y simplifica los datos de las cotizaciones marítimas para enviar al LLM.
    Convierte Decimals a float para serialización JSON.
    """
    datos_simplificados = []

    for item in items:
        # Convertir line_items con Decimals
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

        # Convertir commodities con Decimals
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

        # Logistics
        logistics = item.get("logistics", {})
        logistics_converted = {
            "shipping_line": logistics.get("shipping_line", ""),
        }
        if logistics.get("transit_time_days") is not None:
            logistics_converted["transit_time_days"] = float(logistics["transit_time_days"])

        datos_simplificados.append({
            "id": item.get("id"),
            "quotation_number": item.get("quotation_number"),
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
        from datetime import date as _date
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
        # Si hay transbordo, solo informar (no es un error)
        alertas.append(
            f"INFO TRANSBORDO: Ruta con transbordo vía {routing['via_port']}. "
            f"Verificar tiempos de tránsito parciales (origen→via y via→destino)."
        )

    return alertas


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

    # Indicar transbordo si aplica
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


def generar_xml_maritimo(datos: dict) -> str:
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

    # Unidad: tipo de contenedor del primer commodity
    tipo_unidad = "Contenedor Marítimo"
    peso_solicitado = 0
    if commodities:
        tipo_unidad = commodities[0].get("container_type") or tipo_unidad
        peso_solicitado = float(commodities[0].get("gross_weight") or 0)

    # Tarifa base: primer line_item (generalmente Ocean Freight / Flete)
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

    # Detalles: tiempo de tránsito y transbordo
    transit = logistics.get("transit_time_days")
    detalles_parts = []
    if transit is not None:
        detalles_parts.append(f"Tiempo de tránsito: {int(float(transit))} días")
    via_port = routing.get("via_port", "")
    if via_port:
        detalles_parts.append(f"Transbordo vía: {via_port}")
    detalles = " | ".join(detalles_parts)

    # Nota: vigencia de la cotización
    dates = datos.get("dates", {})
    valid_till = dates.get("valid_till", "")
    q_number = datos.get("quotation_number", "")
    nota_parts = []
    if q_number:
        nota_parts.append(f"Cotización #{q_number}")
    if valid_till:
        nota_parts.append(f"Válida hasta {valid_till}")
    nota = " | ".join(nota_parts)

    # Construir XML de costos adicionales
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
  </cotizacion>
</respuesta>"""

    return xml


def paso_3_generar_respuesta_maritima(pregunta, items, conversation_history=None):
    """
    Genera la respuesta final basada en los datos de cotizaciones marítimas.
    - Si hay exactamente 1 cotización: devuelve XML para renderizar tarjeta en el frontend.
    - Si hay múltiples: devuelve formato Markdown con listado comparativo.

    Returns:
        str: XML (1 resultado) o Markdown (múltiples resultados).
    """
    if not items:
        return (
            "No encontré cotizaciones marítimas que coincidan con tu consulta.\n\n"
            "Puedes buscar por:\n"
            "- Número de cotización (ej. Q-000793)\n"
            "- Puerto de origen (ej. NLRTM - ROTTERDAM, NETHERLANDS)\n"
            "- Puerto de destino (ej. GTPBR - PUERTO BARRIOS, GUATEMALA)\n"
            "- Naviera (ej. CMA CGM, MAERSK, MSC)\n\n"
            "¿Qué información puedes proporcionarme?"
        )

    # Extraer datos completos (se usan internamente para validación)
    datos_optimizados = extraer_datos_relevantes_maritimos(items)

    # Ejecutar validaciones de negocio ALCE V2 sobre datos completos
    todas_las_alertas = []
    for datos in datos_optimizados:
        alertas = validar_cotizacion(datos)
        if alertas:
            cotizacion_num = datos.get("quotation_number", datos.get("id", "N/A"))
            for alerta in alertas:
                todas_las_alertas.append(f"[{cotizacion_num}] {alerta}")

    print(f"\n{'='*60}")
    print(f"VALIDACIONES MARITIMAS: {len(todas_las_alertas)} alertas detectadas")
    for alerta in todas_las_alertas:
        print(f"  - {alerta}")
    print(f"{'='*60}\n")

    count = len(datos_optimizados)

    # CASO: cotización única → devolver XML para tarjeta en el frontend
    if count == 1:
        print(f"{'='*60}")
        print("GENERANDO XML MARITIMO para tarjeta en frontend")
        print(f"{'='*60}\n")
        return generar_xml_maritimo(datos_optimizados[0])

    # CASO: múltiples cotizaciones → Markdown comparativo
    encabezado = f"Encontré **{count} cotizaciones**:"

    bloques = []
    for i, datos in enumerate(datos_optimizados, start=1):
        q_num = datos.get("quotation_number", "")
        titulo = f"### Cotización {q_num}" if q_num else f"### Cotización #{i}"
        bloques.append(titulo + "\n" + _formatear_cotizacion(datos))

    respuesta = encabezado + "\n\n" + "\n\n---\n\n".join(bloques)

    if todas_las_alertas:
        respuesta += "\n\n---\n\n⚠️ **Alertas de validación:**\n"
        for alerta in todas_las_alertas:
            respuesta += f"- {alerta}\n"

    print(f"\n{'='*60}")
    print(f"RESPUESTA MARITIMA FORMATEADA ({count} cotizaciones, Markdown comparativo)")
    print(f"{'='*60}\n")

    return respuesta


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
        "tipo": "cotizacion" | "conversacional",
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
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
                    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
                },
                "body": json.dumps({"error": "Falta el campo 'query'"})
            }

        print(f"\n{'='*80}")
        print("NUEVA PETICION MARITIMA (ALCE V2)")
        print(f"{'='*80}")
        print(f"Pregunta: {user_query}")
        print(f"Historial: {len(conversation_history)} mensajes")
        print(f"{'='*80}\n")

        # PASO 0: CLASIFICACION INTELIGENTE DE INTENCION
        clasificacion = paso_0_clasificar_intencion(user_query, conversation_history)
        tipo_pregunta = clasificacion.get('tipo')
        requiere_db = clasificacion.get('requiere_db')

        # RUTA 1: PREGUNTA CONVERSACIONAL (sin consulta DB)
        if tipo_pregunta == "conversacional" and not requiere_db:
            print("RUTA CONVERSACIONAL MARITIMA ACTIVADA (sin consulta DB)")
            respuesta_final = manejar_pregunta_conversacional(user_query, conversation_history)

            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
                    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
                },
                "body": json.dumps({
                    "respuesta": respuesta_final,
                    "tipo": tipo_pregunta,
                    "items_found": 0,
                    "requiere_db": False,
                    "razon": clasificacion.get('razon', ''),
                    "alertas": [],
                }, cls=DecimalEncoder)
            }

        # RUTA 2: COTIZACION (consulta DB completa)
        print("RUTA COTIZACION MARITIMA ACTIVADA (consulta DynamoDB)")

        # 1. Generar estrategia de query
        db_params = paso_1_generar_query(user_query, conversation_history)
        print(f"Estrategia DB maritima: {db_params}")

        # 2. Recuperar datos de DynamoDB
        items = paso_2_ejecutar_dynamo(db_params)
        print(f"Cotizaciones encontradas: {len(items)}")

        # 3. Generar respuesta con validaciones automáticas
        respuesta_final = paso_3_generar_respuesta_maritima(
            user_query,
            items,
            conversation_history
        )

        # 4. Calcular alertas de validación para incluir en respuesta
        alertas_respuesta = []
        for item in items:
            datos_item = extraer_datos_relevantes_maritimos([item])
            if datos_item:
                alertas = validar_cotizacion(datos_item[0])
                alertas_respuesta.extend(alertas)

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            },
            "body": json.dumps({
                "respuesta": respuesta_final,
                "tipo": tipo_pregunta,
                "items_found": len(items),
                "requiere_db": True,
                "razon": clasificacion.get('razon', ''),
                "alertas": alertas_respuesta,
            }, cls=DecimalEncoder)
        }

    except Exception as exc:
        print(f"Error en handler maritimo: {exc}")
        import traceback
        traceback.print_exc()

        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
            },
            "body": json.dumps({"error": str(exc)})
        }
