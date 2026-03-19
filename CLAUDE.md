# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**LogiBotIA** is a full-stack logistics tariff management system with an AI chatbot. It consists of:
- **Backend**: Python/AWS CDK defining serverless AWS infrastructure (Lambda, API Gateway, DynamoDB, Cognito)
- **Webapp**: Angular 21 frontend with AWS Amplify authentication and SSR support

---

## Backend Commands

All commands run from `Backend/`:

```bash
# Install Python dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# AWS CDK operations
cdk synth        # Synthesize CloudFormation template
cdk diff         # Show infrastructure diff
cdk deploy       # Deploy stack to AWS
cdk destroy      # Tear down stack

# Automated deployment
./deploy.sh

# Run API tests (requires deployed backend)
python test_api.py
```

**Python version:** 3.9+
**CDK version:** 2.215.0

---

## Frontend (Webapp) Commands

All commands run from `Webapp/`:

```bash
npm install           # Install dependencies
npm start             # Dev server at localhost:4200
npm run build         # Production build → dist/
npm test              # Run tests with Vitest
npm run watch         # Build in watch mode

# SSR server
npm run serve:ssr:LogiBotIA
```

**Node/npm version:** npm 10.9.2

---

## Architecture

### Backend (AWS Serverless)

**Stack entry point:** `Backend/ia_project/ia_project_stack.py`
**CDK app entry:** `Backend/app.py`

Lambda functions in `Backend/lambda/`:
- `tarifas_crud/` — CRUD handlers (create.py, read.py, update.py, delete.py) for `/tarifas` REST endpoints
- `chatbot/chatbot_terrestre.py` — AI chatbot using Amazon Nova Pro via Bedrock; supports multi-turn conversations with the last 10 messages kept as history; queries DynamoDB for tariff context
- `data_loader/dynamo_load_data.py` — One-time data seeder

**API Base URL:** `https://evukogmlq2.execute-api.us-east-1.amazonaws.com/prod/tarifas`

**DynamoDB table:** `TarifasLogistica` with PK `id` (UUID string) and 4 GSIs: `OrigenIndex`, `DestinoIndex`, `ProveedorIndex`, `RutaIndex` (origen+destino).

### Frontend (Angular 21)

**Key directories under `Webapp/src/app/`:**
- `components/` — Standalone Angular components (login, chat, tarifas, header, footer, etc.)
- `services/` — `auth.service.ts` (Cognito via Amplify), `tarifas.service.ts` (HTTP CRUD)
- `models/types.ts` — TypeScript interfaces (`Tarifa`, `RangoBasePrice`)
- `config/cognito.config.ts` — Cognito User Pool / Client IDs

**Auth flow:** AWS Amplify → Cognito → JWT stored in localStorage → `authGuard` protects routes → `auth.interceptor.ts` attaches tokens to HTTP requests.

**Data flow:** Angular component → `tarifas.service.ts` (HttpClient + RxJS) → API Gateway → Lambda → DynamoDB.

### Tarifa Data Model

```typescript
{
  id?: string;
  origen: string;
  destino: string;
  proveedor: string;
  fianza: number;
  dias_libres: number;
  estadia: number;
  tramite_de_aduana_cominter: number;
  condiciones_de_aduana_cominter: string;
  tramite_aduana: number;
  condiciones_aduana: string;
  custodio_comsi: number;
  custodio_yantarni: number;
  rango_base_precios: { min_kg: number; max_kg: number; costo: number; concepto: string }[];
}
```

---

## Key Configuration

| File | Purpose |
|---|---|
| `Backend/cdk.json` | CDK feature flags and context |
| `Webapp/tsconfig.json` | Strict TypeScript, ES2022 target |
| `Webapp/src/app/config/cognito.config.ts` | Cognito User Pool / Client IDs |

**Cognito:** User Pool `us-east-1_rOZcYSsNs`, Client `2mv4phm971j9b32hulgtjlda43`, Region `us-east-1`.

**TypeScript:** Strict mode enabled. Prettier configured for 100-char line width and single quotes (see `Webapp/package.json`).

---

## Documentation

Detailed docs live in `Backend/`:
- `ARCHITECTURE.md` — Architecture diagrams and data flows
- `API_DOCUMENTATION.md` — Full endpoint reference
- `DEPLOYMENT_GUIDE.md` — Step-by-step AWS deployment
- `INTEGRATION_EXAMPLES.md` — Frontend/backend integration examples
