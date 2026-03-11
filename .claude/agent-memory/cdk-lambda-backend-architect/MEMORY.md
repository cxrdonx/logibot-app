# LogiBotIA Backend Architect Memory

## Key File Paths
- CDK stack: `Backend/ia_project/ia_project_stack.py`
- CDK app entry: `Backend/app.py`
- Tarifas CRUD: `Backend/lambda/tarifas_crud/` (create, read, update, delete, index)
- Maritime CRUD: `Backend/lambda/maritime_crud/` (create, read, update, delete)
- Chatbot directory: `Backend/lambda/chatbot/`
  - `chatbot_terrestre.py` — terrestre handler (DO NOT modify)
  - `chatbot_maritimo.py` — maritime ALCE V2 handler
  - `index.py` — router: reads CHATBOT_TYPE env var, imports correct handler
  - `Dockerfile` — CMD is `index.handler`; copies both chatbot modules + index.py

## DynamoDB Tables
- `TarifasLogistica`: PK=id, GSIs: OrigenIndex, DestinoIndex, ProveedorIndex, RutaIndex(origen+destino SK)
- `MaritimeQuotations`: PK=id, GSIs: OriginPortIndex, DestinationPortIndex, ShippingLineIndex, QuotationNumberIndex
  - GSI projection fields (denormalized at top level): origin_port, destination_port, shipping_line, quotation_number

## API Gateway Routes
- `/tarifas` GET/POST, `/tarifas/{id}` GET/PUT/DELETE → TarifasLogistica handlers
- `/chatbot` POST → ChatbotTerrestreHandler (CHATBOT_TYPE=terrestre)
- `/maritime-quotations` GET/POST, `/maritime-quotations/{id}` GET/PUT/DELETE → MaritimeQuotations handlers
- `/chatbot-maritimo` POST → ChatbotMaritimoHandler (CHATBOT_TYPE=maritimo)

## Lambda Env Var Patterns
- Tarifas CRUD: TABLE_NAME
- Maritime CRUD: TABLE_NAME (points to maritime table)
- Chatbot terrestre: TABLE_NAME, REGION, MODEL_ID, CHATBOT_TYPE=terrestre
- Chatbot maritimo: MARITIME_TABLE_NAME, REGION, MODEL_ID, CHATBOT_TYPE=maritimo

## CDK Patterns
- CRUD Lambdas: `_lambda.Function` with `runtime=PYTHON_3_9`, `Code.from_asset("lambda/<folder>")`
- Docker chatbots: `_lambda.DockerImageFunction` with `DockerImageCode.from_image_asset("lambda/chatbot")`
- IAM grants: `grant_write_data` for create, `grant_read_data` for read, `grant_read_write_data` for update/delete
- Bedrock: `add_to_role_policy(iam.PolicyStatement(actions=["bedrock:InvokeModel"], resources=["*"]))`

## Docker Routing Pattern
- Single Docker image for all chatbots (lambda/chatbot Dockerfile)
- `index.py` reads `CHATBOT_TYPE` env var → imports and exposes the correct `handler`
- CDK sets `CHATBOT_TYPE` per DockerImageFunction definition

## Maritime CRUD Key Design
- `create.py`: UUID generation, validates required fields + business rules (dates, prices)
- GSI fields denormalized at item root level (origin_port, destination_port, shipping_line, quotation_number)
  so DynamoDB GSI queries work directly without nested attribute access
- `routing.via_port` = optional transshipment port
- All numeric fields use `Decimal(str(value))` for DynamoDB storage

## ALCE V2 Chatbot Design
- Same 3-step pipeline as terrestre: classify → query → respond
- Validates quotations via `validar_cotizacion()`: dates, line_item math, total, transit time
- `calcular_total_cotizacion()` computes Total = Σ(Qi × Pi) — programmatic, not AI
- Alerts returned as `alertas` array in response JSON alongside `respuesta`
- Never forces currency conversion; respects declared `currency` field
- Transshipment detection via `routing.via_port`

## Bedrock Model
- Model ID: `amazon.nova-pro-v1:0`
- Request format: `{ system: [{text}], messages: [{role, content: [{text}]}], inferenceConfig: {...} }`
- Response path: `response_body['output']['message']['content'][0]['text']`
- History: last 10 messages from `conversation_history` array sent by frontend

## CORS Headers Pattern
All Lambda responses must include:
```python
"Access-Control-Allow-Origin": "*"
"Access-Control-Allow-Headers": "*"
```

## See Also
- `Backend/ARCHITECTURE.md`, `Backend/API_DOCUMENTATION.md`, `Backend/DEPLOYMENT_GUIDE.md`
