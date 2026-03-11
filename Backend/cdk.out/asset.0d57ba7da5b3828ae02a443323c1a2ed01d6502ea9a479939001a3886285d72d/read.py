import json
import os
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_NAME', 'MaritimeQuotations')
table = dynamodb.Table(table_name)

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "*",
}


def decimal_default(obj):
    """Helper para serializar Decimal a JSON."""
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
    Obtener cotizaciones marítimas.
    GET /maritime-quotations                          → Lista todas (o filtra por GSI params)
    GET /maritime-quotations/{id}                     → Obtiene una por PK
    GET /maritime-quotations?origin_port=X            → Filtra por OriginPortIndex
    GET /maritime-quotations?destination_port=X       → Filtra por DestinationPortIndex
    GET /maritime-quotations?shipping_line=X          → Filtra por ShippingLineIndex
    GET /maritime-quotations?quotation_number=X       → Filtra por QuotationNumberIndex
    """
    print(f"Event: {json.dumps(event)}")

    try:
        path_parameters = event.get("pathParameters") or {}
        query_parameters = event.get("queryStringParameters") or {}

        item_id = path_parameters.get("id")

        # Case 1: Get by primary key
        if item_id:
            response = table.get_item(Key={"id": item_id})

            if "Item" not in response:
                return _error(404, "Maritime quotation not found")

            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps(response["Item"], default=decimal_default),
            }

        # Case 2: Query by GSI parameters
        origin_port = query_parameters.get("origin_port")
        destination_port = query_parameters.get("destination_port")
        shipping_line = query_parameters.get("shipping_line")
        quotation_number = query_parameters.get("quotation_number")

        if quotation_number:
            response = table.query(
                IndexName="QuotationNumberIndex",
                KeyConditionExpression=Key("quotation_number").eq(quotation_number),
            )
        elif origin_port:
            response = table.query(
                IndexName="OriginPortIndex",
                KeyConditionExpression=Key("origin_port").eq(origin_port),
            )
        elif destination_port:
            response = table.query(
                IndexName="DestinationPortIndex",
                KeyConditionExpression=Key("destination_port").eq(destination_port),
            )
        elif shipping_line:
            response = table.query(
                IndexName="ShippingLineIndex",
                KeyConditionExpression=Key("shipping_line").eq(shipping_line),
            )
        else:
            # Case 3: Full scan (list all)
            response = table.scan()

        items = response.get("Items", [])

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({"count": len(items), "items": items}, default=decimal_default),
        }

    except ClientError as exc:
        error_msg = exc.response["Error"]["Message"]
        print(f"DynamoDB Error: {error_msg}")
        return _error(500, f"Database error: {error_msg}")
    except Exception as exc:
        print(f"Error: {exc}")
        return _error(500, str(exc))
