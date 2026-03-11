# Angular Frontend Builder — Persistent Memory
## LogiBotIA / ALCE V2 Project

### Project Root
`/Users/josecardona/Desktop/IA App/` — Git repo root.
All frontend work is in `Webapp/src/app/`.

### Key Files
- Models: `models/types.ts` — all shared interfaces (Message, XMLQuotation, ChatbotMessage, MaritimeQuotation, etc.)
- Routes: `app.routes.ts`
- Services: `services/tarifas.service.ts`, `services/maritime-quotations.service.ts`, `services/auth.service.ts`
- Auth guard: `services/auth.guard.ts`
- Chat logic lives in `components/chat-container/chat-container.ts` (not `chat/chat.ts` — that is the dumb display child)

### Component Patterns
- All components are **standalone** — always include `CommonModule`, `FormsModule` in imports as needed
- File naming: `component-name.ts` / `.html` / `.css` (no `.component.` infix)
- Selector: `app-[name]`
- Dependency injection: constructor-based (`constructor(private svc: Service)`) is the existing project style; `inject()` also acceptable
- CSS files use class-based BEM-lite styling, no Tailwind in form/list components (Tailwind only used in chat-container inline template)

### Existing Route Prefix Conventions
- Terrestre tarifas: `/tarifas`, `/tarifas/list`, `/tarifas/create`, `/tarifas/edit/:id`, `/tarifas/view/:id`
- Maritime quotations: `/tarifas/maritimo/list`, `/tarifas/maritimo/create`, `/tarifas/maritimo/edit/:id`, `/tarifas/maritimo/view/:id`
- Chatbot terrestre: `/` (root, ChatContainerComponent)
- Chatbot marítimo: `/chatbot-maritimo`

### API Endpoints
- Base: `https://evukogmlq2.execute-api.us-east-1.amazonaws.com/prod`
- Terrestre CRUD: `/tarifas`
- Maritime CRUD: `/maritime-quotations`
- Chatbot terrestre: `/chatbot`
- Chatbot marítimo: `/chatbot-maritimo`
- Auth interceptor attaches JWT automatically — never add Authorization headers manually

### Auth / Storage
- localStorage keys used: `logibot_conversations`, `logibot_current_conversation_id` (terrestre chatbot)
- localStorage keys for ALCE: `alce_maritimo_messages`, `alce_maritimo_history`
- Always guard `localStorage` access with `isPlatformBrowser(platformId)` for SSR safety

### Typing Effect Pattern
- Used in `chat-container.ts`: start with empty message, use `setInterval` at 12-15ms per char
- Track active intervals in `activeTypingIntervals: number[]`, clear on `ngOnDestroy`
- Call `cdr.detectChanges()` inside the interval for reactivity

### TarifaMaritima → MaritimeQuotation Mapping
Form field → API field:
- `supplierName` → `prepared_by`
- `requestedBy.nameCompany` → `company.name`
- `requestedBy.primaryContact` → `company.contact` and `requested_by`
- `requestedBy.address` → `company.address`
- `requestedBy.vatNumber` → `company.vat_number`
- `origin.portCodeName` → `routing.origin_port`
- `destination.portCodeName` → `routing.destination_port`
- `quoteInfo.viaPort` → `routing.via_port`
- `details.quotationNumber` → `quotation_number`
- `charges[].price` → `line_items[].unit_price`
- `charges[].quantity * price` → `line_items[].amount`
- Sum of amounts → `total_amount`
- `tarifa.notes` → `terms_and_conditions.general_notes`

### Header Component Events
- `(onReset)` — reset current conversation
- `(onLogout)` — logout handler
- `(onNewConversation)`, `(onSelectConversation)`, `(onDeleteConversation)` — conversation management
- `[isOnline]`, `[conversations]`, `[currentConversationId]` — inputs
- For simple pages (forms, lists), just use `<app-header></app-header>` with no bindings

### CSS Color Palette
- Primary blue (brand): `#050D9E`
- Maritime blue: `#0369a1`
- Success green: `#28a745` / `#155724`
- Error red: `#dc3545` / `#721c24`
- Background gradient: `linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)`
- Dark selector card: `#0b1220`

### TypeScript Strict Rules Enforced
- No implicit `any` — always type observables
- Optional fields: use `?` and `?? fallback` when mapping API → form
- `err.message ?? 'Error desconocido'` pattern for HTTP error messages
- Private methods only called internally, never exposed in template
