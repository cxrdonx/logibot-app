import json
import os
import uuid
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
    Crear una nueva tarifa logística
    POST /tarifas
    Body: {
        "origen": "Puerto Quetzal",
        "destino": "Mixco",
        "proveedor": "Nixon Larios",
        "fianza": 1000,
        "dias_libres": 3,
        "estadia": 500,
        "tramite_de_aduana_cominter": 825,
        "condiciones_de_aduana_cominter": "HASTA 50 LINEAS...",
        "tramite_aduana": 650,
        "condiciones_aduana": "HASTA 10 LINEAS...",
        "custodio_comsi": 450,
        "custodio_yantarni": 375,
        "rango_base_precios": [
            {
                "min_kg": 0,
                "max_kg": 20999,
                "costo": 3600,
                "concepto": "Tarifa Base"
            }
        ]
    }
    """
    print(f"Event: {json.dumps(event)}")
    
    try:
        # Parsear el body
        if 'body' in event and event['body']:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Body is required"})
            }
        
        # Validar campos requeridos
        required_fields = ['origen', 'destino', 'proveedor']
        for field in required_fields:
            if field not in body:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                    "body": json.dumps({"error": f"Missing required field: {field}"})
                }
        
        # Generar ID único
        item_id = str(uuid.uuid4())
        
        # Convertir números a Decimal para DynamoDB
        item = {
            'id': item_id,
            'origen': body['origen'],
            'destino': body['destino'],
            'proveedor': body['proveedor'],
        }
        
        # Campos opcionales numéricos
        numeric_fields = ['fianza', 'dias_libres', 'estadia', 'tramite_de_aduana_cominter', 
                         'tramite_aduana', 'custodio_comsi', 'custodio_yantarni']
        for field in numeric_fields:
            if field in body:
                item[field] = Decimal(str(body[field]))
        
        # Campos opcionales de texto
        text_fields = ['condiciones_de_aduana_cominter', 'condiciones_aduana']
        for field in text_fields:
            if field in body:
                item[field] = body[field]
        
        # Convertir rango_base_precios
        if 'rango_base_precios' in body and isinstance(body['rango_base_precios'], list):
            rangos_decimal = []
            for rango in body['rango_base_precios']:
                rangos_decimal.append({
                    'min_kg': Decimal(str(rango.get('min_kg', 0))),
                    'max_kg': Decimal(str(rango.get('max_kg', 0))),
                    'costo': Decimal(str(rango.get('costo', 0))),
                    'concepto': rango.get('concepto', '')
                })
            item['rango_base_precios'] = rangos_decimal
        
        # Guardar en DynamoDB
        table.put_item(Item=item)
        
        return {
            "statusCode": 201,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "message": "Tarifa created successfully",
                "id": item_id,
                "item": item
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
