# Guía de Despliegue de Funciones Lambda en Contenedores Docker con AWS CDK

## Índice

1. [Introducción](#introducción)
2. [Arquitectura General](#arquitectura-general)
3. [Estructura de Archivos](#estructura-de-archivos)
4. [Configuración del Dockerfile](#configuración-del-dockerfile)
5. [Estructura del Archivo Python (Handler)](#estructura-del-archivo-python-handler)
6. [Definición en AWS CDK](#definición-en-aws-cdk)
7. [Configuración de Permisos](#configuración-de-permisos)
8. [Integración con Servicios AWS](#integración-con-servicios-aws)
9. [Troubleshooting](#troubleshooting)
10. [Checklist de Despliegue](#checklist-de-despliegue)
11. [Ejemplos Completos](#ejemplos-completos)

---

## Introducción

Esta guía documenta el proceso completo para desplegar funciones AWS Lambda usando contenedores Docker con AWS CDK (Cloud Development Kit) en Python.

### Ventajas de Lambda con Docker:
- **Dependencias complejas**: Puedes incluir librerías nativas (PIL, NumPy, etc.)
- **Tamaño mayor**: Hasta 10GB vs 250MB de deployment packages tradicionales
- **Consistencia**: Mismo ambiente en desarrollo y producción
- **Flexibilidad**: Control total sobre el runtime

---

## Arquitectura General

```
┌─────────────────────────────────────────────────────────────────┐
│                        Flujo de Despliegue                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Dockerfile        2. CDK Build         3. ECR Push          │
│  ┌──────────┐        ┌──────────┐        ┌──────────┐          │
│  │  FROM    │   ──►  │  docker  │   ──►  │  Amazon  │          │
│  │  lambda  │        │  build   │        │   ECR    │          │
│  │  python  │        │          │        │          │          │
│  └──────────┘        └──────────┘        └──────────┘          │
│                                                 │                │
│                                                 ▼                │
│  4. Lambda Creation                      ┌──────────┐          │
│  ┌──────────────────────────────────────►│  Lambda  │          │
│  │  CDK deploys Lambda pointing to ECR   │ Function │          │
│  │                                       └──────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Estructura de Archivos

```
proyecto/
├── deploy/
│   ├── docker/                          # Directorio con Dockerfile y código
│   │   ├── Dockerfile                   # Definición del contenedor
│   │   ├── requirements.txt             # Dependencias Python
│   │   ├── mi_funcion.py               # Handler de Lambda
│   │   ├── otra_funcion.py             # Otro handler
│   │   └── utils/                       # Módulos compartidos
│   │       └── helpers.py
│   │
│   ├── constructs/                      # Constructos CDK
│   │   ├── __init__.py
│   │   └── lambdas_and_s3.py           # Definición de Lambdas
│   │
│   ├── app.py                           # Punto de entrada CDK
│   ├── cdk.json                         # Configuración CDK
│   └── requirements.txt                 # Dependencias CDK
│
└── docs/
    └── LAMBDA_DOCKER_DEPLOYMENT_GUIDE.md
```

---

## Configuración del Dockerfile

### Dockerfile Básico

```dockerfile
# filepath: deploy/docker/Dockerfile

# ============================================================
# IMAGEN BASE DE AWS LAMBDA
# ============================================================
# IMPORTANTE: Usar siempre imágenes oficiales de AWS Lambda
# Versiones disponibles: 3.8, 3.9, 3.10, 3.11, 3.12
FROM public.ecr.aws/lambda/python:3.11

# ============================================================
# INSTALACIÓN DE DEPENDENCIAS DEL SISTEMA (OPCIONAL)
# ============================================================
# Solo si necesitas librerías nativas
RUN yum install -y \
    gcc \
    gcc-c++ \
    libffi-devel \
    && yum clean all

# ============================================================
# INSTALACIÓN DE DEPENDENCIAS PYTHON
# ============================================================
# LAMBDA_TASK_ROOT es una variable predefinida que apunta a /var/task
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt

# ============================================================
# COPIAR CÓDIGO FUENTE
# ============================================================
# Copiar TODOS los archivos Python necesarios
COPY *.py ${LAMBDA_TASK_ROOT}/

# Si tienes subdirectorios con módulos:
# COPY utils/ ${LAMBDA_TASK_ROOT}/utils/

# ============================================================
# CMD (OPCIONAL)
# ============================================================
# El CMD se especifica en CDK, pero puedes poner un default
# Formato: ["nombre_archivo.nombre_funcion"]
# CMD ["mi_funcion.lambda_handler"]
```

### Dockerfile Avanzado (con dependencias complejas)

```dockerfile
# filepath: deploy/docker/Dockerfile

FROM public.ecr.aws/lambda/python:3.11

# Dependencias para procesamiento de imágenes
RUN yum install -y \
    gcc \
    gcc-c++ \
    libffi-devel \
    libjpeg-devel \
    zlib-devel \
    libpng-devel \
    && yum clean all

# Variables de entorno para optimización
ENV NUMBA_CACHE_DIR=/tmp
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1

# Instalar dependencias Python
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY *.py ${LAMBDA_TASK_ROOT}/
COPY utils/ ${LAMBDA_TASK_ROOT}/utils/

# Pre-descargar modelos de ML (si aplica)
# RUN python -c "from rembg import new_session; new_session('u2net')"
```

### requirements.txt de Ejemplo

```txt
# filepath: deploy/docker/requirements.txt

# AWS SDK
boto3>=1.28.0

# Procesamiento de imágenes
Pillow>=10.0.0
rembg>=2.0.50

# Utilidades
requests>=2.31.0
python-dateutil>=2.8.2

# Base de datos
pymysql>=1.1.0
```

---

## Estructura del Archivo Python (Handler)

### Handler Básico

```python
# filepath: deploy/docker/mi_funcion.py

import json
import boto3
from datetime import datetime

# Inicializar clientes AWS fuera del handler (reutilización)
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')


def lambda_handler(event, context):
    """
    Punto de entrada de la función Lambda.
    
    Args:
        event (dict): Datos del evento que disparó la Lambda
            - Para API Gateway: contiene httpMethod, body, pathParameters, etc.
            - Para SQS: contiene Records con mensajes
            - Para S3: contiene Records con eventos de bucket
        
        context (LambdaContext): Información del contexto de ejecución
            - context.function_name: Nombre de la función
            - context.memory_limit_in_mb: Memoria asignada
            - context.aws_request_id: ID único de la invocación
            - context.get_remaining_time_in_millis(): Tiempo restante
    
    Returns:
        dict: Respuesta de la Lambda
            - Para API Gateway: debe incluir statusCode y body
            - Para invocación directa: puede retornar cualquier dict
    """
    try:
        print(f"Event received: {json.dumps(event)}")
        print(f"Request ID: {context.aws_request_id}")
        
        # Tu lógica aquí
        result = process_request(event)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'data': result,
                'requestId': context.aws_request_id
            })
        }
        
    except ValueError as e:
        # Errores de validación (4xx)
        return {
            'statusCode': 400,
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
        
    except Exception as e:
        # Errores internos (5xx)
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': 'Internal server error'
            })
        }


def process_request(event):
    """Lógica de negocio separada del handler."""
    # Implementar lógica aquí
    return {'processed': True}
```

### Handler para SQS

```python
# filepath: deploy/docker/sqs_worker.py

import json
import boto3


def lambda_handler(event, context):
    """
    Handler para procesar mensajes de SQS.
    
    El evento contiene 'Records' con los mensajes de la cola.
    """
    results = []
    
    for record in event.get('Records', []):
        try:
            # El body del mensaje viene como string JSON
            message_body = json.loads(record['body'])
            message_id = record['messageId']
            
            print(f"Processing message: {message_id}")
            
            # Procesar el mensaje
            result = process_message(message_body)
            results.append({
                'messageId': message_id,
                'success': True,
                'result': result
            })
            
        except Exception as e:
            print(f"Error processing message {record.get('messageId')}: {e}")
            results.append({
                'messageId': record.get('messageId'),
                'success': False,
                'error': str(e)
            })
            # Re-lanzar para que SQS reintente (si está configurado)
            raise
    
    return {
        'processed': len(results),
        'results': results
    }


def process_message(message):
    """Procesa un mensaje individual de SQS."""
    # Implementar lógica aquí
    return {'status': 'completed'}
```

---

## Definición en AWS CDK

### Construct Básico de Lambda

```python
# filepath: deploy/constructs/lambdas.py

from constructs import Construct
from aws_cdk import (
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_sqs as sqs,
    aws_lambda_event_sources as lambda_event_sources,
    Duration,
)
from aws_cdk.aws_ecr_assets import Platform


class LambdaConstruct(Construct):
    """Construct que agrupa todas las funciones Lambda."""
    
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        # Parámetros opcionales para integración con otros recursos
        bucket: s3.Bucket = None,
        table: dynamodb.Table = None,
        queue: sqs.Queue = None,
    ) -> None:
        super().__init__(scope, construct_id)
        
        # ============================================================
        # LAMBDA BÁSICA
        # ============================================================
        self.mi_funcion = lambda_.DockerImageFunction(
            self,
            "MiFuncion-function",              # ID del constructo (único en el stack)
            function_name="MiFuncion",          # Nombre en AWS
            description="Descripción de la función",
            
            # Configuración de recursos
            memory_size=512,                    # MB (128 - 10240)
            timeout=Duration.seconds(30),       # Máximo 15 minutos
            
            # Código desde Docker
            code=lambda_.DockerImageCode.from_image_asset(
                "./docker",                     # Ruta al directorio con Dockerfile
                platform=Platform.LINUX_AMD64,  # IMPORTANTE para Mac M1/M2
                cmd=["mi_funcion.lambda_handler"]  # archivo.funcion
            ),
            
            # Variables de entorno
            environment={
                "BUCKET_NAME": bucket.bucket_name if bucket else "",
                "TABLE_NAME": table.table_name if table else "",
                "PYTHONUNBUFFERED": "1",  # Logs en tiempo real
            }
        )
        
        # ============================================================
        # LAMBDA CON VPC (para RDS, ElastiCache, etc.)
        # ============================================================
        self.funcion_vpc = lambda_.DockerImageFunction(
            self,
            "FuncionVPC-function",
            function_name="FuncionVPC",
            description="Lambda con acceso a VPC",
            memory_size=512,
            timeout=Duration.seconds(30),
            
            # Configuración de VPC
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnets=[private_subnet]
            ),
            allow_public_subnet=True,  # Solo si usas subnets públicas
            
            code=lambda_.DockerImageCode.from_image_asset(
                "./docker",
                platform=Platform.LINUX_AMD64,
                cmd=["funcion_vpc.lambda_handler"]
            ),
            
            environment={
                "DB_HOST": "mi-rds.xxx.us-east-1.rds.amazonaws.com",
                "DB_USER": "admin",
                "DB_NAME": "mi_base_datos",
                "DB_PORT": "3306",
            }
        )
        
        # ============================================================
        # LAMBDA WORKER (procesamiento pesado)
        # ============================================================
        self.worker_function = lambda_.DockerImageFunction(
            self,
            "Worker-function",
            function_name="Worker",
            description="Lambda worker para procesamiento pesado",
            
            # Recursos máximos para procesamiento
            memory_size=3008,                   # Casi máximo
            timeout=Duration.minutes(5),        # 5 minutos
            
            code=lambda_.DockerImageCode.from_image_asset(
                "./docker",
                platform=Platform.LINUX_AMD64,
                cmd=["worker.lambda_handler"]
            ),
            
            environment={
                "OUTPUT_BUCKET": bucket.bucket_name if bucket else "",
                # Variables para optimizar procesamiento
                "NUMBA_CACHE_DIR": "/tmp",
                "OMP_NUM_THREADS": "1",
                "HOME": "/tmp",
            }
        )
        
        # Conectar SQS como trigger
        if queue:
            self.worker_function.add_event_source(
                lambda_event_sources.SqsEventSource(
                    queue,
                    batch_size=1,  # Procesar de a uno
                    max_batching_window=Duration.seconds(5)
                )
            )
```

### Configuración del CMD - Referencia Rápida

```python
# El CMD es CRÍTICO - debe coincidir exactamente con el archivo y función

# Formato: ["nombre_archivo_sin_extension.nombre_funcion"]

# Ejemplos:
cmd=["mi_funcion.lambda_handler"]           # mi_funcion.py → def lambda_handler()
cmd=["image_worker.lambda_handler"]         # image_worker.py → def lambda_handler()
cmd=["utils.helpers.process"]               # utils/helpers.py → def process()
cmd=["catalogs.crud.lambda_handler"]        # catalogs.crud.py → def lambda_handler()

# ❌ ERRORES COMUNES:
cmd=["mi_funcion.py.lambda_handler"]        # No incluir .py
cmd=["MiFuncion.lambda_handler"]            # Case sensitive
cmd=["mi_funcion.handler"]                  # Nombre de función incorrecto
```

---

## Configuración de Permisos

### Permisos para S3

```python
# Permisos usando grant methods (recomendado)
bucket.grant_read(self.mi_funcion)
bucket.grant_write(self.mi_funcion)
bucket.grant_read_write(self.mi_funcion)

# Permisos usando políticas explícitas
s3_policy = iam.PolicyStatement(
    effect=iam.Effect.ALLOW,
    actions=[
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket",
        "s3:PutObjectAcl",
    ],
    resources=[
        bucket.bucket_arn,
        f"{bucket.bucket_arn}/*"
    ]
)
self.mi_funcion.add_to_role_policy(s3_policy)
```

### Permisos para DynamoDB

```python
# Permisos usando grant methods
table.grant_read_data(self.mi_funcion)
table.grant_write_data(self.mi_funcion)
table.grant_read_write_data(self.mi_funcion)

# Permisos específicos
dynamodb_policy = iam.PolicyStatement(
    effect=iam.Effect.ALLOW,
    actions=[
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan",
    ],
    resources=[
        table.table_arn,
        f"{table.table_arn}/index/*"  # Para GSIs
    ]
)
self.mi_funcion.add_to_role_policy(dynamodb_policy)
```

### Permisos para SQS

```python
# Permisos usando grant methods
queue.grant_send_messages(self.coordinador_function)
queue.grant_consume_messages(self.worker_function)

# El consume ya incluye:
# - sqs:ReceiveMessage
# - sqs:DeleteMessage
# - sqs:GetQueueAttributes
```

### Permisos para SSM Parameter Store

```python
# Leer parámetros SSM
ssm_param.grant_read(self.mi_funcion)

# En el código Python:
import boto3
ssm = boto3.client('ssm')
response = ssm.get_parameter(
    Name='/mi-app/api-key',
    WithDecryption=True
)
api_key = response['Parameter']['Value']
```

### Permisos para Cognito

```python
cognito_policy = iam.PolicyStatement(
    effect=iam.Effect.ALLOW,
    actions=[
        "cognito-idp:GetUser",
        "cognito-idp:AdminGetUser",
        "cognito-idp:ListUsers",
    ],
    resources=[user_pool.user_pool_arn]
)
self.mi_funcion.add_to_role_policy(cognito_policy)
```

---

## Integración con Servicios AWS

### Integración con API Gateway

```python
# En el stack principal o construct de API
from aws_cdk import aws_apigateway as apigw

api = apigw.RestApi(
    self, "MiApi",
    rest_api_name="Mi API"
)

# Integrar Lambda
integration = apigw.LambdaIntegration(
    lambda_construct.mi_funcion,
    proxy=True
)

# Agregar recurso y método
resource = api.root.add_resource("items")
resource.add_method("GET", integration)
resource.add_method("POST", integration)
```

### Integración con EventBridge (Scheduled)

```python
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets

# Ejecutar cada hora
rule = events.Rule(
    self, "ScheduleRule",
    schedule=events.Schedule.rate(Duration.hours(1))
)

rule.add_target(targets.LambdaFunction(self.mi_funcion))
```

### Integración con S3 Events

```python
from aws_cdk import aws_s3_notifications as s3n

bucket.add_event_notification(
    s3.EventType.OBJECT_CREATED,
    s3n.LambdaDestination(self.mi_funcion),
    s3.NotificationKeyFilter(prefix="uploads/")
)
```

---

## Troubleshooting

### Error: `Runtime.InvalidEntrypoint`

**Causa**: El CMD especificado no coincide con el archivo o función.

```python
# ❌ INCORRECTO
cmd=["mi_funcion.py.lambda_handler"]  # No incluir .py
cmd=["MiFuncion.lambda_handler"]      # Case sensitive (archivo es mi_funcion.py)
cmd=["mi_funcion.handler"]            # Función se llama lambda_handler

# ✅ CORRECTO
cmd=["mi_funcion.lambda_handler"]
```

**Verificación**:
```bash
# Verificar que el archivo existe
ls deploy/docker/mi_funcion.py

# Verificar que la función existe
grep "def lambda_handler" deploy/docker/mi_funcion.py

# Verificar sintaxis Python
python3 -m py_compile deploy/docker/mi_funcion.py
```

### Error: `Unable to import module`

**Causa**: El archivo no fue copiado al contenedor o hay error de sintaxis.

```dockerfile
# Verificar en Dockerfile
COPY *.py ${LAMBDA_TASK_ROOT}/  # ¿Incluye tu archivo?
```

**Verificación local**:
```bash
# Build local
cd deploy/docker
docker build -t test-lambda .

# Verificar archivos en contenedor
docker run --rm test-lambda ls -la /var/task/

# Verificar import
docker run --rm test-lambda python -c "import mi_funcion; print('OK')"
```

### Error: `Task timed out`

**Causa**: La función tarda más que el timeout configurado.

```python
# Aumentar timeout (máximo 15 minutos)
timeout=Duration.minutes(5)

# O aumentar memoria (más memoria = más CPU)
memory_size=3008
```

### Error: `Memory size exceeded`

**Causa**: La función consume más memoria que la asignada.

```python
# Aumentar memoria (máximo 10240 MB)
memory_size=1024  # o más según necesidad
```

### Error: Dependencia no encontrada

**Causa**: La dependencia no está en requirements.txt o falla al instalar.

```txt
# En requirements.txt
Pillow>=10.0.0
numpy>=1.24.0
```

```dockerfile
# Si necesita compilación, agregar dependencias de sistema
RUN yum install -y gcc gcc-c++ libffi-devel
```

---

## Checklist de Despliegue

### Nueva Función Lambda

- [ ] **Archivo Python**
  - [ ] Crear `deploy/docker/nombre_funcion.py`
  - [ ] Implementar `def lambda_handler(event, context):`
  - [ ] Verificar sintaxis: `python3 -m py_compile nombre_funcion.py`

- [ ] **Dockerfile**
  - [ ] Verificar `COPY *.py ${LAMBDA_TASK_ROOT}/`
  - [ ] Agregar dependencias a `requirements.txt`

- [ ] **CDK (lambdas_and_s3.py)**
  - [ ] Agregar definición de `DockerImageFunction`
  - [ ] Especificar `cmd=["nombre_funcion.lambda_handler"]`
  - [ ] Configurar `memory_size` y `timeout`
  - [ ] Agregar variables de entorno
  - [ ] Configurar permisos (S3, DynamoDB, SQS, etc.)
  - [ ] Si usa VPC: configurar `vpc` y `vpc_subnets`

- [ ] **Despliegue**
  - [ ] `cd deploy`
  - [ ] `cdk synth` (verificar sin errores)
  - [ ] `cdk deploy`
  - [ ] Verificar en AWS Console

### Verificación Post-Despliegue

- [ ] Lambda aparece en AWS Console
- [ ] Probar con evento de prueba
- [ ] Verificar logs en CloudWatch
- [ ] Verificar permisos (intentar acceder a S3, DynamoDB, etc.)

---

## Ejemplos Completos

### Ejemplo 1: Lambda CRUD Simple

```python
# filepath: deploy/docker/items_crud.py

import json
import boto3
import os
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TABLE_NAME', 'items'))


def lambda_handler(event, context):
    """CRUD de items."""
    http_method = event.get('httpMethod', 'GET')
    
    handlers = {
        'GET': handle_get,
        'POST': handle_post,
        'PUT': handle_put,
        'DELETE': handle_delete,
    }
    
    handler = handlers.get(http_method)
    if not handler:
        return response(405, {'error': 'Method not allowed'})
    
    return handler(event)


def handle_get(event):
    """Obtener items."""
    item_id = event.get('pathParameters', {}).get('id')
    
    if item_id:
        result = table.get_item(Key={'id': item_id})
        item = result.get('Item')
        if not item:
            return response(404, {'error': 'Item not found'})
        return response(200, item)
    
    result = table.scan()
    return response(200, result.get('Items', []))


def handle_post(event):
    """Crear item."""
    body = json.loads(event.get('body', '{}'))
    body['created_at'] = datetime.utcnow().isoformat()
    
    table.put_item(Item=body)
    return response(201, body)


def handle_put(event):
    """Actualizar item."""
    item_id = event.get('pathParameters', {}).get('id')
    body = json.loads(event.get('body', '{}'))
    body['id'] = item_id
    body['updated_at'] = datetime.utcnow().isoformat()
    
    table.put_item(Item=body)
    return response(200, body)


def handle_delete(event):
    """Eliminar item."""
    item_id = event.get('pathParameters', {}).get('id')
    table.delete_item(Key={'id': item_id})
    return response(204, None)


def response(status_code, body):
    """Construir respuesta HTTP."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(body) if body else ''
    }
```

```python
# En CDK
self.items_crud_function = lambda_.DockerImageFunction(
    self,
    "ItemsCRUD-function",
    function_name="ItemsCRUD",
    description="CRUD de items",
    memory_size=256,
    timeout=Duration.seconds(10),
    code=lambda_.DockerImageCode.from_image_asset(
        "./docker",
        platform=Platform.LINUX_AMD64,
        cmd=["items_crud.lambda_handler"]
    ),
    environment={
        "TABLE_NAME": items_table.table_name
    }
)

items_table.grant_read_write_data(self.items_crud_function)
```

### Ejemplo 2: Worker de Procesamiento con SQS

```python
# filepath: deploy/docker/image_processor.py

import json
import boto3
import os
from PIL import Image
import io

s3 = boto3.client('s3')
BUCKET = os.environ.get('OUTPUT_BUCKET')


def lambda_handler(event, context):
    """Procesar imágenes desde SQS."""
    for record in event.get('Records', []):
        message = json.loads(record['body'])
        process_image(message)
    
    return {'processed': len(event.get('Records', []))}


def process_image(message):
    """Procesar una imagen individual."""
    input_key = message['input_key']
    output_key = message['output_key']
    width = message.get('width', 800)
    height = message.get('height', 600)
    
    # Descargar imagen
    response = s3.get_object(Bucket=BUCKET, Key=input_key)
    image_data = response['Body'].read()
    
    # Procesar con PIL
    image = Image.open(io.BytesIO(image_data))
    image = image.resize((width, height), Image.LANCZOS)
    
    # Guardar
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG', quality=85)
    buffer.seek(0)
    
    s3.put_object(
        Bucket=BUCKET,
        Key=output_key,
        Body=buffer.getvalue(),
        ContentType='image/jpeg'
    )
    
    print(f"Processed: {input_key} -> {output_key}")
```

```python
# En CDK
self.image_processor = lambda_.DockerImageFunction(
    self,
    "ImageProcessor-function",
    function_name="ImageProcessor",
    description="Procesador de imágenes desde SQS",
    memory_size=1024,
    timeout=Duration.minutes(2),
    code=lambda_.DockerImageCode.from_image_asset(
        "./docker",
        platform=Platform.LINUX_AMD64,
        cmd=["image_processor.lambda_handler"]
    ),
    environment={
        "OUTPUT_BUCKET": bucket.bucket_name
    }
)

# Trigger desde SQS
self.image_processor.add_event_source(
    lambda_event_sources.SqsEventSource(
        processing_queue,
        batch_size=1
    )
)

bucket.grant_read_write(self.image_processor)
processing_queue.grant_consume_messages(self.image_processor)
```

---

## Referencias

- [AWS Lambda Container Images](https://docs.aws.amazon.com/lambda/latest/dg/images-create.html)
- [AWS CDK Python Reference](https://docs.aws.amazon.com/cdk/api/v2/python/)
- [Docker Image Function Construct](https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_lambda/DockerImageFunction.html)
- [Lambda Base Images (ECR)](https://gallery.ecr.aws/lambda/python)

---

*Última actualización: Marzo 2026*