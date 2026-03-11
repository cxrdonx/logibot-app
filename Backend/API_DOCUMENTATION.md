# API REST - CRUD de Tarifas Logísticas

## Descripción
Esta API permite administrar tarifas logísticas en DynamoDB mediante operaciones CRUD (Crear, Leer, Actualizar, Eliminar).

## URL Base
Una vez desplegado, tu API estará disponible en:
```
https://{api-id}.execute-api.us-east-1.amazonaws.com/prod/
```

## Endpoints

### 1. CREATE - Crear Nueva Tarifa
**Endpoint:** `POST /tarifas`

**Body:**
```json
{
  "origen": "Puerto Quetzal",
  "destino": "Mixco",
  "proveedor": "Nixon Larios",
  "fianza": 1000,
  "dias_libres": 3,
  "estadia": 500,
  "tramite_de_aduana_cominter": 825,
  "condiciones_de_aduana_cominter": "HASTA 50 LINEAS ADICIONALES Q2.50",
  "tramite_aduana": 650,
  "condiciones_aduana": "HASTA 10 LINEAS Q0.75 ADICIONALES",
  "custodio_comsi": 450,
  "custodio_yantarni": 375,
  "rango_base_precios": [
    {
      "min_kg": 0,
      "max_kg": 20999,
      "costo": 3600,
      "concepto": "Tarifa Base"
    },
    {
      "min_kg": 21000,
      "max_kg": 25000,
      "costo": 1000,
      "concepto": "Sobrepeso Nivel 1"
    }
  ]
}
```

**Campos Requeridos:**
- `origen` (string)
- `destino` (string)
- `proveedor` (string)

**Respuesta Exitosa (201):**
```json
{
  "message": "Tarifa created successfully",
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "item": { ... }
}
```

**Ejemplo con cURL:**
```bash
curl -X POST https://YOUR-API-URL/tarifas \
  -H "Content-Type: application/json" \
  -d '{
    "origen": "Puerto Quetzal",
    "destino": "Mixco",
    "proveedor": "Nixon Larios",
    "fianza": 1000,
    "dias_libres": 3,
    "estadia": 500
  }'
```

---

### 2. READ - Leer Tarifas

#### 2.1 Listar Todas las Tarifas
**Endpoint:** `GET /tarifas`

**Respuesta (200):**
```json
{
  "count": 5,
  "items": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "origen": "Puerto Quetzal",
      "destino": "Mixco",
      "proveedor": "Nixon Larios",
      ...
    },
    ...
  ]
}
```

**Ejemplo con cURL:**
```bash
curl -X GET https://YOUR-API-URL/tarifas
```

#### 2.2 Filtrar por Origen
**Endpoint:** `GET /tarifas?origen=Puerto%20Quetzal`

**Ejemplo con cURL:**
```bash
curl -X GET "https://YOUR-API-URL/tarifas?origen=Puerto%20Quetzal"
```

#### 2.3 Filtrar por Destino
**Endpoint:** `GET /tarifas?destino=Mixco`

**Ejemplo con cURL:**
```bash
curl -X GET "https://YOUR-API-URL/tarifas?destino=Mixco"
```

#### 2.4 Filtrar por Proveedor
**Endpoint:** `GET /tarifas?proveedor=Nixon%20Larios`

**Ejemplo con cURL:**
```bash
curl -X GET "https://YOUR-API-URL/tarifas?proveedor=Nixon%20Larios"
```

#### 2.5 Filtrar por Origen y Destino
**Endpoint:** `GET /tarifas?origen=Puerto%20Quetzal&destino=Mixco`

**Ejemplo con cURL:**
```bash
curl -X GET "https://YOUR-API-URL/tarifas?origen=Puerto%20Quetzal&destino=Mixco"
```

#### 2.6 Obtener Tarifa Específica por ID
**Endpoint:** `GET /tarifas/{id}`

**Respuesta (200):**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "origen": "Puerto Quetzal",
  "destino": "Mixco",
  "proveedor": "Nixon Larios",
  ...
}
```

**Ejemplo con cURL:**
```bash
curl -X GET https://YOUR-API-URL/tarifas/123e4567-e89b-12d3-a456-426614174000
```

---

### 3. UPDATE - Actualizar Tarifa
**Endpoint:** `PUT /tarifas/{id}`

**Body (solo incluye los campos que quieres actualizar):**
```json
{
  "fianza": 1200,
  "estadia": 550,
  "rango_base_precios": [
    {
      "min_kg": 0,
      "max_kg": 20999,
      "costo": 3800,
      "concepto": "Tarifa Base Actualizada"
    }
  ]
}
```

**Respuesta Exitosa (200):**
```json
{
  "message": "Tarifa updated successfully",
  "item": {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "origen": "Puerto Quetzal",
    "destino": "Mixco",
    "proveedor": "Nixon Larios",
    "fianza": 1200,
    "estadia": 550,
    ...
  }
}
```

**Ejemplo con cURL:**
```bash
curl -X PUT https://YOUR-API-URL/tarifas/123e4567-e89b-12d3-a456-426614174000 \
  -H "Content-Type: application/json" \
  -d '{
    "fianza": 1200,
    "estadia": 550
  }'
```

---

### 4. DELETE - Eliminar Tarifa
**Endpoint:** `DELETE /tarifas/{id}`

**Respuesta Exitosa (200):**
```json
{
  "message": "Tarifa deleted successfully",
  "id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Ejemplo con cURL:**
```bash
curl -X DELETE https://YOUR-API-URL/tarifas/123e4567-e89b-12d3-a456-426614174000
```

---

## Códigos de Estado HTTP

| Código | Descripción |
|--------|-------------|
| 200    | Operación exitosa |
| 201    | Recurso creado exitosamente |
| 400    | Solicitud incorrecta (parámetros faltantes o inválidos) |
| 404    | Recurso no encontrado |
| 500    | Error interno del servidor |

---

## Errores Comunes

### Tarifa no encontrada (404)
```json
{
  "error": "Tarifa not found"
}
```

### Campos requeridos faltantes (400)
```json
{
  "error": "Missing required field: proveedor"
}
```

### Error de base de datos (500)
```json
{
  "error": "Database error: ..."
}
```

---

## Ejemplo de Flujo Completo desde Frontend

### JavaScript/Fetch
```javascript
// 1. Obtener todas las tarifas
const getTarifas = async () => {
  const response = await fetch('https://YOUR-API-URL/tarifas');
  const data = await response.json();
  return data.items;
};

// 2. Crear nueva tarifa
const createTarifa = async (nuevaTarifa) => {
  const response = await fetch('https://YOUR-API-URL/tarifas', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(nuevaTarifa)
  });
  return await response.json();
};

// 3. Actualizar costo de una tarifa
const updateTarifa = async (id, updates) => {
  const response = await fetch(`https://YOUR-API-URL/tarifas/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates)
  });
  return await response.json();
};

// 4. Eliminar tarifa
const deleteTarifa = async (id) => {
  const response = await fetch(`https://YOUR-API-URL/tarifas/${id}`, {
    method: 'DELETE'
  });
  return await response.json();
};

// Uso:
// const tarifas = await getTarifas();
// const nuevaTarifa = await createTarifa({...});
// const actualizada = await updateTarifa('id-123', { fianza: 1500 });
// await deleteTarifa('id-123');
```

---

## Despliegue

1. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

2. **Sintetizar CloudFormation:**
```bash
cdk synth
```

3. **Desplegar:**
```bash
cdk deploy
```

4. **Obtener la URL del API:**
Después del despliegue, busca en los outputs:
```
Outputs:
IaProjectStack.IaProjectApiEndpoint = https://xxxxxxxx.execute-api.us-east-1.amazonaws.com/prod/
```

---

## Seguridad

**Autenticación (Opcional):**
Las líneas de autenticación con Cognito están comentadas en el código. Para habilitarlas:
1. Descomenta las líneas de `authorizer` y `authorization_type` en `ia_project_stack.py`
2. Redespliega con `cdk deploy`
3. Usa tokens JWT de Cognito en el header `Authorization: Bearer {token}`

---

## Índices DynamoDB Disponibles

El API aprovecha los siguientes índices para búsquedas eficientes:
- **OrigenIndex**: Búsqueda por origen
- **DestinoIndex**: Búsqueda por destino
- **ProveedorIndex**: Búsqueda por proveedor
- **RutaIndex**: Búsqueda por origen + destino (compuesto)

---

## Testing

Para probar el API después del despliegue:

```bash
# Obtener URL del API
export API_URL=$(aws cloudformation describe-stacks \
  --stack-name IaProjectStack \
  --query 'Stacks[0].Outputs[?OutputKey==`IaProjectApiEndpoint`].OutputValue' \
  --output text)

# Crear una tarifa
curl -X POST $API_URL/tarifas \
  -H "Content-Type: application/json" \
  -d '{
    "origen": "Puerto Quetzal",
    "destino": "Mixco",
    "proveedor": "Test Provider",
    "fianza": 1000
  }'

# Listar todas
curl -X GET $API_URL/tarifas
```
