# Especificación para Órdenes de Embarque Marítimas
## AI Logistics & Customs Expert (ALCE) - V2

## Introducción

Esta especificación (ALCE V2) define la estructura y los requisitos para las órdenes de cotización y embarque marítimas. El sistema debe actuar como un Forwarder/Pricing Analyst capaz de extraer, estructurar y generar cotizaciones marítimas detalladas, considerando la temporalidad de las tarifas, transbordos, y términos de facturación específicos. El modelo debe manejar la logística de envío, incluyendo trámites aduaneros, cálculos de flete y procedimientos de embarque.

## 1. Perfil del Modelo y Alcance

El modelo debe actuar como un Forwarder/Pricing Analyst capaz de:
- Extraer y estructurar cotizaciones marítimas detalladas
- Analizar la temporalidad de las tarifas
- Procesar información de transbordos
- Aplicar términos de facturación específicos
- Validar información de cotizaciones contra reglas de negocio

## 2. Estructura de Datos de Cotización (Quotation)

### A. Metadatos de la Cotización

- **quotation_number** (string, obligatorio): Identificador único de la oferta (ej. Q-000793).
- **dates** (objeto, obligatorio):
  - **quote_date** (ISO 8601, obligatorio): Fecha de emisión de la cotización.
  - **valid_from** (ISO 8601, obligatorio): Inicio de vigencia de la tarifa.
  - **valid_till** (ISO 8601, obligatorio): Fin de vigencia de la tarifa.

### B. Información de Contactos

- **prepared_by** (string, obligatorio): Emisor de la cotización (ej. Rogier van der Graaf).
- **requested_by** (string, obligatorio): Cliente que solicita la cotización.
- **company** (objeto, obligatorio):
  - **name** (string): Nombre de la empresa.
  - **contact** (string): Nombre del contacto primario.
  - **address** (string): Dirección física.
  - **tax_id** / **vat_number** (string, opcional): Identificador fiscal.

### C. Detalles del Embarque (Routing & Shipment)

- **shipment_type** (string, obligatorio): Tipo de carga (ej. CONTAINER (FCL), LCL, BREAK BULK).
- **movement_type** (string, obligatorio): Alcance del servicio (ej. DOOR TO PORT, PORT TO PORT, DOOR TO DOOR).
- **shipment_term** (string, obligatorio): Incoterm aplicable (ej. FREE ON BOARD, COST & FREIGHT).
- **routing** (objeto, obligatorio):
  - **origin_port** (string, obligatorio): Puerto de salida con código (ej. NLRTM - ROTTERDAM, NETHERLANDS).
  - **via_port** (string, opcional): Puerto de transbordo (ej. JMKIN - KINGSTON, JAMAICA).
  - **destination_port** (string, obligatorio): Puerto final (ej. GTPBR - PUERTO BARRIOS, GUATEMALA).
- **logistics** (objeto, obligatorio):
  - **shipping_line** (string, obligatorio): Naviera (ej. CMA CGM, MAERSK, MSC).
  - **transit_time_days** (number, obligatorio): Tiempo estimado de tránsito en días (ej. 32).

### D. Detalles de la Carga (Commodities)

Lista de objetos para soportar múltiples líneas de productos:
- **description** (string, obligatorio): Naturaleza de la carga (ej. GENERAL CARGO-PALLETIZED).
- **container_type** (string, obligatorio): Cantidad y tipo de equipo (ej. 1 X 40HC, 2 X 20FT).
- **gross_weight** (number, obligatorio): Peso bruto total en KG (ej. 20000).
- **volume_cbm** (number, opcional): Volumen en metros cúbicos.
- **hs_code** (string, obligatorio): Código del Sistema Armonizado para clasificación aduanera.
- **country_of_origin** (string, obligatorio): País de origen de la mercancía.

### E. Desglose Financiero (Line Items)

El motor de precios debe estructurar los cobros en una tabla detallada. Cada ítem contiene:
- **description** (string, obligatorio): Concepto del cobro (ej. OCEAN FREIGHT CHARGES 40HC, BILL OF LADING FEE).
- **quantity** (number, obligatorio): Cantidad facturable.
- **unit** (string, obligatorio): Unidad de medida (ej. PER CONTAINER, PER SHIPMENT, PER BL).
- **currency** (string, obligatorio): Moneda (ej. EUR, USD, GBP).
- **unit_price** (number, obligatorio): Precio unitario.
- **amount** (number, obligatorio): Total por línea (quantity × unit_price).
- **total_amount** (number, obligatorio): Sumatoria total de la cotización.

### F. Notas y Condiciones (Terms & Conditions)

El modelo debe ser capaz de extraer o generar cláusulas operativas:
- **hs_code_limitations** (string, opcional): Limitaciones de códigos HS (ej. incluye 1 código, EUR 15 por código extra).
- **exclusions** (array de strings, opcional): Exclusiones (ej. excluye revisión aduanal, excluye gastos en destino).
- **carrier_conditions** (array de strings, opcional): Condiciones de la naviera (ej. sujeto a espacio y disponibilidad).
- **currency_notes** (string, opcional): Riesgo cambiario (ej. el tipo de cambio puede variar al momento del embarque).
- **general_notes** (string, opcional): Notas adicionales.

## 3. Lógica de Negocio y Cálculo de Tarifas

Para procesar cotizaciones marítimas, el sistema debe aplicar la siguiente fórmula matemática formal:

$$Total = \sum_{i=1}^{n} (Q_i \times P_i) + F_{fijos}$$

Donde:
- $Q_i$ es la cantidad (Quantity) del ítem $i$ (ej. número de contenedores o embarques)
- $P_i$ es el precio unitario (Unit Price) aplicable a esa unidad
- $F_{fijos}$ son tarifas fijas por embarque (ej. Handling Fee, Bill of Lading Fee, Documentation Fee)

### Ejemplo de Aplicación:
Para una cotización con:
- 2 contenedores 40HC @ EUR 3,500 por contenedor = EUR 7,000
- 1 Bill of Lading Fee @ EUR 150 = EUR 150
- 1 Handling Fee @ EUR 200 = EUR 200

**Total = (2 × 3,500) + (1 × 150) + (1 × 200) = EUR 7,350**

## 4. Reglas de Validación

- El peso no puede ser negativo.
- El volumen debe ser positivo si se proporciona (volume_cbm > 0).
- La fecha **valid_till** debe ser posterior a **valid_from** y a **quote_date**. Si no es así, generar una alerta de validación.
- Todos los campos obligatorios deben estar presentes.
- Si existe **via_port**, la ruta es de transbordo y los tiempos de tránsito deben reflejarlo.
- El **unit_price** no puede ser negativo.
- La **quantity** debe ser mayor a 0.
- Las monedas deben ser códigos ISO válidos (EUR, USD, GBP, etc.).

## 5. Ejemplo de Cotización en JSON

```json
{
  "quotation_number": "Q-000793",
  "dates": {
    "quote_date": "2026-01-20",
    "valid_from": "2026-01-29",
    "valid_till": "2026-10-31"
  },
  "prepared_by": "Rogier van der Graaf",
  "requested_by": "Anthony HP",
  "company": {
    "name": "ALONSO FORWARDING PANAMA",
    "contact": "Anthony HP",
    "address": "Panama City, Panama",
    "vat_number": "TBD"
  },
  "shipment_type": "CONTAINER (FCL)",
  "movement_type": "PORT TO PORT",
  "shipment_term": "FREE ON BOARD",
  "routing": {
    "origin_port": "PABAO - BALBOA, PANAMA",
    "via_port": "JMKIN - KINGSTON, JAMAICA",
    "destination_port": "GTPBR - PUERTO BARRIOS, GUATEMALA"
  },
  "logistics": {
    "shipping_line": "CMA CGM",
    "transit_time_days": 5
  },
  "commodities": [
    {
      "description": "GENERAL CARGO - PALLETIZED",
      "container_type": "1 X 40HC",
      "gross_weight": 20000,
      "volume_cbm": 60.5,
      "hs_code": "8471.30",
      "country_of_origin": "Panama"
    }
  ],
  "line_items": [
    {
      "description": "OCEAN FREIGHT CHARGES 40HC",
      "quantity": 1,
      "unit": "PER CONTAINER",
      "currency": "EUR",
      "unit_price": 1500,
      "amount": 1500
    },
    {
      "description": "BILL OF LADING FEE",
      "quantity": 1,
      "unit": "PER SHIPMENT",
      "currency": "EUR",
      "unit_price": 75,
      "amount": 75
    },
    {
      "description": "DOCUMENTATION FEE",
      "quantity": 1,
      "unit": "PER SHIPMENT",
      "currency": "EUR",
      "unit_price": 50,
      "amount": 50
    }
  ],
  "total_amount": 1625,
  "currency": "EUR",
  "terms_and_conditions": {
    "hs_code_limitations": "Incluye 1 código HS. EUR 15 por código adicional.",
    "exclusions": [
      "Excluye revisión aduanera en destino",
      "Excluye gastos de manejo en puertos intermedios"
    ],
    "carrier_conditions": [
      "Sujeto a espacio y disponibilidad de la naviera",
      "Cambios en itinerario sin previo aviso"
    ],
    "currency_notes": "El tipo de cambio EUR/USD puede variar al momento del embarque.",
    "general_notes": "Válido para embarques durante el período especificado. Consultar disponibilidad de línea naviera."
  }
}
```

### Ejemplo de Cotización Alternativa (Operinter)

```json
{
  "quotation_number": "Q-000794",
  "dates": {
    "quote_date": "2026-01-25",
    "valid_from": "2026-02-01",
    "valid_till": "2026-11-30"
  },
  "prepared_by": "Operinter Operations Team",
  "requested_by": "Forwarding Department",
  "company": {
    "name": "OPERINTER LOGISTICS",
    "contact": "Operations Manager",
    "address": "Rotterdam, Netherlands"
  },
  "shipment_type": "CONTAINER (FCL)",
  "movement_type": "PORT TO PORT",
  "shipment_term": "FREE ON BOARD",
  "routing": {
    "origin_port": "NLRTM - ROTTERDAM, NETHERLANDS",
    "via_port": null,
    "destination_port": "GTPBR - PUERTO BARRIOS, GUATEMALA"
  },
  "logistics": {
    "shipping_line": "MAERSK",
    "transit_time_days": 28
  },
  "commodities": [
    {
      "description": "GENERAL CARGO - MACHINERY",
      "container_type": "1 X 40HC",
      "gross_weight": 22000,
      "volume_cbm": 65.0,
      "hs_code": "8471.30",
      "country_of_origin": "Netherlands"
    }
  ],
  "line_items": [
    {
      "description": "OCEAN FREIGHT CHARGES 40HC",
      "quantity": 1,
      "unit": "PER CONTAINER",
      "currency": "EUR",
      "unit_price": 3200,
      "amount": 3200
    },
    {
      "description": "BILL OF LADING FEE",
      "quantity": 1,
      "unit": "PER SHIPMENT",
      "currency": "EUR",
      "unit_price": 100,
      "amount": 100
    },
    {
      "description": "TERMINAL HANDLING CHARGE",
      "quantity": 1,
      "unit": "PER CONTAINER",
      "currency": "EUR",
      "unit_price": 150,
      "amount": 150
    }
  ],
  "total_amount": 3450,
  "currency": "EUR",
  "terms_and_conditions": {
    "hs_code_limitations": "Sin limitación de códigos HS.",
    "exclusions": [
      "Excluye gastos de origen y destino"
    ],
    "carrier_conditions": [
      "Sujeto a confirmación de naviera",
      "Espacio no garantizado"
    ],
    "currency_notes": "Cotización en EUR. Conversión a USD según tasa del día de embarque.",
    "general_notes": "Presupuesto sin compromisos hasta confirmación de carga."
  }
}
```

## 6. Instrucciones de Comportamiento para el Modelo (AI)

### A. Detección de Transbordos
Si existe un **via_port** en la sección de routing:
- El modelo debe entender que la ruta no es directa
- Los tiempos de tránsito deben reflejar los tiempos parciales (origin→via y via→destination)
- Se deben adicionar líneas de costo específicas para transbordos si aplica

### B. Validación de Fechas
El modelo debe validar las fechas de cotización:
- **valid_till** debe ser posterior a **valid_from**
- **valid_till** debe ser posterior a **quote_date**
- Si la validación falla, generar una ALERTA indicando la inconsistencia
- Ejemplo de error: "Valid From: Jan 29 2026, Valid Till: Oct 31 2025 → INCONSISTENCIA DETECTADA"

### C. Manejo de Monedas
- Si la cotización está en Euros (EUR), el modelo NO debe forzar la conversión a USD
- Debe respetar la moneda declarada en **currency**
- Incluir cláusula de riesgo cambiario en las **currency_notes**
- Permitir conversiones SOLO si se le solicita explícitamente

### D. Validación de Montos y Cantidades
- No permitir cantidades (quantity) ≤ 0
- No permitir precios unitarios (unit_price) negativos
- El **total_amount** debe ser la suma exacta de todos los **line_items**
- Si hay discrepancia, generar alerta de cálculo

### E. Extracción de Información
Al procesar documentos de cotización:
- Extraer automáticamente **prepared_by** como el nombre del contacto
- Identificar naviera desde descripción de servicios
- Calcular **transit_time_days** a partir de fechas estimadas de salida/llegada si está disponible
- Estructurar múltiples **commodities** si hay varias líneas de carga

### F. Generación de Alertas
El modelo debe generar alertas en los siguientes casos:
- Fechas inválidas (valid_till < valid_from)
- Montos de línea que no coinciden (quantity × unit_price ≠ amount)
- Total de cotización que no coincide con suma de líneas
- Códigos de puerto no reconocidos
- Monedas inválidas
- Tiempos de tránsito muy largos (>60 días) o muy cortos (<1 día)

## 7. Requisitos Funcionales

- El sistema debe permitir crear, actualizar y consultar cotizaciones y órdenes marítimas.
- Debe validar todos los datos según las reglas de negocio definidas.
- Debe calcular automáticamente montos de línea y totales según la fórmula matemática especificada.
- Integración con sistemas aduaneros para verificación automática de códigos HS.
- Generación automática de documentos como Bill of Lading, Manifiestos y Cotizaciones.
- Soporte para múltiples monedas con manejo de tasas de cambio.
- Detección y validación de irregularidades en fechas y montos.
- Extraer y estructurar cotizaciones desde documentos no estructurados.

## 8. Requisitos No Funcionales

- **Seguridad**: Encriptación de datos sensibles (especialmente información de contacto y datos financieros).
- **Rendimiento**: Manejo de hasta 1000 cotizaciones/órdenes por día con cálculos en tiempo real.
- **Escalabilidad**: Soporte para múltiples puertos, navieras, y rutas de transbordo.
- **Precisión**: Cálculos financieros exactos con dos decimales mínimo.
- **Usabilidad**: Interfaz clara para ingreso y visualización de cotizaciones.