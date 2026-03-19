# 🤖 Lógica de Decisión del Chatbot Inteligente

## 📋 Flujo de Decisión: XML vs Comparativa

El chatbot utiliza una lógica inteligente para decidir cuándo generar una **cotización XML formal** versus una **comparativa en Markdown**.

---

## 🎯 Casos de Uso

### 1️⃣ **Generar Cotización XML** (Formato Formal)

El chatbot genera XML cuando:

#### Palabras Clave Detectadas:
- "cotización" / "cotizacion"
- "genera"
- "dame la cotización"
- "quiero cotización"
- "cotiza"
- "genera cotización"
- "cotización formal"
- "cotización de [proveedor]"
- "cotización para [proveedor]"
- "hazme cotización"
- "xml"
- "formal"

#### Ejemplos de Preguntas:
```
✅ "Dame la cotización para Edwin Suchite"
✅ "Genera la cotización de Nixon Larios"
✅ "Quiero cotización formal de Angel Paiz"
✅ "Cotiza con Nixon Larios para 26,000 kg"
✅ "Dame cotización para Puerto Quetzal a Mixco"
```

#### Comportamiento:
- **1 sola opción encontrada** → Siempre genera XML
- **Múltiples opciones + mención de "cotización"** → Genera XML (filtra por proveedor si se menciona)
- **Proveedor específico mencionado** → Selecciona ese proveedor y genera XML
- **Sin proveedor específico** → Selecciona el **más económico** automáticamente

---

### 2️⃣ **Generar Comparativa Markdown** (Múltiples Opciones)

El chatbot genera comparativa cuando:

#### Palabras Clave Detectadas:
- "mejor"
- "opciones"
- "compara"
- "recomienda"
- "cual" / "cuál"
- "más barato"
- "más económico"
- "diferencia"
- "comparativa"
- "compárame"
- "cuál es mejor"

#### Ejemplos de Preguntas:
```
✅ "¿Cuáles son las mejores opciones para Puerto Quetzal a Zona 16?"
✅ "Compara los proveedores para esta ruta"
✅ "¿Cuál es más barato?"
✅ "Recomiéndame opciones"
✅ "Diferencias entre Nixon Larios y Angel Paiz"
```

#### Comportamiento:
- **Múltiples opciones (>1)** + palabras clave de comparación → Comparativa
- **Muchas opciones (>3)** sin mención de "cotización" → Comparativa automática
- **Ordena por precio** (menor a mayor)
- **Muestra top 5** opciones máximo
- **Recomienda** la opción más económica

---

## 🔄 Flujo Conversacional Típico

### Escenario: Usuario pide comparativa y luego cotización específica

#### Paso 1: Usuario pide opciones
```
👤 Usuario: "¿Cuáles son las opciones para Puerto Quetzal a Zona 16?"
```

**Chatbot detecta:**
- Palabra clave: "opciones"
- Múltiples resultados en DB

**Respuesta:** 📊 **Comparativa Markdown**
```markdown
# 🚛 Comparativa de Opciones

Encontré **5 opciones** para tu ruta:

## 🥇 1. Edwin Suchite
**Ruta:** Puerto Quetzal → Zona 6,16,17,18
- **Tarifa base:** Q1,475.00
- **Fianza:** Q850.00
- **Días libres:** 0 días
- **Estadía:** Q500.00/día
- **💰 TOTAL:** Q2,325.00

## 🥈 2. Nixon Larios
...
```

---

#### Paso 2: Usuario solicita cotización específica
```
👤 Usuario: "Dame la cotización de Edwin Suchite"
```

**Chatbot detecta:**
- Palabra clave: "cotización"
- Proveedor mencionado: "Edwin Suchite"

**Respuesta:** 📋 **Cotización XML**
```xml
<respuesta>
    <cotizacion>
        <proveedor>Edwin Suchite</proveedor>
        <ruta>
            <origen>Puerto Quetzal</origen>
            <destino>Zona 6,16,17,18</destino>
        </ruta>
        <tarifa_base>
            <monto>1475.00</monto>
            <moneda>GTQ</moneda>
        </tarifa_base>
        ...
    </cotizacion>
</respuesta>
```

---

## 🧠 Lógica de Selección de Proveedor

Cuando se genera XML y hay múltiples opciones:

### 1. **Proveedor Mencionado Explícitamente**
```python
# Usuario dice: "Dame cotización de Nixon Larios"
proveedor_detectado = "Nixon Larios"
item_seleccionado = buscar_por_nombre(proveedor_detectado)
```

### 2. **Sin Proveedor Específico → Selección Automática**
```python
# Usuario dice: "Dame cotización para esta ruta"
# Sistema calcula costos de todas las opciones
# Selecciona el más económico automáticamente
item_seleccionado = min(opciones, key=lambda x: x['costo_total'])
```

### 3. **Única Opción → Selección Directa**
```python
# Solo hay 1 resultado en la base de datos
item_seleccionado = opciones[0]
```

---

## 🎨 Ejemplos de Casos Especiales

### ✅ Caso 1: Comparativa sin peso específico
```
👤 "Opciones de Puerto Quetzal a Mixco"
🤖 Comparativa con 5 opciones (sin cálculo de sobrepeso)
```

### ✅ Caso 2: Comparativa con peso específico
```
👤 "Mejores opciones para 26,000 kg de Puerto Quetzal a Mixco"
🤖 Comparativa con 5 opciones (incluye sobrepeso calculado)
```

### ✅ Caso 3: Cotización con proveedor + peso
```
👤 "Cotización de Nixon Larios para 26,000 kg"
🤖 XML de Nixon Larios con sobrepeso incluido
```

### ✅ Caso 4: Cotización sin proveedor (selección automática)
```
👤 "Dame cotización para 26,000 kg de Puerto Quetzal a Mixco"
🤖 XML del proveedor más económico (seleccionado automáticamente)
```

### ✅ Caso 5: Cambio de contexto (peso diferente)
```
Conversación:
👤 "Opciones para Puerto Quetzal a Mixco con 20,000 kg"
🤖 Comparativa con 20,000 kg

👤 "¿Y con 30,000 kg?"
🤖 Comparativa actualizada con 30,000 kg (incluye sobrepeso)

👤 "Dame cotización de Angel Paiz"
🤖 XML de Angel Paiz con 30,000 kg (mantiene contexto de peso)
```

---

## 📊 Resumen de la Lógica

| Condición | Resultado |
|-----------|-----------|
| 1 sola opción | XML (siempre) |
| Menciona "cotización" + proveedor | XML (proveedor específico) |
| Menciona "cotización" sin proveedor | XML (más económico) |
| Menciona "opciones" o "compara" | Comparativa Markdown |
| Múltiples opciones (>3) sin "cotización" | Comparativa Markdown |
| Múltiples opciones + "cotización" | XML (selecciona mejor o mencionado) |

---

## 🔧 Mejoras Implementadas

### 1. **Detección de Intención Mejorada**
- ✅ Identifica 15+ palabras clave para "cotización"
- ✅ Identifica 10+ palabras clave para "comparación"
- ✅ Prioriza "cotización" sobre "comparación" si ambas se mencionan

### 2. **Selección Inteligente de Proveedor**
- ✅ Busca nombres de proveedores en la pregunta
- ✅ Selecciona proveedor mencionado explícitamente
- ✅ Selecciona más económico automáticamente si no se especifica
- ✅ Muestra logs claros de la selección

### 3. **Cálculos Programáticos**
- ✅ **Tarifa base** siempre se calcula (incluso sin peso)
- ✅ **Sobrepeso** solo si hay peso y excede el rango base
- ✅ **Estadía** solo si excede días libres
- ✅ **Custodio** solo si se solicita explícitamente
- ✅ **Total** = suma de todos los componentes aplicables

### 4. **Nunca Respuestas Vacías**
- ✅ Query con índice específico
- ✅ Búsqueda flexible por destino
- ✅ Scan completo como último recurso
- ✅ Mensaje alternativo si realmente no hay datos

---

## 🎓 Guía para Usuarios

### Para obtener una **comparativa**:
```
"Opciones para Puerto Quetzal a Mixco"
"Compara proveedores para esta ruta"
"¿Cuál es más barato?"
```

### Para obtener una **cotización XML**:
```
"Dame la cotización de Nixon Larios"
"Genera cotización para esta ruta"
"Quiero cotización formal"
```

### Para cambiar de contexto:
```
Después de comparativa:
"Dame cotización de [proveedor]" → XML específico
"Cotiza con [proveedor]" → XML específico
"Genera cotización" → XML del más económico
```

---

**Última actualización:** 28 de enero de 2025
**Versión:** 2.0 - Lógica de decisión mejorada
