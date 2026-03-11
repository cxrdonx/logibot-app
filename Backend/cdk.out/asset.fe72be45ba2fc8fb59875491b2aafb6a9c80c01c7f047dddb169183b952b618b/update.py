import json
import os
from decimal import Decimal
from datetime import date
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


def _validate_business_rules(body: dict) -> str | None:
    """
    Aplica reglas de negocio según la especificación ALCE V2.
    Devuelve un mensaje de error o None si todo está OK.
    """
    dates = body.get("dates")
    if dates:
        valid_from_str = dates.get("valid_from")
        valid_till_str = dates.get("valid_till")
        if valid_from_str and valid_till_str:
            try:
                valid_from = date.fromisoformat(valid_from_str)
                valid_till = date.fromisoformat(valid_till_str)
                if valid_till <= valid_from:
                    return "Business rule violation: valid_till must be after valid_from"
            except ValueError as exc:
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
    Actualizar una cotización marítima existente.
    PUT /maritime-quotations/{id}
    """
    print(f"Event: {json.dumps(event)}")

    try:
        path_parameters = event.get("pathParameters") or {}
        item_id = path_parameters.get("id")

        if not item_id:
            return _error(400, "ID is required in path")

        # Parsear body
        if event.get("body"):
            body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        else:
            return _error(400, "Body is required")

        # Verify item exists
        existing = table.get_item(Key={"id": item_id})
        if "Item" not in existing:
            return _error(404, "Maritime quotation not found")

        # Validate business rules on provided fields
        business_error = _validate_business_rules(body)
        if business_error:
            return _error(400, business_error)

        # Build update expression dynamically
        update_parts = []
        expression_attribute_names = {}
        expression_attribute_values = {}

        # Simple string/object fields that can be updated directly
        simple_fields = [
            "quotation_number",
            "dates",
            "prepared_by",
            "requested_by",
            "company",
            "shipment_type",
            "movement_type",
            "shipment_term",
            "routing",
            "terms_and_conditions",
            "currency",
        ]
        for field in simple_fields:
            if field in body:
                attr_name = f"#{field}"
                attr_value = f":{field}"
                expression_attribute_names[attr_name] = field
                expression_attribute_values[attr_value] = body[field]
                update_parts.append(f"{attr_name} = {attr_value}")

        # Update GSI projection fields when routing changes
        if "routing" in body:
            routing = body["routing"]
            if routing.get("origin_port"):
                expression_attribute_names["#origin_port"] = "origin_port"
                expression_attribute_values[":origin_port"] = routing["origin_port"]
                update_parts.append("#origin_port = :origin_port")
            if routing.get("destination_port"):
                expression_attribute_names["#destination_port"] = "destination_port"
                expression_attribute_values[":destination_port"] = routing["destination_port"]
                update_parts.append("#destination_port = :destination_port")

        # Logistics (nested with numeric field)
        if "logistics" in body:
            logistics_to_store = {}
            if body["logistics"].get("shipping_line"):
                logistics_to_store["shipping_line"] = body["logistics"]["shipping_line"]
                # Update GSI projection field
                expression_attribute_names["#shipping_line"] = "shipping_line"
                expression_attribute_values[":shipping_line"] = body["logistics"]["shipping_line"]
                update_parts.append("#shipping_line = :shipping_line")
            if body["logistics"].get("transit_time_days") is not None:
                logistics_to_store["transit_time_days"] = _convert_numeric(
                    body["logistics"]["transit_time_days"]
                )
            if logistics_to_store:
                expression_attribute_names["#logistics"] = "logistics"
                expression_attribute_values[":logistics"] = logistics_to_store
                update_parts.append("#logistics = :logistics")

        # Commodities (list with numeric fields)
        if "commodities" in body and isinstance(body["commodities"], list):
            expression_attribute_names["#commodities"] = "commodities"
            expression_attribute_values[":commodities"] = [
                _convert_commodity(c) for c in body["commodities"]
            ]
            update_parts.append("#commodities = :commodities")

        # Line items (list with numeric fields)
        if "line_items" in body and isinstance(body["line_items"], list):
            expression_attribute_names["#line_items"] = "line_items"
            expression_attribute_values[":line_items"] = [
                _convert_line_item(li) for li in body["line_items"]
            ]
            update_parts.append("#line_items = :line_items")

        # Total amount
        if "total_amount" in body and body["total_amount"] is not None:
            expression_attribute_names["#total_amount"] = "total_amount"
            expression_attribute_values[":total_amount"] = _convert_numeric(body["total_amount"])
            update_parts.append("#total_amount = :total_amount")

        if not update_parts:
            return _error(400, "No valid fields to update")

        update_expression = "SET " + ", ".join(update_parts)

        response = table.update_item(
            Key={"id": item_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="ALL_NEW",
        )

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps(
                {"message": "Maritime quotation updated successfully", "item": response["Attributes"]},
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
