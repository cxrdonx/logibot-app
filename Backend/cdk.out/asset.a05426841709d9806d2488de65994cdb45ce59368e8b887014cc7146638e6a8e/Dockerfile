FROM public.ecr.aws/lambda/python:3.12

# Copiar archivo de dependencias e instalar
COPY requirements.txt ${LAMBDA_TASK_ROOT}
#RUN pip install -r requirements.txt

# Copiar módulos de chatbot (terrestre y marítimo)
# El handler activo se selecciona via cmd en cada DockerImageFunction del CDK stack
COPY chatbot_terrestre.py ${LAMBDA_TASK_ROOT}
COPY chatbot_maritimo.py ${LAMBDA_TASK_ROOT}

# CMD por defecto (sobreescrito por cada Lambda via ImageConfig en CDK)
CMD ["chatbot_terrestre.handler"]
