"""
Router de entrada para los chatbots del proyecto LogiBotIA.

Lee la variable de entorno CHATBOT_TYPE para despachar al módulo correcto:
  - "terrestre" (o no definido) → chatbot_terrestre.handler
  - "maritimo"                  → chatbot_maritimo.handler

Esto permite que la misma imagen Docker sea reutilizada por múltiples
funciones Lambda, diferenciándose únicamente por la variable de entorno
CHATBOT_TYPE definida en el CDK stack.
"""
import os

CHATBOT_TYPE = os.environ.get('CHATBOT_TYPE', 'terrestre').lower().strip()

if CHATBOT_TYPE == 'maritimo':
    from chatbot_maritimo import handler  # noqa: F401
else:
    from chatbot_terrestre import handler  # noqa: F401
