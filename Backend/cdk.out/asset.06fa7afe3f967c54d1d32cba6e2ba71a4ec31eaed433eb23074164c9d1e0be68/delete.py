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
    Eliminar una tarifa logística
    DELETE /tarifas/{id}
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
        
        # Verificar que el item existe antes de eliminarlo
        existing_item = table.get_item(Key={'id': item_id})
        if 'Item' not in existing_item:
            return {
                "statusCode": 404,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"error": "Tarifa not found"})
            }
        
        # Eliminar el item
        table.delete_item(Key={'id': item_id})
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({
                "message": "Tarifa deleted successfully",
                "id": item_id
            })
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
