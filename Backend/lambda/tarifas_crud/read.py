import json
import os
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError


dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_NAME', 'TarifasLogistica')
table = dynamodb.Table(table_name)

CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
}

def decimal_default(obj):
    """Helper para serializar Decimal a JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def handler(event, context):
    """
    Obtener tarifas logísticas
    GET /tarifas - Lista todas las tarifas
    GET /tarifas/{id} - Obtiene una tarifa específica
    GET /tarifas?origen=X&destino=Y - Filtra por origen/destino
    GET /tarifas?proveedor=X - Filtra por proveedor
    """
    print(f"Event: {json.dumps(event)}")
    
    try:
        # Obtener parámetros de la ruta y query string
        path_parameters = event.get('pathParameters', {}) or {}
        query_parameters = event.get('queryStringParameters', {}) or {}
        
        item_id = path_parameters.get('id')
        
        # Caso 1: Obtener por ID
        if item_id:
            response = table.get_item(Key={'id': item_id})
            
            if 'Item' not in response:
                return {
                    "statusCode": 404,
                    "headers": CORS_HEADERS,
                    "body": json.dumps({"error": "Tarifa not found"})
                }
            
            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps(response['Item'], default=decimal_default)
            }
        
        # Caso 2: Filtrar por query parameters
        origen = query_parameters.get('origen')
        destino = query_parameters.get('destino')
        proveedor = query_parameters.get('proveedor')
        
        if origen and destino:
            # Usar RutaIndex (origen + destino)
            response = table.query(
                IndexName='RutaIndex',
                KeyConditionExpression='origen = :origen AND destino = :destino',
                ExpressionAttributeValues={
                    ':origen': origen,
                    ':destino': destino
                }
            )
        elif origen:
            # Usar OrigenIndex
            response = table.query(
                IndexName='OrigenIndex',
                KeyConditionExpression='origen = :origen',
                ExpressionAttributeValues={':origen': origen}
            )
        elif destino:
            # Usar DestinoIndex
            response = table.query(
                IndexName='DestinoIndex',
                KeyConditionExpression='destino = :destino',
                ExpressionAttributeValues={':destino': destino}
            )
        elif proveedor:
            # Usar ProveedorIndex
            response = table.query(
                IndexName='ProveedorIndex',
                KeyConditionExpression='proveedor = :proveedor',
                ExpressionAttributeValues={':proveedor': proveedor}
            )
        else:
            # Caso 3: Scan completo (todas las tarifas)
            response = table.scan()
        
        items = response.get('Items', [])
        
        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps({
                "count": len(items),
                "items": items
            }, default=decimal_default)
        }
        
    except ClientError as e:
        print(f"DynamoDB Error: {e.response['Error']['Message']}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": f"Database error: {e.response['Error']['Message']}"})
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps({"error": str(e)})
        }
