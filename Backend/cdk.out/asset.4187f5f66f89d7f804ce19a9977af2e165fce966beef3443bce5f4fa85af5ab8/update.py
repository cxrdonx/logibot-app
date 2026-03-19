import json
import os
from decimal import Decimal
from datetime import datetime
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


def _error(status_code: int, message: str) -> dict:
    return {"statusCode": status_code, "headers": CORS_HEADERS, "body": json.dumps({"error": message})}


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def _floats_to_decimal(obj):
    """Recursively convert float -> Decimal for DynamoDB storage."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _floats_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_floats_to_decimal(i) for i in obj]
    return obj


def handler(event, context):
    """
    PUT /cotizaciones/{id}
    Body: { "datos": { ...all updated cotizacion fields... }, "estado": "..." (optional) }

    Updates datos and/or estado for an existing cotizacion.
    Always stamps fecha_actualizacion.
    Returns 404 if the id does not exist.
    """
    try:
        path_parameters = event.get("pathParameters") or {}
        item_id = path_parameters.get("id")

        if not item_id:
            return _error(400, "Missing path parameter: id")

        body = (
            json.loads(event["body"])
            if isinstance(event.get("body"), str)
            else (event.get("body") or {})
        )

        if not body:
            return _error(400, "Request body is required")

        update_parts = []
        expr_attr_names = {}
        expr_attr_values = {}

        if "datos" in body:
            update_parts.append("#datos = :datos")
            expr_attr_names["#datos"] = "datos"
            expr_attr_values[":datos"] = _floats_to_decimal(body["datos"])

        if "estado" in body:
            update_parts.append("#estado = :estado")
            expr_attr_names["#estado"] = "estado"
            expr_attr_values[":estado"] = body["estado"]

        # Require at least one user-supplied field before proceeding
        if not update_parts:
            return _error(400, "Nothing to update — provide 'datos' and/or 'estado'")

        # Always stamp last-update timestamp
        update_parts.append("#fecha_act = :fecha_act")
        expr_attr_names["#fecha_act"] = "fecha_actualizacion"
        expr_attr_values[":fecha_act"] = datetime.utcnow().isoformat()

        result = table.update_item(
            Key={"id": item_id},
            UpdateExpression="SET " + ", ".join(update_parts),
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values,
            ReturnValues="ALL_NEW",
            ConditionExpression="attribute_exists(id)",
        )

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps(
                {"message": "Cotizacion actualizada exitosamente", "item": result.get("Attributes", {})},
                default=decimal_default,
            ),
        }

    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        if code == "ConditionalCheckFailedException":
            return _error(404, f"Cotizacion with id '{item_id}' not found")
        return _error(500, f"Database error: {exc.response['Error']['Message']}")
    except Exception as exc:
        return _error(500, str(exc))
