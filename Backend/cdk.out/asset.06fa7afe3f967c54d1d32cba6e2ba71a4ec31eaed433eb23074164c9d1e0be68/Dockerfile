# Usar la imagen base oficial de AWS Lambda para Python 3.9
FROM public.ecr.aws/lambda/python:3.9

# Metadata
LABEL maintainer="IA Project Team"
LABEL description="Lambda functions for Tarifas CRUD operations"

# Copiar todos los archivos de código al directorio de trabajo de Lambda
COPY create.py ${LAMBDA_TASK_ROOT}/
COPY read.py ${LAMBDA_TASK_ROOT}/
COPY update.py ${LAMBDA_TASK_ROOT}/
COPY delete.py ${LAMBDA_TASK_ROOT}/

# Si tienes un archivo de dependencias, descoméntalo:
# COPY requirements.txt ${LAMBDA_TASK_ROOT}/
# RUN pip install --no-cache-dir -r requirements.txt

# boto3 ya viene incluido en el runtime de Lambda
# No es necesario instalarlo manualmente

# El handler se especificará en el stack CDK mediante el parámetro 'cmd'
# Esto permite usar la misma imagen para múltiples funciones
CMD ["create.handler"]
