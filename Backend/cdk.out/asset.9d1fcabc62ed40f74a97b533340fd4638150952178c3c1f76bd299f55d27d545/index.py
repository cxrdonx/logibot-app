"""
Multiplexor de handlers para funciones CRUD de tarifas.
Este archivo permite usar un solo Dockerfile para todas las operaciones CRUD.
"""
import os
import json

# Importar todos los handlers
from create import handler as create_handler
from read import handler as read_handler
from update import handler as update_handler
from delete import handler as delete_handler

# Mapeo de operaciones a handlers
HANDLERS = {
    'create': create_handler,
    'read': read_handler,
    'update': update_handler,
    'delete': delete_handler
}

def handler(event, context):
    """
    Handler principal que determina qué operación ejecutar.
    La operación se define mediante la variable de entorno OPERATION.
    """
    operation = os.environ.get('OPERATION', '').lower()
    
    if operation not in HANDLERS:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': f'Invalid operation: {operation}',
                'valid_operations': list(HANDLERS.keys())
            })
        }
    
    # Ejecutar el handler correspondiente
    return HANDLERS[operation](event, context)
