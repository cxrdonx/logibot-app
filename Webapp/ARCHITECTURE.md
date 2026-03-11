# 🔄 Diagrama de Flujo - Chatbot V2 Integration

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                      FRONTEND (Angular)                         │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    app.ts (Main Component)                │  │
│  │                                                           │  │
│  │  State:                                                   │  │
│  │  • messages: Message[]          (UI)                     │  │
│  │  • conversationHistory: ChatbotMessage[]  (API)          │  │
│  │                                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│         │                            │                          │
│         │ (Auto-save)                │ (Auto-load)              │
│         ▼                            ▼                          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    localStorage                           │  │
│  │  • logibot_conversation_history                          │  │
│  │  • logibot_messages                                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS POST
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AWS API GATEWAY                              │
│  https://evukogmlq2.execute-api.us-east-1.amazonaws.com/        │
│                      /prod/chatbot                               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AWS LAMBDA                                  │
│                  (chatbot_v2.handler)                           │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  1. Recibe: { query, conversation_history }             │  │
│  │  2. Procesa query con contexto                          │  │
│  │  3. Consulta DynamoDB                                    │  │
│  │  4. Invoca Amazon Bedrock (Nova Pro)                    │  │
│  │  5. Retorna: { respuesta, items_found }                 │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
        │                                    │
        │ Query DB                           │ Invoke AI
        ▼                                    ▼
┌──────────────────┐              ┌──────────────────────┐
│   DynamoDB       │              │   Amazon Bedrock     │
│ TarifasLogistica │              │   Nova Pro v1.0      │
└──────────────────┘              └──────────────────────┘
```

---

## Flujo de una Conversación

### 📤 Request Flow

```
Usuario escribe mensaje
        │
        ▼
┌───────────────────────────────────────────────────────┐
│ 1. handleUserMessage(text)                            │
│    • Agrega mensaje a messages[] (UI)                 │
│    • Activa isTyping = true                          │
└───────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────┐
│ 2. Prepara ChatbotRequest                             │
│    {                                                  │
│      query: "mensaje del usuario",                   │
│      conversation_history: [últimos 20 msgs]         │
│    }                                                  │
└───────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────┐
│ 3. HTTP POST al API                                   │
│    → AWS API Gateway                                  │
│    → Lambda Function                                  │
│    → DynamoDB + Bedrock                              │
└───────────────────────────────────────────────────────┘
```

### 📥 Response Flow

```
Lambda retorna respuesta
        │
        ▼
┌───────────────────────────────────────────────────────┐
│ 4. Recibe ChatbotResponse                             │
│    {                                                  │
│      respuesta: "...",                               │
│      items_found: 1                                  │
│    }                                                  │
└───────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────┐
│ 5. Actualiza UI                                       │
│    • Desactiva isTyping = false                      │
│    • Agrega respuesta a messages[]                   │
└───────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────┐
│ 6. Actualiza conversationHistory                      │
│    • Push mensaje user                               │
│    • Push mensaje assistant                          │
│    • Limita a MAX_HISTORY_MESSAGES (20)              │
└───────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────┐
│ 7. Guarda en localStorage                             │
│    • logibot_conversation_history                     │
│    • logibot_messages                                 │
└───────────────────────────────────────────────────────┘
```

---

## Estructura de Datos

### Message (UI Display)
```typescript
{
  id: 1234567890,
  sender: 'user' | 'bot',
  text: "Texto del mensaje",
  type: 'text' | 'quote' | 'comparison',
  data: { /* datos adicionales */ },
  timestamp: Date,
  isError?: boolean
}
```

### ChatbotMessage (API Communication)
```typescript
{
  role: 'user' | 'assistant',
  content: [
    { text: "Contenido del mensaje" }
  ]
}
```

---

## Estados del Componente

```
┌─────────────────────────────────────────────────────┐
│             Estado Inicial (ngOnInit)               │
│                                                     │
│  1. loadHistoryFromLocalStorage()                  │
│  2. Si messages.length === 0:                      │
│     → Mostrar mensaje de bienvenida                │
│  3. isTyping = false                               │
│  4. isOnline = true                                │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│            Usuario envía mensaje                    │
│                                                     │
│  • messages.push(userMessage)                      │
│  • isTyping = true                                 │
│  • POST request al API                             │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│            Recibe respuesta exitosa                 │
│                                                     │
│  • isTyping = false                                │
│  • messages.push(botMessage)                       │
│  • conversationHistory actualizado                 │
│  • localStorage actualizado                        │
└─────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────┐
│               Listo para nuevo mensaje              │
└─────────────────────────────────────────────────────┘
```

---

## Manejo de Errores

```
Error en HTTP Request
        │
        ▼
┌───────────────────────────────────────────────────────┐
│ Determinar tipo de error:                             │
│                                                       │
│ • status === 400 → "Solicitud inválida"             │
│ • status === 500 → "Error interno del servidor"     │
│ • status === 404 → "Endpoint no encontrado"         │
│ • status === 0   → "Error de red o CORS"            │
└───────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────┐
│ Muestra mensaje de error en UI:                       │
│                                                       │
│ • isTyping = false                                    │
│ • messages.push({                                     │
│     sender: 'bot',                                    │
│     text: "❌ Error...",                             │
│     isError: true                                     │
│   })                                                  │
└───────────────────────────────────────────────────────┘
```

---

## Límites y Optimizaciones

```
┌─────────────────────────────────────────────────────┐
│         Límite de Historial (MAX = 20)              │
│                                                     │
│  conversationHistory.length > 20                   │
│         │                                           │
│         ▼                                           │
│  conversationHistory.slice(-20)                    │
│         │                                           │
│         ▼                                           │
│  Solo últimos 20 mensajes (10 intercambios)        │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│         Optimización de Tokens                      │
│                                                     │
│  • Lambda lee máximo 10 mensajes del historial     │
│  • Frontend envía máximo 20 mensajes               │
│  • Previene exceder límites de Bedrock             │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│         Persistencia localStorage                   │
│                                                     │
│  • Guarda después de cada respuesta                │
│  • Carga al iniciar la app                         │
│  • Limpia al hacer Reset                           │
│  • Compatible con SSR (isPlatformBrowser)          │
└─────────────────────────────────────────────────────┘
```

---

## Beneficios de la Arquitectura

### ✅ Stateless Lambda
- No mantiene estado en memoria
- Escalado horizontal sin problemas
- Menor costo en AWS

### ✅ Frontend Responsable
- Controla la persistencia
- Gestiona el historial
- Flexible para diferentes casos de uso

### ✅ Experiencia de Usuario
- Conversaciones contextuales
- Historial persistente
- Sin pérdida de datos al recargar

### ✅ Rendimiento
- Límite de mensajes optimizado
- Menos tokens enviados a Bedrock
- Respuestas más rápidas
