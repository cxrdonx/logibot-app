
# 🚚 Sistema CRUD de Tarifas Logísticas

Sistema completo de gestión de tarifas logísticas construido con AWS CDK, Lambda, API Gateway y DynamoDB. Incluye API REST completa y frontend de ejemplo.

![AWS](https://img.shields.io/badge/AWS-Lambda%20%7C%20API%20Gateway%20%7C%20DynamoDB-orange)
![Python](https://img.shields.io/badge/Python-3.9-blue)
![CDK](https://img.shields.io/badge/AWS%20CDK-2.x-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 📋 Características

✅ **CRUD Completo** - Create, Read, Update, Delete  
✅ **API REST** - Endpoints RESTful con API Gateway  
✅ **Serverless** - 100% serverless con AWS Lambda  
✅ **Búsquedas Eficientes** - 4 índices globales secundarios  
✅ **Frontend Incluido** - Interfaz web moderna lista para usar  
✅ **Documentación Completa** - Guías, ejemplos y arquitectura  
✅ **Testing** - Scripts de pruebas automáticas  
✅ **Despliegue Fácil** - Script automatizado de despliegue  

## 🚀 Inicio Rápido

### 1. Clonar y Configurar

```bash
# Clonar el proyecto
cd "IA project"

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Desplegar

```bash
# Opción 1: Script automatizado (recomendado)
./deploy.sh

# Opción 2: Manual
cdk deploy
```

### 3. Probar

```bash
# Ejecutar pruebas automáticas
python test_api.py <API_URL>

# O abrir el frontend
open frontend_example.html
```

## 📁 Estructura del Proyecto

```
.
├── lambda/
│   └── tarifas_crud/
│       ├── create.py          # POST /tarifas
│       ├── read.py            # GET /tarifas, GET /tarifas/{id}
│       ├── update.py          # PUT /tarifas/{id}
│       └── delete.py          # DELETE /tarifas/{id}
├── ia_project/
│   └── ia_project_stack.py    # Infraestructura CDK
├── tests/
│   └── dynamo.py              # Carga de datos iniciales
├── frontend_example.html       # Interfaz web de ejemplo
├── test_api.py                # Pruebas automáticas
├── deploy.sh                  # Script de despliegue
└── Documentación/
    ├── API_DOCUMENTATION.md
    ├── DEPLOYMENT_GUIDE.md
    ├── ARCHITECTURE.md
    ├── INTEGRATION_EXAMPLES.md
    └── CRUD_SUMMARY.md
```

## 🎯 Endpoints del API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/tarifas` | Crear nueva tarifa |
| GET | `/tarifas` | Listar todas las tarifas |
| GET | `/tarifas?origen=X` | Filtrar por origen |
| GET | `/tarifas?destino=Y` | Filtrar por destino |
| GET | `/tarifas/{id}` | Obtener tarifa específica |
| PUT | `/tarifas/{id}` | Actualizar tarifa |
| DELETE | `/tarifas/{id}` | Eliminar tarifa |

## 📊 Arquitectura

```
Frontend → API Gateway → Lambda Functions → DynamoDB
                ↓
          Cognito (Auth)
```

**Componentes:**
- 4 Lambda Functions (Create, Read, Update, Delete)
- 1 API Gateway REST
- 1 Tabla DynamoDB con 4 GSIs
- 1 Cognito User Pool (opcional)

Ver más detalles en [ARCHITECTURE.md](./ARCHITECTURE.md)

## 💻 Ejemplo de Uso

### JavaScript/Fetch

```javascript
// Obtener todas las tarifas
const response = await fetch('https://API-URL/tarifas');
const data = await response.json();

// Crear nueva tarifa
await fetch('https://API-URL/tarifas', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    origen: 'Puerto Quetzal',
    destino: 'Mixco',
    proveedor: 'Nixon Larios',
    fianza: 1000
  })
});

// Actualizar tarifa
await fetch('https://API-URL/tarifas/abc-123', {
  method: 'PUT',
  body: JSON.stringify({ fianza: 1500 })
});
```

### Python

```python
import requests

# Obtener tarifas
response = requests.get('https://API-URL/tarifas')
tarifas = response.json()['items']

# Crear tarifa
requests.post('https://API-URL/tarifas', json={
    'origen': 'Puerto Quetzal',
    'destino': 'Mixco',
    'proveedor': 'Test',
    'fianza': 1000
})
```

Más ejemplos en [INTEGRATION_EXAMPLES.md](./INTEGRATION_EXAMPLES.md)

## 📖 Documentación

| Documento | Descripción |
|-----------|-------------|
| [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) | Documentación completa del API |
| [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) | Guía de despliegue paso a paso |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Arquitectura y diagramas |
| [INTEGRATION_EXAMPLES.md](./INTEGRATION_EXAMPLES.md) | Ejemplos para React, Vue, Angular, etc. |
| [CRUD_SUMMARY.md](./CRUD_SUMMARY.md) | Resumen del proyecto |

## 🧪 Testing

### Pruebas Automáticas

```bash
python test_api.py https://your-api-url.com/prod
```

**Pruebas incluidas:**
- ✅ CREATE - Crear tarifa
- ✅ READ ALL - Listar todas
- ✅ READ BY ID - Obtener por ID
- ✅ READ FILTERED - Filtrar tarifas
- ✅ UPDATE - Actualizar
- ✅ DELETE - Eliminar

### Frontend Web

1. Abre `frontend_example.html` en tu navegador
2. Configura la URL del API
3. Usa la interfaz para gestionar tarifas

## 💰 Costos Estimados

**Desarrollo (Free Tier):** $0/mes  
**Producción (100K requests/mes):** ~$2/mes

| Servicio | Free Tier | Costo Post-Free |
|----------|-----------|-----------------|
| Lambda | 1M requests/mes | $0.20/1M |
| API Gateway | 1M requests/mes (12 meses) | $3.50/1M |
| DynamoDB | 25 GB | $0.25/GB |

## 🔐 Seguridad

- ✅ HTTPS (SSL/TLS)
- ✅ IAM Roles & Policies
- ✅ Cognito Authentication (opcional)
- ✅ Input Validation
- ✅ CORS Configuration

## 📈 Escalabilidad

- **Lambda:** Auto-scaling hasta 1000 concurrentes
- **API Gateway:** 10,000 req/s por defecto
- **DynamoDB:** On-demand, escala automáticamente

## 🛠️ Comandos CDK Útiles

```bash
cdk ls          # Listar stacks
cdk synth       # Sintetizar CloudFormation
cdk deploy      # Desplegar
cdk diff        # Ver cambios
cdk destroy     # Eliminar recursos
```

## 🔍 Monitoreo

```bash
# Ver logs de Lambda
aws logs tail /aws/lambda/IaProjectStack-BackendReadTarifaHandler --follow

# Métricas en CloudWatch
# - Invocaciones
# - Errores  
# - Duración
# - Throttles
```

## 🗑️ Limpieza

Para eliminar todos los recursos:

```bash
cdk destroy
```

⚠️ **Advertencia:** Esto eliminará todos los datos de DynamoDB.

## 📞 Soporte

¿Necesitas ayuda?
- Consulta la [documentación](./API_DOCUMENTATION.md)
- Revisa los [ejemplos de integración](./INTEGRATION_EXAMPLES.md)
- Checa la [arquitectura](./ARCHITECTURE.md)

## 📝 Licencia

MIT License - Siéntete libre de usar este código en tus proyectos.

## 🎉 ¡Listo!

Tu sistema CRUD está completo y listo para desplegar. Ejecuta:

```bash
./deploy.sh
```

Y comienza a gestionar tus tarifas logísticas! 🚀

---

**Desarrollado con** ❤️ **usando AWS CDK + Lambda + DynamoDB**
