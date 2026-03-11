# 🏗️ Arquitectura del Sistema CRUD de Tarifas Logísticas

## Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND LAYER                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────┐          ┌──────────────────┐                 │
│  │                  │          │                  │                 │
│  │  Web Browser     │          │   Mobile App     │                 │
│  │  (HTML/Angular)  │          │   (React/Vue)    │                 │
│  │                  │          │                  │                 │
│  └────────┬─────────┘          └────────┬─────────┘                 │
│           │                             │                           │
│           └──────────────┬──────────────┘                           │
│                          │                                          │
│                  HTTP/HTTPS Requests                                │
│                          │                                          │
└──────────────────────────┼──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY LAYER                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Amazon API Gateway (REST API)                   │   │
│  │                                                              │   │
│  │  Endpoints:                                                  │   │
│  │  • POST   /tarifas          → Create Lambda                 │   │
│  │  • GET    /tarifas          → Read Lambda                   │   │
│  │  • GET    /tarifas/{id}     → Read Lambda                   │   │
│  │  • PUT    /tarifas/{id}     → Update Lambda                 │   │
│  │  • DELETE /tarifas/{id}     → Delete Lambda                 │   │
│  │                                                              │   │
│  │  Features:                                                   │   │
│  │  ✓ CORS Enabled                                             │   │
│  │  ✓ Cognito Authorizer (Optional)                            │   │
│  │  ✓ Request Validation                                       │   │
│  │  ✓ Throttling & Rate Limiting                               │   │
│  └──────────────────────┬──────────────────────────────────────┘   │
│                         │                                           │
└─────────────────────────┼───────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      COMPUTE LAYER (Lambda)                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │   CREATE     │  │     READ     │  │   UPDATE     │              │
│  │   Lambda     │  │    Lambda    │  │   Lambda     │              │
│  │              │  │              │  │              │              │
│  │  create.py   │  │   read.py    │  │  update.py   │              │
│  │              │  │              │  │              │              │
│  │  • Validate  │  │  • Get by ID │  │  • Validate  │              │
│  │  • Convert   │  │  • List all  │  │  • Update    │              │
│  │  • Save      │  │  • Filter    │  │  • Return    │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                 │                       │
│         │                 │                 │   ┌──────────────┐   │
│         │                 │                 │   │   DELETE     │   │
│         │                 │                 │   │   Lambda     │   │
│         │                 │                 │   │              │   │
│         │                 │                 │   │  delete.py   │   │
│         │                 │                 │   │              │   │
│         │                 │                 │   │  • Verify    │   │
│         │                 │                 │   │  • Delete    │   │
│         │                 │                 │   └──────┬───────┘   │
│         │                 │                 │          │           │
│         └─────────────────┴─────────────────┴──────────┘           │
│                                   │                                 │
│                            Read/Write Operations                    │
│                                   │                                 │
└───────────────────────────────────┼─────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DATA LAYER (DynamoDB)                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │              DynamoDB Table: TarifasLogistica                  │ │
│  │                                                                │ │
│  │  Primary Key: id (String)                                     │ │
│  │                                                                │ │
│  │  Attributes:                                                   │ │
│  │  • id                    (String - UUID)                      │ │
│  │  • origen                (String)                             │ │
│  │  • destino               (String)                             │ │
│  │  • proveedor             (String)                             │ │
│  │  • fianza                (Number)                             │ │
│  │  • dias_libres           (Number)                             │ │
│  │  • estadia               (Number)                             │ │
│  │  • rango_base_precios    (List<Map>)                          │ │
│  │                                                                │ │
│  │  Global Secondary Indexes (GSI):                              │ │
│  │  ┌─────────────────────────────────────────────────────────┐ │ │
│  │  │ 1. OrigenIndex (PK: origen)                             │ │ │
│  │  │    → Fast queries by origen                             │ │ │
│  │  ├─────────────────────────────────────────────────────────┤ │ │
│  │  │ 2. DestinoIndex (PK: destino)                           │ │ │
│  │  │    → Fast queries by destino                            │ │ │
│  │  ├─────────────────────────────────────────────────────────┤ │ │
│  │  │ 3. ProveedorIndex (PK: proveedor)                       │ │ │
│  │  │    → Fast queries by proveedor                          │ │ │
│  │  ├─────────────────────────────────────────────────────────┤ │ │
│  │  │ 4. RutaIndex (PK: origen, SK: destino)                  │ │ │
│  │  │    → Fast queries by origen + destino                   │ │ │
│  │  └─────────────────────────────────────────────────────────┘ │ │
│  │                                                                │ │
│  │  Billing Mode: On-Demand (Pay per request)                    │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    AUTHENTICATION LAYER (Optional)                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                    Amazon Cognito User Pool                    │ │
│  │                                                                │ │
│  │  • User Registration                                          │ │
│  │  • User Authentication                                        │ │
│  │  • JWT Token Generation                                       │ │
│  │  • Email Verification                                         │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

## Flujo de Datos

### CREATE (Crear Tarifa)

```
Frontend
   │
   │ POST /tarifas
   │ Body: { origen, destino, proveedor, ... }
   ▼
API Gateway
   │
   │ Validates request
   │ (Optional) Checks Cognito token
   ▼
Create Lambda
   │
   │ 1. Parse JSON body
   │ 2. Validate required fields
   │ 3. Generate UUID
   │ 4. Convert numbers to Decimal
   │ 5. Call DynamoDB PutItem
   ▼
DynamoDB
   │
   │ Store item
   ▼
Response
   │
   │ 201 Created
   │ { message, id, item }
   ▼
Frontend
```

### READ (Leer Tarifas)

```
Frontend
   │
   │ GET /tarifas?origen=X&destino=Y
   ▼
API Gateway
   │
   │ Validates request
   ▼
Read Lambda
   │
   │ 1. Parse query parameters
   │ 2. Choose appropriate query method:
   │    • Scan (all items)
   │    • Query by OrigenIndex
   │    • Query by DestinoIndex
   │    • Query by ProveedorIndex
   │    • Query by RutaIndex (origen+destino)
   │ 3. Call DynamoDB Query/Scan
   ▼
DynamoDB
   │
   │ Return matching items
   ▼
Response
   │
   │ 200 OK
   │ { count, items: [...] }
   ▼
Frontend
```

### UPDATE (Actualizar Tarifa)

```
Frontend
   │
   │ PUT /tarifas/{id}
   │ Body: { fianza: 1500 }
   ▼
API Gateway
   │
   │ Validates request
   ▼
Update Lambda
   │
   │ 1. Extract ID from path
   │ 2. Parse body
   │ 3. Verify item exists (GetItem)
   │ 4. Build UpdateExpression
   │ 5. Call DynamoDB UpdateItem
   ▼
DynamoDB
   │
   │ Update item
   │ Return updated attributes
   ▼
Response
   │
   │ 200 OK
   │ { message, item }
   ▼
Frontend
```

### DELETE (Eliminar Tarifa)

```
Frontend
   │
   │ DELETE /tarifas/{id}
   ▼
API Gateway
   │
   │ Validates request
   ▼
Delete Lambda
   │
   │ 1. Extract ID from path
   │ 2. Verify item exists (GetItem)
   │ 3. Call DynamoDB DeleteItem
   ▼
DynamoDB
   │
   │ Delete item
   ▼
Response
   │
   │ 200 OK
   │ { message, id }
   ▼
Frontend
```

## Características de Seguridad

```
┌─────────────────────────────────────────────┐
│          Security Layers                     │
├─────────────────────────────────────────────┤
│                                              │
│  1. HTTPS (SSL/TLS)                         │
│     └─ Encryption in transit                │
│                                              │
│  2. IAM Roles & Policies                    │
│     └─ Least privilege access               │
│                                              │
│  3. Cognito Authentication (Optional)       │
│     └─ JWT tokens                           │
│                                              │
│  4. API Gateway Throttling                  │
│     └─ Rate limiting                        │
│                                              │
│  5. Input Validation                        │
│     └─ Lambda validates all inputs          │
│                                              │
│  6. CORS Configuration                      │
│     └─ Controlled origin access             │
│                                              │
└─────────────────────────────────────────────┘
```

## Escalabilidad

```
Component          | Auto-Scaling | Limits
-------------------|--------------|---------------------------
API Gateway        | ✓ Yes        | 10,000 requests/second
Lambda (Create)    | ✓ Yes        | 1,000 concurrent executions
Lambda (Read)      | ✓ Yes        | 1,000 concurrent executions
Lambda (Update)    | ✓ Yes        | 1,000 concurrent executions
Lambda (Delete)    | ✓ Yes        | 1,000 concurrent executions
DynamoDB           | ✓ Yes        | On-demand (unlimited)
Cognito            | ✓ Yes        | Based on pricing tier
```

## Costos Estimados (us-east-1)

```
Component          | Free Tier            | Beyond Free Tier
-------------------|----------------------|-------------------
Lambda             | 1M requests/month    | $0.20/1M requests
API Gateway        | 1M requests/month*   | $3.50/1M requests
DynamoDB           | 25 GB storage        | $0.25/GB-month
                   | 25 WCU, 25 RCU       | $1.25/million writes
Cognito            | 50,000 MAUs          | $0.0055/MAU
-------------------|----------------------|-------------------
Total (100K req)   | FREE                 | ~$2/month

* Free tier valid for 12 months
```

## Monitoreo y Logs

```
┌──────────────────────────────────────────┐
│         CloudWatch Monitoring             │
├──────────────────────────────────────────┤
│                                           │
│  Lambda Metrics:                         │
│  • Invocations                           │
│  • Duration                              │
│  • Errors                                │
│  • Throttles                             │
│                                           │
│  API Gateway Metrics:                    │
│  • Request count                         │
│  • Latency                               │
│  • 4XX/5XX errors                        │
│                                           │
│  DynamoDB Metrics:                       │
│  • Read/Write capacity                   │
│  • Throttled requests                    │
│  • System errors                         │
│                                           │
│  CloudWatch Logs:                        │
│  • /aws/lambda/CreateTarifaHandler       │
│  • /aws/lambda/ReadTarifaHandler         │
│  • /aws/lambda/UpdateTarifaHandler       │
│  • /aws/lambda/DeleteTarifaHandler       │
│                                           │
└──────────────────────────────────────────┘
```

---

**Ventajas de esta Arquitectura:**

✅ **Serverless** - Sin servidores que mantener
✅ **Escalable** - Auto-scaling automático
✅ **Altamente disponible** - Multi-AZ por defecto
✅ **Económico** - Pay per use
✅ **Seguro** - Múltiples capas de seguridad
✅ **Mantenible** - Código modular y bien documentado
