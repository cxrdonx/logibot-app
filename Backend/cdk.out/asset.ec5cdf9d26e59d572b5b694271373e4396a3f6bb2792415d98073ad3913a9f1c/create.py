import json
import os
import uuid
from datetime import datetime
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_NAME', 'Cotizaciones')
table = dynamodb.Table(table_name)

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
}


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def _error(status_code: int, message: str) -> dict:
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps({"error": message}),
    }


def _floats_to_decimal(obj):
    """Recursively convert float values to Decimal for DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _floats_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_floats_to_decimal(i) for i in obj]
    return obj


def handler(event, context):
    """
    POST /cotizaciones
    Body:
    {
        "numero_cotizacion": "Q-A3F7B2C1",
        "tipo": "terrestre" | "maritimo",
        "tarifa_id": "uuid-of-source-tarifa (optional)",
        "datos": { ...XMLQuotation fields... }
    }
    """
    try:
        body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else (event.get("body") or {})

        numero_cotizacion = body.get("numero_cotizacion")
        tipo = body.get("tipo", "terrestre")
        tarifa_id = body.get("tarifa_id", "")
        datos = body.get("datos", {})

        if not numero_cotizacion:
            return _error(400, "Missing required field: numero_cotizacion")
        if not datos:
            return _error(400, "Missing required field: datos")

        item_id = str(uuid.uuid4())
        fecha_creacion = datetime.utcnow().isoformat()

        item = {
            "id": item_id,
            "numero_cotizacion": numero_cotizacion,
            "tipo": tipo,
            "tarifa_id": tarifa_id,
            "fecha_creacion": fecha_creacion,
            "estado": "aceptada",
            "datos": _floats_to_decimal(datos),
        }

        table.put_item(Item=item)

        return {
            "statusCode": 201,
            "headers": CORS_HEADERS,
            "body": json.dumps(
                {"message": "Cotización guardada exitosamente", "id": item_id, "numero_cotizacion": numero_cotizacion},
                default=decimal_default,
            ),
        }

    except ClientError as exc:
        return _error(500, f"Database error: {exc.response['Error']['Message']}")
    except Exception as exc:
        return _error(500, str(exc))
