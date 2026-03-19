import boto3
import json
import os

# --- CONFIGURACIÓN ---
# TABLE_NAME is used by chatbot_terrestre (reads from env at module level)
# MARITIME_TABLE_NAME is used by chatbot_maritimo (reads from env at module level)
# Both env vars must be set for this Lambda.
REGION = os.environ.get('REGION', 'us-east-1')
MODEL_ID = os.environ.get('MODEL_ID', 'amazon.nova-pro-v1:0')

# Shared Bedrock client for domain detection only.
# Each delegate module creates its own bedrock client internally.
bedrock = boto3.client('bedrock-runtime', region_name=REGION)

# Import delegate modules.
# Each module initialises its own DynamoDB table and bedrock client at import time
# using the env vars TABLE_NAME (terrestre) and MARITIME_TABLE_NAME (maritimo).
import chatbot_terrestre as terrestre
import chatbot_maritimo as maritimo

# --- CORS HEADERS ---
CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
}

# --- KEYWORD LISTS ---

_MARITIME_KEYWORDS = [
    "maritimo", "marítimo", "naviera", "contenedor", "container",
    "fcl", "lcl", "shipping", "barco", "buque",
    "flete marítimo", "flete maritimo",
    "bill of lading", "cma cgm", "maersk", "msc", "evergreen", "cosco",
    "hapag", "hs code", "40hc", "20gp", "transbordo",
    "cotización marítima", "cotizacion maritima",
    "puerto de origen", "puerto de destino",
    "rotterdam", "shanghai", "hamburg", "antwerp",
    "q-0", "q-1", "q-2", "q-3", "q-4",
    "q-5", "q-6", "q-7", "q-8", "q-9",
]

_TERRESTRIAL_KEYWORDS = [
    "terrestre", "camión", "camion", "camiones",
    "toneladas", "custodio", "fianza", "cominter",
    "tarifas terrestres", "carga terrestre",
]

# --- DOMAIN DETECTION ---

_DOMAIN_SYSTEM_PROMPT = """
Eres un clasificador de dominio logístico. Determina si la consulta es sobre:
- MARITIMO: logística marítima, puertos, contenedores, navieras, fletes por mar
- TERRESTRE: logística terrestre en Guatemala, camiones, rutas por carretera

El sistema gestiona:
- Transporte TERRESTRE en Guatemala (rutas: Puerto Quetzal→Mixco, Puerto Barrios→Guatemala)
- Cotizaciones MARITIMAS internacionales (Rotterdam→Puerto Barrios, Shanghai→Puerto Quetzal)

Responde ÚNICAMENTE: maritimo | terrestre
"""


def _count_keywords(text_lower, keywords):
    """Return count of keywords found in text_lower."""
    count = 0
    for kw in keywords:
        if kw in text_lower:
            count += 1
    return count


def _classify_domain_with_ai(user_query):
    """
    Uses Nova Pro with max_new_tokens=10 to classify the domain.
    Returns 'maritimo' or 'terrestre'. Defaults to 'terrestre' on error.
    """
    payload = {
        "system": [{"text": _DOMAIN_SYSTEM_PROMPT}],
        "messages": [
            {
                "role": "user",
                "content": [{"text": user_query}],
            }
        ],
        "inferenceConfig": {
            "max_new_tokens": 10,
            "temperature": 0,
            "top_p": 0,
        },
    }

    try:
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json",
        )
        response_body = json.loads(response.get("body").read())
        raw = response_body["output"]["message"]["content"][0]["text"].strip().lower()
        print(f"[central] AI domain classification raw response: '{raw}'")
        if "maritimo" in raw or "marítimo" in raw:
            return "maritimo"
        return "terrestre"
    except Exception as exc:
        print(f"[central] Error in AI domain classification: {exc}")
        return "terrestre"


def detectar_dominio(user_query):
    """
    Detects whether the query belongs to the 'maritimo' or 'terrestre' domain.

    Detection order:
    1. Keyword scoring (fast, no AI cost).
    2. Bedrock AI fallback when the score is tied (both 0 or equal).

    Returns:
        str: 'maritimo' | 'terrestre'
    """
    query_lower = user_query.lower()

    maritime_score = _count_keywords(query_lower, _MARITIME_KEYWORDS)
    terrestrial_score = _count_keywords(query_lower, _TERRESTRIAL_KEYWORDS)

    print(
        f"[central] Domain scores — maritime: {maritime_score}, "
        f"terrestrial: {terrestrial_score}"
    )

    if maritime_score > 0 and terrestrial_score == 0:
        return "maritimo"

    if terrestrial_score > 0 and maritime_score == 0:
        return "terrestre"

    if maritime_score > terrestrial_score:
        return "maritimo"

    if terrestrial_score > maritime_score:
        return "terrestre"

    # Tied (both 0 or equal) → AI fallback
    print("[central] Keyword scores tied — using Bedrock AI for domain classification")
    return _classify_domain_with_ai(user_query)


# --- DELEGATE HANDLERS ---

def _handle_terrestre(user_query, conversation_history):
    """
    Executes the full terrestre pipeline and returns a response dict
    (not yet JSON-serialised) matching the chatbot_terrestre response shape
    plus a 'dominio' field.
    """
    clasificacion = terrestre.paso_0_clasificar_intencion(
        user_query, conversation_history
    )
    tipo_pregunta = clasificacion.get("tipo")
    requiere_db = clasificacion.get("requiere_db")

    if tipo_pregunta == "conversacional" and not requiere_db:
        print("[central] Terrestre: conversational route (no DB)")
        respuesta_final = terrestre.manejar_pregunta_conversacional(
            user_query, conversation_history
        )
        return {
            "respuesta": respuesta_final,
            "tipo": tipo_pregunta,
            "items_found": 0,
            "requiere_db": False,
            "razon": clasificacion.get("razon", ""),
            "dominio": "terrestre",
        }

    print("[central] Terrestre: quotation route (DB query)")
    db_params = terrestre.paso_1_generar_query(user_query, conversation_history)
    peso_kg = db_params.get("peso_kg")
    items = terrestre.paso_2_ejecutar_dynamo(db_params)
    respuesta_final = terrestre.paso_3_generar_respuesta_natural(
        user_query, items, peso_kg, conversation_history
    )

    return {
        "respuesta": respuesta_final,
        "tipo": tipo_pregunta,
        "items_found": len(items),
        "requiere_db": True,
        "razon": clasificacion.get("razon", ""),
        "dominio": "terrestre",
    }


def _handle_maritimo(user_query, conversation_history):
    """
    Executes the full maritime pipeline and returns a response dict
    matching the chatbot_maritimo response shape plus a 'dominio' field.
    """
    clasificacion = maritimo.paso_0_clasificar_y_extraer_filtros(
        user_query, conversation_history
    )
    tipo_pregunta = clasificacion.get("tipo")
    requiere_db = clasificacion.get("requiere_db")

    if tipo_pregunta == "conversacional" and not requiere_db:
        print("[central] Maritimo: conversational route (no DB)")
        respuesta_final = maritimo.manejar_pregunta_conversacional(
            user_query, conversation_history
        )
        return {
            "respuesta": respuesta_final,
            "tipo": tipo_pregunta,
            "items_found": 0,
            "requiere_db": False,
            "razon": clasificacion.get("razon", ""),
            "alertas": [],
            "dominio": "maritimo",
        }

    print("[central] Maritimo: quotation route (DB query)")
    filtros = clasificacion.get("filtros", {})
    db_params = maritimo.paso_1_generar_query(user_query, filtros, conversation_history)
    items = maritimo.paso_2_ejecutar_dynamo(db_params)
    respuesta_final = maritimo.paso_3_generar_respuesta_maritima(
        user_query, items, clasificacion, conversation_history
    )

    # Compute per-item validation alerts
    alertas_respuesta = []
    for item in items:
        datos_item = maritimo.extraer_datos_relevantes_maritimos([item])
        if datos_item:
            alertas_respuesta.extend(maritimo.validar_cotizacion(datos_item[0]))

    return {
        "respuesta": respuesta_final,
        "tipo": tipo_pregunta,
        "items_found": len(items),
        "requiere_db": True,
        "razon": clasificacion.get("razon", ""),
        "alertas": alertas_respuesta,
        "dominio": "maritimo",
    }


# --- LAMBDA HANDLER ---

def handler(event, context):  # noqa: ARG001
    """
    Centralized chatbot handler that routes queries to the correct domain chatbot.

    REQUEST FORMAT:
    {
        "query": "string",
        "conversation_history": [
            {"role": "user",      "content": [{"text": "..."}]},
            {"role": "assistant", "content": [{"text": "..."}]}
        ]
    }

    RESPONSE FORMAT:
    {
        "respuesta": "...",
        "tipo": "cotizacion" | "conversacional",
        "items_found": int,
        "requiere_db": bool,
        "razon": "...",
        "dominio": "maritimo" | "terrestre",
        "alertas": ["..."]          // only present for maritime responses
    }
    """
    try:
        body = json.loads(event.get("body", "{}"))
        user_query = body.get("query")
        conversation_history = body.get("conversation_history", [])

        if not user_query:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "Falta el campo 'query'"}),
            }

        print(f"\n{'='*80}")
        print("NUEVA PETICION CENTRAL")
        print(f"{'='*80}")
        print(f"Pregunta: {user_query}")
        print(f"Historial: {len(conversation_history)} mensajes")
        print(f"{'='*80}\n")

        # Step 1: detect domain
        dominio = detectar_dominio(user_query)
        print(f"[central] Detected domain: {dominio}")

        # Step 2: delegate to the appropriate chatbot
        if dominio == "maritimo":
            response_data = _handle_maritimo(user_query, conversation_history)
            encoder_cls = maritimo.DecimalEncoder
        else:
            response_data = _handle_terrestre(user_query, conversation_history)
            encoder_cls = terrestre.DecimalEncoder

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps(response_data, cls=encoder_cls),
        }

    except Exception as exc:
        print(f"[central] Error in handler: {exc}")
        import traceback
        traceback.print_exc()

        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": str(exc)}),
        }
