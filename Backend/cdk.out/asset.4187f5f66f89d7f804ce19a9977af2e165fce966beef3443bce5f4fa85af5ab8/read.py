import json
import os
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

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


def handler(event, context):
    """
    GET /cotizaciones                → List all cotizaciones
    GET /cotizaciones?tipo=terrestre → Filter by tipo via TipoIndex
    GET /cotizaciones/{id}           → Get one by PK
    """
    try:
        path_parameters = event.get("pathParameters") or {}
        query_parameters = event.get("queryStringParameters") or {}

        item_id = path_parameters.get("id")

        # Get single by PK
        if item_id:
            response = table.get_item(Key={"id": item_id})
            if "Item" not in response:
                return _error(404, "Cotización not found")
            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps(response["Item"], default=decimal_default),
            }

        # Filter by tipo
        tipo = query_parameters.get("tipo")
        if tipo:
            response = table.query(
                IndexName="TipoIndex",
                KeyConditionExpression=Key("tipo").eq(tipo),
                ScanIndexForward=False,  # newest first
            )
        else:
            # Full scan — all cotizaciones
            response = table.scan()

        items = response.get("Items", [])
        # Sort by fecha_creacion descending
        items.sort(key=lambda x: x.get("fecha_creacion", ""), reverse=True)

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({"count": len(items), "items": items}, default=decimal_default),
        }

    except ClientError as exc:
        return _error(500, f"Database error: {exc.response['Error']['Message']}")
    except Exception as exc:
        return _error(500, str(exc))
