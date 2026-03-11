FROM public.ecr.aws/lambda/python:3.9

# Copiar el código de la función
COPY index.py ${LAMBDA_TASK_ROOT}/

# Instalar dependencias
RUN pip install --no-cache-dir boto3

# Comando para ejecutar la función Lambda
CMD [ "index.handler" ]
