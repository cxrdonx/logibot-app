# Mejoras al Sistema Conversacional del Chatbot Marítimo (ALCE)

## Problema Original

El chatbot marítimo tenía un sistema de clasificación binario (solo 2 tipos de intención)
y no podía filtrar resultados con criterios numéricos ni generar cotizaciones a medida.

---

## Arquitectura del Pipeline (antes vs. después)

### Antes
```
paso_0: clasificar → "cotizacion" | "conversacional"
paso_1: generar query DynamoDB
paso_2: ejecutar query
paso_3: formatear respuesta (XML si 1 resultado, Markdown si varios)
```

### Después
```
paso_0: clasificar + extraer filtros → 4 tipos de intención + filtros numéricos
paso_1: generar query DynamoDB (usa filtros del paso_0 como contexto)
paso_2: ejecutar query DynamoDB
        → aplicar_filtros_cuantitativos (Python-side)
        → encontrar_mejor_coincidencia (solo para generacion_cotizacion)
        → _enriquecer_datos_con_requisitos (merge usuario + DB)
paso_3: respuesta diferenciada según tipo de intención
```

---

## 1. Clasificación de Intención (4 tipos)

### Tipos de intención

| Tipo | `requiere_db` | Cuándo se activa |
|---|---|---|
| `conversacional` | false | Preguntas de seguimiento sobre datos ya mostrados, saludos, cálculos sobre info ya dada |
| `busqueda_simple` | true | Búsqueda por ruta/naviera sin filtros numéricos |
| `busqueda_cuantitativa` | true | Filtros numéricos (precio, tránsito, peso) o comparaciones ("más económica", "más rápida") |
| `generacion_cotizacion` | true | Usuario provee todos los datos necesarios para generar una cotización formal |

### Señales clave para cada tipo

```
busqueda_cuantitativa:
  - "flete menor a EUR 2,500"       → max_flete: 2500, moneda_filtro: "EUR"
  - "tiempo de tránsito máximo 30 días" → max_transit_days: 30
  - "peso bruto hasta 20,000 kg"    → max_peso_kg: 20000
  - "la más económica"              → ordenar_por: "precio_asc"
  - "la más rápida"                 → ordenar_por: "transito_asc"

generacion_cotizacion:
  - verbos: "genera", "cotiza", "necesito una cotización para", "quiero una cotización"
  - el usuario provee: origen + destino + naviera + tipo de contenedor
```

### Campo `ordenar_por`

| Valor | Señal en la pregunta |
|---|---|
| `"precio_asc"` | "más económica", "menor precio", "más barata" |
| `"precio_desc"` | "más cara", "mayor precio" |
| `"transito_asc"` | "más rápida", "menor tiempo de tránsito" |
| `null` | Sin preferencia de orden |

---

## 2. Extracción de Filtros en el Mismo LLM Call

Un solo `invoke_nova_pro` retorna clasificación + todos los filtros numéricos y de negocio:

```json
{
  "tipo": "busqueda_cuantitativa",
  "requiere_db": true,
  "razon": "Búsqueda con filtro de precio máximo",
  "ordenar_por": "precio_asc",
  "filtros": {
    "origin": "Rotterdam",
    "destination": "Puerto Barrios",
    "shipping_line": "CMA CGM",
    "container_type": "40HC",
    "num_containers": null,
    "max_flete": 2500.0,
    "min_flete": null,
    "moneda_filtro": "EUR",
    "max_transit_days": null,
    "max_peso_kg": null,
    "shipment_term": null,
    "movement_type": null,
    "via_port": null,
    "validity_days": null
  }
}
```

**Ventaja**: ahorra 1 LLM call vs. el enfoque de clasificar y extraer por separado.

---

## 3. Normalización de Puertos

`paso_1_generar_query` inyecta un diccionario de mapeo nombre → código UN/LOCODE en el system prompt para mejorar el match exacto contra los GSI de DynamoDB:

| Nombre común | Código normalizado |
|---|---|
| Rotterdam | `NLRTM - ROTTERDAM, NETHERLANDS` |
| Hamburgo / Hamburg | `DEHAM - HAMBURG, GERMANY` |
| Amberes / Antwerp | `BEANR - ANTWERP, BELGIUM` |
| Puerto Barrios | `GTPBR - PUERTO BARRIOS, GUATEMALA` |
| Puerto Quetzal | `GTQUE - PUERTO QUETZAL, GUATEMALA` |
| Santo Tomás de Castilla | `GTSTC - SANTO TOMAS DE CASTILLA, GUATEMALA` |
| Kingston | `JMKIN - KINGSTON, JAMAICA` |

---

## 4. Filtrado Cuantitativo en Python (`aplicar_filtros_cuantitativos`)

Después de la query DynamoDB, se aplican filtros Python-side sobre los items recuperados:

```python
def aplicar_filtros_cuantitativos(items, filtros):
    # 1. container_type → busca en commodities[].container_type (case-insensitive)
    # 2. max_flete      → total_amount <= max_flete, respetando moneda_filtro
    # 3. min_flete      → total_amount >= min_flete
    # 4. max_transit_days → logistics.transit_time_days <= max_transit_days
    # 5. max_peso_kg    → commodities[].gross_weight <= max_peso_kg
    #
    # Regla de seguridad: si un filtro devuelve lista vacía, se omite
    # (nunca se devuelve vacío por un filtro muy restrictivo)
```

**Por qué en Python y no en DynamoDB**: DynamoDB no soporta filtros de rango sobre atributos
anidados (`commodities[0].gross_weight`) ni comparaciones multi-campo. El filtrado post-query
en Python es la única opción sin índices adicionales.

---

## 5. Generación de Cotización (`generacion_cotizacion`)

### Flujo completo

```
1. DynamoDB query con origin + destination + shipping_line del filtros
2. aplicar_filtros_cuantitativos (principalmente container_type)
3. encontrar_mejor_coincidencia → scoring contra criterios del usuario
4. _enriquecer_datos_con_requisitos → merge datos DB + requisitos usuario
5. generar_xml_maritimo(enriched) → XML para tarjeta en el frontend
```

### Scoring de mejor coincidencia (`encontrar_mejor_coincidencia`)

Cuando DynamoDB retorna múltiples candidatos, se selecciona el que mejor cumple los requisitos:

| Criterio | Puntos |
|---|---|
| `container_type` coincide | +4 |
| `shipping_line` coincide | +3 |
| `shipment_term` coincide (FOB, CIF…) | +2 |
| `movement_type` coincide (Door to Port…) | +1 |

El item con mayor puntaje es seleccionado. Las diferencias se registran en `_notas_adicionales`.

### Enriquecimiento de datos (`_enriquecer_datos_con_requisitos`)

Los requisitos del usuario que no están en la tarifa de DB se inyectan antes de generar el XML:

```python
# Overrides aplicados:
enriched["movement_type"]          = filtros.get("movement_type")
enriched["shipment_term"]          = filtros.get("shipment_term")
enriched["routing"]["via_port"]    = filtros.get("via_port")  # transbordo solicitado
enriched["dates"]["valid_from"]    = today
enriched["dates"]["valid_till"]    = today + validity_days    # vigencia solicitada
# Si num_containers > 1: escala line_items con unit "PER CONTAINER"
```

---

## 6. Contexto Conversacional Mejorado (`construir_contexto_conversacion`)

Se extrae más información del historial para enriquecer el contexto del LLM:

| Extracción | Antes | Después |
|---|---|---|
| Navieras | ✅ regex navieras conocidas | ✅ igual |
| Puertos | Solo códigos 5 letras (`[A-Z]{5}`) | Nombres de puerto completos (Rotterdam, Puerto Barrios…) usando `_PORT_NORMALIZATION` |
| Contenedores | ❌ No extraía | ✅ regex `(20FT\|40HC\|45HC…)` |

Los últimos 6 mensajes se incluyen literalmente + resumen de entidades detectadas.

---

## 7. Identificación Robusta de `datos_completos`

Cuando el chatbot retorna XML de 1 cotización, el backend incluye el objeto completo de DynamoDB
en el campo `datos_completos` del JSON de respuesta, para que el frontend lo almacene al
"Aceptar Cotización".

**Problema con el enfoque naïve** (`len(items) == 1`): en `generacion_cotizacion`, DynamoDB puede
retornar N candidatos pero solo 1 es seleccionado como mejor coincidencia. `len(items) > 1`
→ `datos_completos` quedaba `null`.

**Solución**: extraer el `tarifa_id` directamente del XML generado y buscar el item por ID:

```python
if respuesta_final.strip().startswith("<respuesta>"):
    tid_match = re.search(r'<tarifa_id>([^<]+)</tarifa_id>', respuesta_final)
    if tid_match:
        tarifa_id_xml = tid_match.group(1).strip()
        matched = [d for d in datos_extraidos if d.get("id") == tarifa_id_xml]
        if matched:
            datos_completos = matched[0]
    # Fallback: si no hay tarifa_id pero solo 1 item
    if datos_completos is None and len(datos_extraidos) == 1:
        datos_completos = datos_extraidos[0]
```

---

## 8. Lógica de Respuesta por Tipo (`paso_3_generar_respuesta_maritima`)

```
generacion_cotizacion
  → filtrar por container_type
  → mejor_coincidencia (scoring)
  → enriquecer con requisitos
  → XML (notas de diferencia en <nota> del XML, no como Markdown suelto)

busqueda_cuantitativa
  → aplicar_filtros_cuantitativos
  → si vacío: mensaje explicando qué filtros no encontraron resultados
  → ordenar por precio/tránsito si se solicitó
  → 1 resultado → XML | varios → Markdown comparativo ordenado

busqueda_simple
  → sin filtros extra
  → 1 resultado → XML | varios → Markdown comparativo

conversacional
  → manejar_pregunta_conversacional (sin consulta DB)
  → responde solo con historial de conversación
```

---

## 9. Preguntas de Ejemplo Soportadas

### Búsqueda cuantitativa
```
"¿Cotizaciones de contenedor 40HC desde Rotterdam a Puerto Barrios con flete menor a EUR 2,500?"
"¿Cuál es la cotización más económica para un 20FT desde Hamburgo hacia Puerto Quetzal?"
"¿Qué cotizaciones tienen peso bruto hasta 20,000 kg en contenedor 40HC desde Rotterdam?"
"¿Hay cotizaciones con tiempo de tránsito máximo de 30 días desde Amberes hacia Puerto Barrios?"
```

### Generación de cotización
```
"¿Puedes generarme una cotización para un contenedor 40HC desde Rotterdam hasta Puerto Barrios, con CMA CGM, en términos FOB?"
"Necesito una cotización para 18,000 kg en un 20FT desde Hamburgo a Puerto Quetzal, movimiento Door to Port."
"Cotízame un 40HC desde Amberes hasta Santo Tomás de Castilla con Maersk."
"Genera una cotización Door to Port, FOB, 40HC, desde Rotterdam hacia Puerto Barrios vía Kingston, con CMA CGM, vigente por 30 días."
```

---

## Archivos Modificados

| Archivo | Cambio |
|---|---|
| `lambda/chatbot/chatbot_maritimo.py` | Reescritura completa del pipeline |
| `lambda/chatbot/chatbot_central.py` | Actualizar llamadas a nuevas firmas de función + `datos_completos` |
