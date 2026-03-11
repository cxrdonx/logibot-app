import json
import os
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_NAME', 'TarifasLogistica')
table = dynamodb.Table(table_name)

def decimal_default(obj):
    """Helper para serializar Decimal a JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def handler(event, context):
    """
    Actualizar una tarifa logística existente
    PUT /tarifas/{id}
    Body: {
        "fianza": 1200,
        "estadia": 550,
        "rango_base_precios": [...]
    }
    """
    print(f"Event: {json.dumps(event)}")
    
    try:
        # Obtener ID de los path parameters
        path_parameters = event.get('pathParameters', {}) or {}
        item_id = path_parameters.get('id')
        
        if not item_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "ID is required in path"})
            }
        
        # Parsear el body
        if 'body' in event and event['body']:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Body is required"})
            }
        
        # Verificar que el item existe
        existing_item = table.get_item(Key={'id': item_id})
        if 'Item' not in existing_item:
            return {
                "statusCode": 404,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Tarifa not found"})
            }
        
        # Construir la expresión de actualización
        update_expression = "SET "
        expression_attribute_values = {}
        expression_attribute_names = {}
        
        # Campos que se pueden actualizar
        updatable_fields = {
            'origen': str,
            'destino': str,
            'proveedor': str,
            'fianza': Decimal,
            'dias_libres': Decimal,
            'estadia': Decimal,
            'tramite_de_aduana_cominter': Decimal,
            'condiciones_de_aduana_cominter': str,
            'tramite_aduana': Decimal,
            'condiciones_aduana': str,
            'custodio_comsi': Decimal,
            'custodio_yantarni': Decimal
        }
        
        update_parts = []
        for field, field_type in updatable_fields.items():
            if field in body:
                # Usar attribute names para evitar palabras reservadas
                attr_name = f"#{field}"
                attr_value = f":{field}"
                
                expression_attribute_names[attr_name] = field
                
                if field_type == Decimal:
                    expression_attribute_values[attr_value] = Decimal(str(body[field]))
                else:
                    expression_attribute_values[attr_value] = body[field]
                
                update_parts.append(f"{attr_name} = {attr_value}")
        
        # Manejar rango_base_precios por separado
        if 'rango_base_precios' in body and isinstance(body['rango_base_precios'], list):
            rangos_decimal = []
            for rango in body['rango_base_precios']:
                rangos_decimal.append({
                    'min_kg': Decimal(str(rango.get('min_kg', 0))),
                    'max_kg': Decimal(str(rango.get('max_kg', 0))),
                    'costo': Decimal(str(rango.get('costo', 0))),
                    'concepto': rango.get('concepto', '')
                })
            
            expression_attribute_names['#rango_base_precios'] = 'rango_base_precios'
            expression_attribute_values[':rango_base_precios'] = rangos_decimal
            update_parts.append("#rango_base_precios = :rango_base_precios")
        
        if not update_parts:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "No valid fields to update"})
            }
        
        update_expression += ", ".join(update_parts)
        
        # Actualizar el item
        response = table.update_item(
            Key={'id': item_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="ALL_NEW"
        )
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "message": "Tarifa updated successfully",
                "item": response['Attributes']
            }, default=decimal_default)
        }
        
    except ClientError as e:
        print(f"DynamoDB Error: {e.response['Error']['Message']}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": f"Database error: {e.response['Error']['Message']}"})
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(e)})
        }
