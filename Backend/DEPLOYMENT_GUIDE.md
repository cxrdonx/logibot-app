# 🚀 Despliegue del API CRUD de Tarifas Logísticas

## 📋 Descripción

Este sistema proporciona un API REST completo para gestionar tarifas logísticas en DynamoDB mediante AWS Lambda y API Gateway.

## 🏗️ Arquitectura

```
Frontend (HTML) 
    ↓ HTTP Requests
API Gateway
    ↓ Invoke
Lambda Functions (CRUD)
    ↓ Read/Write
DynamoDB (TarifasLogistica)
```

### Componentes:

- **4 Lambda Functions** (Create, Read, Update, Delete)
- **1 API Gateway** con endpoints REST
- **1 Tabla DynamoDB** con 4 índices globales secundarios
- **Cognito User Pool** (opcional, para autenticación)

## 📁 Estructura de Archivos

```
lambda/tarifas_crud/
├── create.py       # POST /tarifas
├── read.py         # GET /tarifas, GET /tarifas/{id}
├── update.py       # PUT /tarifas/{id}
└── delete.py       # DELETE /tarifas/{id}

frontend_example.html   # Interfaz web para pruebas
test_api.py            # Script de pruebas automáticas
API_DOCUMENTATION.md   # Documentación completa del API
```

## 🚀 Pasos de Despliegue

### 1. Prerequisitos

```bash
# Instalar AWS CDK
npm install -g aws-cdk

# Configurar credenciales de AWS
aws configure

# Instalar dependencias de Python
pip install -r requirements.txt
```

### 2. Verificar el Stack

```bash
# Ver los cambios que se aplicarán
cdk diff
```

### 3. Desplegar

```bash
# Primera vez (bootstrap)
cdk bootstrap

# Desplegar el stack
cdk deploy
```

**Salida esperada:**
```
✅  IaProjectStack

Outputs:
IaProjectStack.IaProjectApiEndpoint = https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/
```

### 4. Guardar la URL del API

Copia la URL del output y guárdala para usar en el frontend.

## 🧪 Pruebas

### Opción 1: Script de Pruebas Automáticas

```bash
# Ejecutar todas las pruebas CRUD
python test_api.py https://YOUR-API-URL.execute-api.us-east-1.amazonaws.com/prod

# Salida esperada:
# ✓ PASS - CREATE
# ✓ PASS - READ_ALL
# ✓ PASS - READ_BY_ID
# ✓ PASS - READ_FILTERED
# ✓ PASS - UPDATE
# ✓ PASS - DELETE
```

### Opción 2: Frontend HTML

1. Abre `frontend_example.html` en tu navegador
2. Pega la URL del API en el campo de configuración
3. Usa la interfaz para crear, leer, actualizar y eliminar tarifas

### Opción 3: cURL

```bash
# Variable con la URL del API
export API_URL="https://YOUR-API-URL.execute-api.us-east-1.amazonaws.com/prod"

# Crear tarifa
curl -X POST $API_URL/tarifas \
  -H "Content-Type: application/json" \
  -d '{
    "origen": "Puerto Quetzal",
    "destino": "Mixco",
    "proveedor": "Nixon Larios",
    "fianza": 1000,
    "dias_libres": 3,
    "estadia": 500
  }'

# Listar todas las tarifas
curl -X GET $API_URL/tarifas

# Obtener tarifa específica
curl -X GET $API_URL/tarifas/{id}

# Actualizar tarifa
curl -X PUT $API_URL/tarifas/{id} \
  -H "Content-Type: application/json" \
  -d '{"fianza": 1200}'

# Eliminar tarifa
curl -X DELETE $API_URL/tarifas/{id}
```

## 📊 Endpoints del API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/tarifas` | Crear nueva tarifa |
| GET | `/tarifas` | Listar todas las tarifas |
| GET | `/tarifas?origen=X` | Filtrar por origen |
| GET | `/tarifas?destino=Y` | Filtrar por destino |
| GET | `/tarifas?proveedor=Z` | Filtrar por proveedor |
| GET | `/tarifas/{id}` | Obtener tarifa específica |
| PUT | `/tarifas/{id}` | Actualizar tarifa |
| DELETE | `/tarifas/{id}` | Eliminar tarifa |

Ver documentación completa en [`API_DOCUMENTATION.md`](./API_DOCUMENTATION.md)

## 🔐 Seguridad (Opcional)

Para habilitar autenticación con Cognito:

1. Edita `ia_project/ia_project_stack.py`
2. Descomenta las líneas de `authorizer` y `authorization_type`
3. Redespliega: `cdk deploy`
4. Crea usuarios en Cognito User Pool
5. Obtén token JWT y úsalo en el header: `Authorization: Bearer {token}`

## 📦 Cargar Datos Iniciales

Después del despliegue, carga los datos de prueba:

```bash
cd tests
python dynamo.py
```

Esto cargará las tarifas iniciales desde el archivo `tests/dynamo.py`.

## 🗑️ Eliminar el Stack

Para eliminar todos los recursos:

```bash
cdk destroy
```

**⚠️ Advertencia:** Esto eliminará la tabla DynamoDB y todos los datos.

## 🔍 Troubleshooting

### Error: "Unable to locate credentials"
```bash
aws configure
# Ingresa tus credenciales AWS
```

### Error: "Table already exists"
```bash
# Elimina la tabla existente manualmente o cambia el nombre en el stack
aws dynamodb delete-table --table-name TarifasLogistica
```

### Error: "No module named 'boto3'"
```bash
pip install boto3
```

### Ver logs de Lambda
```bash
# Obtener el nombre de la función
aws lambda list-functions --query 'Functions[?contains(FunctionName, `TarifaHandler`)].FunctionName'

# Ver logs
aws logs tail /aws/lambda/IaProjectStack-BackendReadTarifaHandler --follow
```

## 📈 Monitoreo

### CloudWatch Metrics

Accede a CloudWatch para ver:
- Invocaciones de Lambda
- Errores
- Duración de ejecución
- Throttles

### DynamoDB Metrics

- Read/Write capacity units
- Latencia
- Errores

## 🎯 Próximos Pasos

1. ✅ **Desplegar el stack** - `cdk deploy`
2. ✅ **Cargar datos iniciales** - `python tests/dynamo.py`
3. ✅ **Probar el API** - `python test_api.py <URL>`
4. ✅ **Usar el frontend** - Abrir `frontend_example.html`
5. 🔄 **Integrar con tu aplicación** - Usa los endpoints REST

## 📞 Soporte

Para más información, consulta:
- [Documentación del API](./API_DOCUMENTATION.md)
- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)

---

**¡Listo para producción! 🚀**
