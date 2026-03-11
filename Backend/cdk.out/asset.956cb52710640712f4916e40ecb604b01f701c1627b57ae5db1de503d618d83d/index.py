import json

def handler(event, context):
    """
    Lambda function handler to process API Gateway POST requests
    """
    print("Event received:", json.dumps(event))
    
    body = {}
    if 'body' in event and event['body']:
        try:
            # API Gateway bodies are often stringified JSON
            body = json.loads(event['body'])
        except (TypeError, json.JSONDecodeError):
            body = event['body']

    # Aquí iría tu lógica de negocio
    response_data = {
        "message": "Data received successfully",
        "input": body
    }

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(response_data)
    }
