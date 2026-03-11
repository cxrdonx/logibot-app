import json
import os
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_NAME', 'MaritimeQuotations')
table = dynamodb.Table(table_name)

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
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
    Eliminar una cotización marítima.
    DELETE /maritime-quotations/{id}
    """
    print(f"Event: {json.dumps(event)}")

    try:
        path_parameters = event.get("pathParameters") or {}
        item_id = path_parameters.get("id")

        if not item_id:
            return _error(400, "ID is required in path")

        # Verify item exists before deleting
        existing = table.get_item(Key={"id": item_id})
        if "Item" not in existing:
            return _error(404, "Maritime quotation not found")

        table.delete_item(Key={"id": item_id})

        return {
            "statusCode": 204,
            "headers": CORS_HEADERS,
            "body": json.dumps(
                {"message": "Maritime quotation deleted successfully", "id": item_id}
            ),
        }

    except ClientError as exc:
        error_msg = exc.response["Error"]["Message"]
        print(f"DynamoDB Error: {error_msg}")
        return _error(500, f"Database error: {error_msg}")
    except Exception as exc:
        print(f"Error: {exc}")
        return _error(500, str(exc))
