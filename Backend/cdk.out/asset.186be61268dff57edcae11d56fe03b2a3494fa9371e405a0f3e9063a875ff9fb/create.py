import json
import os
import uuid
from decimal import Decimal
from datetime import date
from typing import Optional
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


def _convert_numeric(value):
    """Convierte un valor numérico a Decimal para DynamoDB."""
    if value is None:
        return None
    return Decimal(str(value))


def _convert_line_item(item: dict) -> dict:
    """Convierte los campos numéricos de un line_item a Decimal."""
    converted = {}
    for key, value in item.items():
        if key in ("quantity", "unit_price", "amount"):
            converted[key] = _convert_numeric(value)
        else:
            converted[key] = value
    return converted


def _convert_commodity(commodity: dict) -> dict:
    """Convierte los campos numéricos de un commodity a Decimal."""
    converted = {}
    for key, value in commodity.items():
        if key in ("gross_weight", "volume_cbm"):
            if value is not None:
                converted[key] = _convert_numeric(value)
        else:
            converted[key] = value
    return converted


def _validate_required(body: dict) -> Optional[str]:
    """
    Valida los campos obligatorios.
    Devuelve un mensaje de error o None si todo está OK.
    """
    required_top = ["quotation_number", "dates", "routing", "logistics"]
    for field in required_top:
        if field not in body or body[field] is None:
            return f"Missing required field: {field}"

    dates = body.get("dates", {})
    for date_field in ("quote_date", "valid_from", "valid_till"):
        if not dates.get(date_field):
            return f"Missing required field: dates.{date_field}"

    routing = body.get("routing", {})
    for routing_field in ("origin_port", "destination_port"):
        if not routing.get(routing_field):
            return f"Missing required field: routing.{routing_field}"

    logistics = body.get("logistics", {})
    if not logistics.get("shipping_line"):
        return "Missing required field: logistics.shipping_line"

    return None


def _validate_business_rules(body: dict) -> Optional[str]:
    """
    Aplica reglas de negocio según la especificación ALCE V2.
    Devuelve un mensaje de error o None si todo está OK.
    """
    dates = body.get("dates", {})
    try:
        valid_from = date.fromisoformat(dates["valid_from"])
        valid_till = date.fromisoformat(dates["valid_till"])
        if valid_till <= valid_from:
            return "Business rule violation: valid_till must be after valid_from"
    except (KeyError, ValueError) as exc:
        return f"Invalid date format: {exc}"

    for item in body.get("line_items", []):
        unit_price = item.get("unit_price")
        if unit_price is not None and float(unit_price) < 0:
            return "Business rule violation: unit_price cannot be negative"
        quantity = item.get("quantity")
        if quantity is not None and float(quantity) <= 0:
            return "Business rule violation: quantity must be greater than 0"

    return None


def handler(event, context):
    """
    Crear una nueva cotización marítima.
    POST /maritime-quotations
    """
    print(f"Event: {json.dumps(event)}")

    try:
        # Parsear body
        if event.get("body"):
            body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        else:
            return _error(400, "Body is required")

        # Validar campos requeridos
        validation_error = _validate_required(body)
        if validation_error:
            return _error(400, validation_error)

        # Validar reglas de negocio
        business_error = _validate_business_rules(body)
        if business_error:
            return _error(400, business_error)

        item_id = str(uuid.uuid4())

        # Construir el item con los tipos correctos para DynamoDB
        item = {
            "id": item_id,
            "quotation_number": body["quotation_number"],
            "dates": body["dates"],  # Almacenar fechas como strings ISO 8601
            "routing": {
                "origin_port": body["routing"]["origin_port"],
                "destination_port": body["routing"]["destination_port"],
            },
            "logistics": {
                "shipping_line": body["logistics"]["shipping_line"],
            },
        }

        # GSI projection fields (denormalized for efficient querying)
        item["origin_port"] = body["routing"]["origin_port"]
        item["destination_port"] = body["routing"]["destination_port"]
        item["shipping_line"] = body["logistics"]["shipping_line"]

        # via_port (optional transshipment)
        if body["routing"].get("via_port"):
            item["routing"]["via_port"] = body["routing"]["via_port"]

        # transit_time_days
        if body["logistics"].get("transit_time_days") is not None:
            item["logistics"]["transit_time_days"] = _convert_numeric(
                body["logistics"]["transit_time_days"]
            )

        # Contact / company fields (optional)
        for field in ("prepared_by", "requested_by", "shipment_type", "movement_type", "shipment_term"):
            if body.get(field):
                item[field] = body[field]

        if body.get("company"):
            item["company"] = body["company"]

        # Commodities list
        if body.get("commodities") and isinstance(body["commodities"], list):
            item["commodities"] = [_convert_commodity(c) for c in body["commodities"]]

        # Line items
        if body.get("line_items") and isinstance(body["line_items"], list):
            item["line_items"] = [_convert_line_item(li) for li in body["line_items"]]

        # Totals
        if body.get("total_amount") is not None:
            item["total_amount"] = _convert_numeric(body["total_amount"])

        if body.get("currency"):
            item["currency"] = body["currency"]

        # Terms and conditions (optional nested object)
        if body.get("terms_and_conditions"):
            item["terms_and_conditions"] = body["terms_and_conditions"]

        # Persist to DynamoDB
        table.put_item(Item=item)

        return {
            "statusCode": 201,
            "headers": CORS_HEADERS,
            "body": json.dumps(
                {"message": "Maritime quotation created successfully", "id": item_id, "item": item},
                default=decimal_default,
            ),
        }

    except ClientError as exc:
        error_msg = exc.response["Error"]["Message"]
        print(f"DynamoDB Error: {error_msg}")
        return _error(500, f"Database error: {error_msg}")
    except Exception as exc:
        print(f"Error: {exc}")
        return _error(500, str(exc))
