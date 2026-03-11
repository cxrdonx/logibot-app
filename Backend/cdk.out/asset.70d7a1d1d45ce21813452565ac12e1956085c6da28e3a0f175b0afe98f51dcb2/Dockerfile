FROM public.ecr.aws/lambda/python:3.12

# Copiar archivo de dependencias e instalar
COPY requirements.txt ${LAMBDA_TASK_ROOT}
#RUN pip install -r requirements.txt

# Copiar todos los módulos de chatbot
COPY chatbot_terrestre.py ${LAMBDA_TASK_ROOT}
COPY chatbot_maritimo.py ${LAMBDA_TASK_ROOT}

# Copiar el router de entrada (selecciona módulo via CHATBOT_TYPE env var)
COPY index.py ${LAMBDA_TASK_ROOT}

# El handler de entrada siempre es index.handler
# La variable de entorno CHATBOT_TYPE determina qué módulo se usa:
#   CHATBOT_TYPE=terrestre  → chatbot_terrestre.handler
#   CHATBOT_TYPE=maritimo   → chatbot_maritimo.handler
CMD ["index.handler"]