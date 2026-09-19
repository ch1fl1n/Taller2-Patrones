# 🏦 NovaBank International — Taller Patrón Saga Distribuido




Daniel David Gómez Britto 
Juan Camilo Silva Velasco 

> **Módulo:** Arquitectura de Software Distribuida & Sistemas Transaccionales  
> **Stack:** 100% Local · Python/FastAPI · React · Supabase (PostgreSQL local) · Redis · Prefect v2

---

## 📋 Tabla de Contenidos

1. [Visión General](#1-visión-general)
2. [Arquitectura del Sistema](#2-arquitectura-del-sistema)
3. [Stack Tecnológico](#3-stack-tecnológico)
4. [Estructura del Repositorio](#4-estructura-del-repositorio)
5. [Las 4 Capas Obligatorias](#5-las-4-capas-obligatorias)
6. [Patrón Saga: Orquestación vs. Coreografía](#6-patrón-saga-orquestación-vs-coreografía)
7. [Casos de Prueba Obligatorios](#7-casos-de-prueba-obligatorios)
8. [Modelo de Datos](#8-modelo-de-datos)
9. [Contratos de API entre Servicios](#9-contratos-de-api-entre-servicios)
10. [Observabilidad y Trazabilidad](#10-observabilidad-y-trazabilidad)
11. [Plan de Implementación (7 días)](#11-plan-de-implementación-7-días)
12. [Instrucciones de Instalación y Ejecución](#12-instrucciones-de-instalación-y-ejecución)
13. [Diagrama de Flujo de la Saga](#13-diagrama-de-flujo-de-la-saga)
14. [Decisiones de Diseño y Comparativa](#14-decisiones-de-diseño-y-comparativa)

---

## 1. Visión General

NovaBank International requiere procesar transferencias interbancarias de alto valor eliminando los bloqueos globales de bases de datos (2PC). La solución adopta el **Patrón Saga bajo el modelo BASE** (Basically Available, Soft state, Eventual consistency), implementando y contrastando las dos modalidades:

| Modalidad | Coordinación | Canal |
|-----------|-------------|-------|
| **Orquestación** | Orquestador central (Prefect v2) | Llamadas HTTP directas |
| **Coreografía** | Sin coordinador central | Bus de eventos (Redis Pub/Sub) |

### Principio fundamental
> Ante cualquier fallo en una fase intermedia, las **transacciones de compensación se disparan en orden estrictamente inverso** para restituir el estado de consistencia, sin dinero perdido ni registros en limbo.

---

## 2. Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Vite)                      │
│  · Formulario de transferencia    · Switches de caos                │
│  · Timeline paso a paso en RT     · Estado visual de compensaciones  │
└───────────────────────────────────┬─────────────────────────────────┘
                                    │ HTTP REST
┌───────────────────────────────────▼─────────────────────────────────┐
│                    API GATEWAY (FastAPI :8000)                       │
│  · Genera UUID de idempotencia    · Routing hacia saga               │
│  · Valida payloads                · Expone WebSocket para el frontend │
└──────────┬────────────────────────┬───────────────────────┬─────────┘
           │                        │                       │
    ┌──────▼──────┐         ┌───────▼───────┐      ┌───────▼───────┐
    │  ACCOUNT    │         │   RISK /      │      │  CLEARING     │
    │  SERVICE    │         │   FRAUD SVC   │      │  GATEWAY SVC  │
    │  :8001      │         │   :8002       │      │  :8003        │
    │             │         │               │      │               │
    │ Supabase DB │         │ Supabase DB   │      │ Supabase DB   │
    │ (schema:    │         │ (schema:      │      │ (schema:      │
    │  accounts)  │         │  risk)        │      │  clearing)    │
    └─────────────┘         └───────────────┘      └───────────────┘
           │                        │                       │
           └────────────────────────┴───────────────────────┘
                                    │
              ┌─────────────────────┴─────────────────────┐
              │          CAPA SAGA                         │
              │                                            │
              │  ┌─────────────────┐  ┌─────────────────┐ │
              │  │  ORQUESTACIÓN   │  │  COREOGRAFÍA     │ │
              │  │  (Prefect v2)   │  │  (Redis Pub/Sub) │ │
              │  └─────────────────┘  └─────────────────┘ │
              └───────────────────────────────────────────┘
                                    │
              ┌─────────────────────▼─────────────────────┐
              │     OBSERVABILIDAD (Prefect UI :4200)      │
              │   · Dashboard de flujos   · Logs en RT     │
              │   · Delays configurables  · Auditoría      │
              └───────────────────────────────────────────┘
```

---

## 3. Stack Tecnológico

| Capa | Tecnología | Puerto | Justificación |
|------|-----------|--------|---------------|
| Frontend | React 18 + Vite + TailwindCSS | 5173 | Componentes reactivos, WebSocket nativo |
| API Gateway | Python 3.11 + FastAPI | 8000 | Async, OpenAPI auto-generado, WebSocket |
| Account Service | Python 3.11 + FastAPI | 8001 | Consistente con el gateway |
| Risk Service | Python 3.11 + FastAPI | 8002 | Ídem |
| Clearing Service | Python 3.11 + FastAPI | 8003 | Ídem |
| Base de Datos | Supabase Local (PostgreSQL 15) | 5432/54321 | Schemas aislados por servicio, Row-Level Security |
| Bus de Eventos | Redis 7 (Pub/Sub + Streams) | 6379 | Liviano, cero configuración de broker |
| Orquestador | Prefect v2 (self-hosted) | 4200 | UI visual, delays nativos, retry policies |
| Contenedores | Docker + Docker Compose | — | Despliegue local reproducible |

> **Nota:** Todo corre localmente. Supabase se usa en modo `supabase start` (CLI local), lo que levanta PostgreSQL + Studio en tu máquina sin necesidad de cuenta en la nube.

---

## 4. Estructura del Repositorio

```
Taller2-Patrones/
├── docker-compose.yml              # Orquesta todos los servicios localmente
├── .env.example                    # Variables de entorno de referencia
├── README.md
│
├── frontend/                       # React + Vite
│   ├── src/
│   │   ├── components/
│   │   │   ├── TransferForm.jsx    # Formulario principal
│   │   │   ├── ChaosPanel.jsx      # Switches CP-02 a CP-05
│   │   │   ├── SagaTimeline.jsx    # Visualizador paso a paso
│   │   │   └── StatusBadge.jsx     # Chips de estado
│   │   ├── hooks/
│   │   │   └── useSagaWebSocket.js # Suscripción a eventos en RT
│   │   └── App.jsx
│   └── package.json
│
├── gateway/                        # API Gateway :8000
│   ├── main.py
│   ├── routers/
│   │   ├── transfers.py            # POST /transfers, GET /transfers/{id}
│   │   └── websocket.py            # WS /ws/{transfer_id}
│   ├── models.py
│   └── requirements.txt
│
├── services/
│   ├── account/                    # Account & Ledger Service :8001
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── debit.py            # POST /debit
│   │   │   ├── credit.py           # POST /credit
│   │   │   └── compensate.py       # POST /compensate/debit
│   │   ├── models.py
│   │   └── requirements.txt
│   │
│   ├── risk/                       # Risk & Fraud Service :8002
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── validate.py         # POST /validate
│   │   │   └── compensate.py       # POST /compensate/approval
│   │   ├── rules_engine.py         # Reglas de fraude configurables
│   │   └── requirements.txt
│   │
│   └── clearing/                   # Clearing Gateway Service :8003
│       ├── main.py
│       ├── routers/
│       │   ├── settle.py           # POST /settle
│       │   └── compensate.py       # POST /compensate/settlement
│       ├── simulator.py            # Simula timeouts y fallos de red
│       └── requirements.txt
│
├── saga/
│   ├── orchestration/
│   │   ├── transfer_flow.py        # Flujo Prefect v2 (Orquestación)
│   │   └── compensation_flow.py    # Flujo de compensación en reversa
│   └── choreography/
│       ├── publisher.py            # Emisor de eventos Redis
│       ├── subscribers/
│       │   ├── account_subscriber.py
│       │   ├── risk_subscriber.py
│       │   └── clearing_subscriber.py
│       └── event_schemas.py        # Eventos: TransferRequested, DebitApplied, etc.
│
├── supabase/
│   ├── migrations/
│   │   ├── 001_accounts_schema.sql
│   │   ├── 002_risk_schema.sql
│   │   ├── 003_clearing_schema.sql
│   │   └── 004_audit_log.sql
│   └── seed.sql                    # Cuentas de prueba con saldos
│
└── docs/
    ├── comparativa_orquestacion_vs_coreografia.md
    ├── diagramas/
    │   ├── flujo_happy_path.png
    │   ├── flujo_compensacion_riesgo.png
    │   └── flujo_compensacion_red.png
    └── decisiones_arquitectonicas.md
```

---

## 5. Las 4 Capas Obligatorias

### Capa 1 — Frontend (React + Vite)

**Responsabilidades:**
- Formulario de transferencia: cuenta origen, cuenta destino, importe
- Panel de Caos con switches para forzar cada escenario de fallo
- Timeline visual que refleja en tiempo real el progreso de cada paso de la Saga
- Conexión vía WebSocket al gateway para recibir actualizaciones de estado sin polling

**Componentes clave:**
```
ChaosPanel.jsx
  ├── switch: FORZAR_FONDOS_INSUFICIENTES  → CP-02
  ├── switch: FORZAR_FRAUDE               → CP-03
  ├── switch: FORZAR_TIMEOUT_RED          → CP-04
  └── switch: MODO_IDEMPOTENCIA           → CP-05

SagaTimeline.jsx
  ├── Step: Débito contable        [PENDIENTE / OK / COMPENSADO]
  ├── Step: Validación de riesgo   [PENDIENTE / OK / COMPENSADO]
  └── Step: Liquidación externa    [PENDIENTE / OK / FALLIDO]
```

---

### Capa 2 — API Gateway (FastAPI :8000)

**Responsabilidades:**
- Recibir `POST /transfers` y generar UUID de idempotencia
- Verificar duplicados consultando la tabla `transfer_operations` (CP-05)
- Decidir qué modo de Saga ejecutar (`?mode=orchestration` o `?mode=choreography`)
- Mantener canal WebSocket activo por transferencia para notificar al frontend
- Exponer `GET /transfers/{id}` para consultar el estado y la bitácora de auditoría

**Contrato de entrada:**
```json
POST /transfers
{
  "source_account": "ACC-001",
  "target_account": "ACC-002",
  "amount": 5000.00,
  "idempotency_key": "uuid-v4-generado-por-el-cliente",
  "saga_mode": "orchestration",
  "chaos": {
    "force_insufficient_funds": false,
    "force_fraud": false,
    "force_network_timeout": false
  }
}
```

---

### Capa 3 — Microservicios de Dominio

Cada servicio tiene **su propio schema PostgreSQL en Supabase** y no accede directamente a las tablas de los demás.

#### Account Service (:8001)
| Endpoint | Descripción |
|---------|-------------|
| `POST /debit` | Debita el monto de la cuenta origen |
| `POST /credit` | Acredita el monto en la cuenta destino |
| `POST /compensate/debit` | **Reversa:** reintegra el monto debitado |
| `GET /balance/{account_id}` | Consulta saldo disponible |

#### Risk & Fraud Service (:8002)
| Endpoint | Descripción |
|---------|-------------|
| `POST /validate` | Evalúa reglas antifraude y límites diarios |
| `POST /compensate/approval` | **Reversa:** anula la aprobación de riesgo |

#### Clearing Gateway Service (:8003)
| Endpoint | Descripción |
|---------|-------------|
| `POST /settle` | Simula la liquidación interbancaria externa |
| `POST /compensate/settlement` | **Reversa:** cancela la liquidación (si aplica) |

---

### Capa 4 — Lógica de la Saga

Ver sección 6 para el detalle completo de orquestación y coreografía.

---

## 6. Patrón Saga: Orquestación vs. Coreografía

### 6.1 Saga Orquestada (Prefect v2)

El flujo Prefect comanda directamente cada servicio. Si cualquier task falla, Prefect captura la excepción y dispara las compensaciones en **orden inverso estricto**.

```
FLUJO HAPPY PATH (CP-01)
========================
[START]
  │
  ▼
Task 1: account.debit()           → delay 2-4s → ✅ DEBIT_OK
  │
  ▼
Task 2: risk.validate()           → delay 2-4s → ✅ RISK_OK
  │
  ▼
Task 3: clearing.settle()         → delay 2-4s → ✅ SETTLED
  │
  ▼
Task 4: account.credit()          → delay 2-4s → ✅ CREDIT_OK
  │
  ▼
[CONFIRMADO]

FLUJO DE COMPENSACIÓN CP-04 (Fallo en Clearing)
================================================
[START]
  │
  ▼
Task 1: account.debit()           → ✅ DEBIT_OK
  │
  ▼
Task 2: risk.validate()           → ✅ RISK_OK
  │
  ▼
Task 3: clearing.settle()         → ❌ TIMEOUT / NETWORK_ERROR
  │
  ▼ (compensaciones en orden inverso)
Comp 2: risk.compensate_approval()   → delay 2-4s → ✅ RISK_REVERSED
  │
  ▼
Comp 1: account.compensate_debit()   → delay 2-4s → ✅ DEBIT_REVERSED
  │
  ▼
[RECHAZADO_RED — saldos íntegros]
```

**Ventajas:**
- Control centralizado y observable
- Fácil de depurar (un solo punto de verdad)
- Rollback determinístico

**Desventajas:**
- El orquestador es un punto único de fallo
- Mayor acoplamiento entre el coordinador y los servicios

---

### 6.2 Saga Coreografiada (Redis Pub/Sub)

No hay coordinador. Cada servicio escucha eventos y reacciona de forma autónoma.

```
EVENTOS DEL DOMINIO
===================
TransferRequested      → Account Service escucha → debita → emite DebitApplied
DebitApplied           → Risk Service escucha    → valida → emite RiskApproved
RiskApproved           → Clearing Service escucha → liquida → emite TransferSettled
TransferSettled        → Account Service escucha → acredita → emite TransferConfirmed

COMPENSACIONES (CP-04)
======================
ClearingFailed         → Risk Service escucha    → anula aprobación → emite RiskReversed
RiskReversed           → Account Service escucha → revierte débito → emite DebitReversed
DebitReversed          → Gateway escucha         → marca RECHAZADO_RED
```

**Esquema de eventos:**
```json
{
  "event_type": "DebitApplied",
  "transfer_id": "uuid",
  "timestamp": "ISO-8601",
  "payload": {
    "source_account": "ACC-001",
    "amount": 5000.00,
    "ledger_entry_id": "uuid"
  }
}
```

**Ventajas:**
- Alta desacoplamiento entre servicios
- Resiliente: ningún componente es coordinador único
- Escala naturalmente

**Desventajas:**
- Difícil de rastrear el flujo completo
- Riesgo de dependencias circulares si los eventos no se diseñan bien
- Debugging más complejo

---

## 7. Casos de Prueba Obligatorios

| ID | Escenario | Disparador Frontend | Compensaciones | Estado Final |
|----|-----------|--------------------|--------------:|--------------|
| CP-01 | Camino feliz | Sin switches activos | Ninguna | `CONFIRMADO` |
| CP-02 | Fondos insuficientes | Monto > saldo | Rechazo inmediato (sin compensar) | `RECHAZADO_FONDOS` |
| CP-03 | Fallo de riesgo/fraude | Switch `FORZAR_FRAUDE` | Reversa Task 1 (débito) | `RECHAZADO_RIESGO` |
| CP-04 | Caída de red externa | Switch `FORZAR_TIMEOUT_RED` | Reversa Task 2 + Task 1 | `RECHAZADO_RED` |
| CP-05 | Idempotencia | Mismo `idempotency_key` | Sin ejecución, respuesta cacheada | Saldos inalterados |

---

## 8. Modelo de Datos

### Schema `accounts` (Account Service)

```sql
-- 001_accounts_schema.sql
CREATE SCHEMA IF NOT EXISTS accounts;

CREATE TABLE accounts.accounts (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_code TEXT UNIQUE NOT NULL,         -- "ACC-001"
  owner_name   TEXT NOT NULL,
  balance      NUMERIC(15, 2) NOT NULL CHECK (balance >= 0),
  created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE accounts.ledger_entries (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transfer_id     UUID NOT NULL,             -- FK lógica (sin FK real entre schemas)
  account_id      UUID NOT NULL REFERENCES accounts.accounts(id),
  entry_type      TEXT NOT NULL,             -- 'DEBIT' | 'CREDIT' | 'REVERSAL'
  amount          NUMERIC(15, 2) NOT NULL,
  status          TEXT NOT NULL DEFAULT 'PENDING', -- 'APPLIED' | 'REVERSED'
  created_at      TIMESTAMPTZ DEFAULT now()
);
```

### Schema `risk` (Risk Service)

```sql
-- 002_risk_schema.sql
CREATE SCHEMA IF NOT EXISTS risk;

CREATE TABLE risk.validations (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transfer_id  UUID NOT NULL UNIQUE,
  status       TEXT NOT NULL,               -- 'APPROVED' | 'REJECTED' | 'REVERSED'
  risk_score   NUMERIC(5,2),
  reason       TEXT,
  created_at   TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE risk.daily_limits (
  account_id    UUID NOT NULL,
  date          DATE NOT NULL DEFAULT CURRENT_DATE,
  total_debited NUMERIC(15, 2) DEFAULT 0,
  PRIMARY KEY (account_id, date)
);
```

### Schema `clearing` (Clearing Service)

```sql
-- 003_clearing_schema.sql
CREATE SCHEMA IF NOT EXISTS clearing;

CREATE TABLE clearing.settlements (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transfer_id       UUID NOT NULL UNIQUE,
  external_ref      TEXT,                   -- Ref del sistema interbancario simulado
  status            TEXT NOT NULL,          -- 'PENDING' | 'SETTLED' | 'CANCELLED' | 'FAILED'
  attempted_at      TIMESTAMPTZ DEFAULT now(),
  settled_at        TIMESTAMPTZ
);
```

### Tabla de Auditoría Global

```sql
-- 004_audit_log.sql
-- En schema público / compartido (solo lectura para el Gateway)
CREATE TABLE public.saga_audit_log (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transfer_id  UUID NOT NULL,
  saga_mode    TEXT NOT NULL,               -- 'orchestration' | 'choreography'
  step_name    TEXT NOT NULL,
  step_status  TEXT NOT NULL,               -- 'STARTED' | 'SUCCESS' | 'FAILED' | 'COMPENSATING' | 'COMPENSATED'
  payload      JSONB,
  created_at   TIMESTAMPTZ DEFAULT now()
);

-- Tabla de idempotencia
CREATE TABLE public.transfer_operations (
  idempotency_key UUID PRIMARY KEY,
  transfer_id     UUID NOT NULL,
  status          TEXT NOT NULL,
  response_cache  JSONB,
  created_at      TIMESTAMPTZ DEFAULT now()
);
```

---

## 9. Contratos de API entre Servicios

### Debit (Account Service)

```
POST http://account-service:8001/debit
Body: { "transfer_id": "uuid", "account_id": "uuid", "amount": 5000.00 }
200 OK: { "ledger_entry_id": "uuid", "new_balance": 45000.00 }
422: { "error": "INSUFFICIENT_FUNDS", "available": 3000.00 }
```

### Validate (Risk Service)

```
POST http://risk-service:8002/validate
Body: { "transfer_id": "uuid", "source_account": "ACC-001", "amount": 5000.00, "force_fraud": false }
200 OK: { "validation_id": "uuid", "approved": true, "risk_score": 12.5 }
422: { "error": "FRAUD_DETECTED", "risk_score": 87.3 }
```

### Settle (Clearing Service)

```
POST http://clearing-service:8003/settle
Body: { "transfer_id": "uuid", "source": "ACC-001", "target": "ACC-002", "amount": 5000.00, "force_timeout": false }
200 OK: { "settlement_id": "uuid", "external_ref": "CLR-XYZ-123" }
504: { "error": "NETWORK_TIMEOUT", "retry_after": 30 }
```

---

## 10. Observabilidad y Trazabilidad

### Prefect v2 (Dashboard local :4200)

- Cada transferencia genera un **Prefect Flow Run** con nombre `transfer-{uuid}`
- Cada task del flujo tiene un **delay configurable de 2 a 4 segundos** para observar la evolución en la UI
- Los task de compensación se marcan con el prefijo `COMPENSATE_` para distinguirlos visualmente
- Prefect registra automáticamente: duración, estado, logs y artefactos de cada step

### Auditoría en Base de Datos

Cada cambio de estado escribe un registro en `public.saga_audit_log`:

```
transfer_id | step_name              | step_status  | created_at
------------|------------------------|--------------|------------
abc-123     | DEBIT                  | STARTED      | 10:00:00.100
abc-123     | DEBIT                  | SUCCESS      | 10:00:02.350
abc-123     | RISK_VALIDATION        | STARTED      | 10:00:02.400
abc-123     | RISK_VALIDATION        | FAILED       | 10:00:04.800
abc-123     | COMPENSATE_DEBIT       | STARTED      | 10:00:04.850
abc-123     | COMPENSATE_DEBIT       | COMPENSATED  | 10:00:07.100
```

### WebSocket en tiempo real

El Gateway mantiene un canal WS por transferencia activa. El frontend recibe eventos de estado sin polling:

```json
{ "transfer_id": "uuid", "step": "DEBIT", "status": "SUCCESS", "timestamp": "..." }
{ "transfer_id": "uuid", "step": "RISK_VALIDATION", "status": "COMPENSATING", "timestamp": "..." }
```

---

## 11. Plan de Implementación (7 días)

### Día 1 — Sesión presencial (3 horas)
- [ ] Levantar entorno Docker + Supabase local
- [ ] Crear migrations SQL (schemas aislados)
- [ ] Implementar Account Service (debit + compensate básico)
- [ ] Implementar primer flujo Prefect con CP-01 (Happy Path)
- [ ] Verificar que el débito y crédito funcionan correctamente

### Día 2 — Infraestructura completa
- [ ] Completar Risk Service (validate + compensate)
- [ ] Completar Clearing Service (settle + compensate + simulador de fallos)
- [ ] Configurar Redis para coreografía
- [ ] Agregar tabla de auditoría y logging en cada step

### Día 3 — Saga Orquestada completa
- [ ] Implementar `transfer_flow.py` en Prefect con los 4 tasks + delays
- [ ] Implementar `compensation_flow.py` con reversa en orden inverso
- [ ] Probar CP-02, CP-03 y CP-04 en modo orquestación
- [ ] Validar que la auditoría registra cada paso y compensación

### Día 4 — Saga Coreografiada completa
- [ ] Definir todos los eventos en `event_schemas.py`
- [ ] Implementar publishers y subscribers de Redis
- [ ] Probar CP-03 y CP-04 en modo coreografía
- [ ] Verificar que las compensaciones se disparan autónomamente

### Día 5 — API Gateway + Idempotencia
- [ ] Implementar `POST /transfers` con generación de UUID
- [ ] Implementar lógica CP-05 (idempotency_key lookup)
- [ ] Agregar WebSocket para notificaciones en tiempo real
- [ ] Integrar selector de modo Saga (`orchestration` vs `choreography`)

### Día 6 — Frontend
- [ ] Crear `TransferForm.jsx` conectado al gateway
- [ ] Crear `ChaosPanel.jsx` con todos los switches
- [ ] Crear `SagaTimeline.jsx` con suscripción WebSocket
- [ ] Pruebas manuales de todos los CP desde la UI

### Día 7 — Pulido, documentación y video
- [ ] Ajustes finales de UX y manejo de errores en el frontend
- [ ] Redactar `comparativa_orquestacion_vs_coreografia.md`
- [ ] Generar diagramas de flujo finales
- [ ] Grabar video demostrativo (máximo 6 minutos) mostrando los 5 CP
- [ ] Revisar rúbrica y validar checklist completo

---

## 12. Instrucciones de Instalación y Ejecución

### Prerrequisitos

```bash
# Verificar versiones requeridas
node --version        # >= 18.x
python --version      # >= 3.11
docker --version      # >= 24.x
supabase --version    # CLI >= 1.x  (npm install -g supabase)
```

### 1. Clonar y configurar variables

```bash
git clone <repo-url>
cd Taller2-Patrones
cp .env.example .env
# Editar .env con los valores locales (ver sección de variables)
```

### 2. Levantar Supabase local

```bash
supabase start
# Esto levanta PostgreSQL en :5432 y Supabase Studio en :54323
# Tomar nota del anon key y service_role key que imprime en consola

supabase db push   # Ejecuta todas las migrations en supabase/migrations/
supabase db seed   # Carga cuentas de prueba desde supabase/seed.sql
```

### 3. Levantar todos los servicios con Docker Compose

```bash
docker-compose up --build
```

Esto levanta:
- Redis en `:6379`
- Account Service en `:8001`
- Risk Service en `:8002`
- Clearing Service en `:8003`
- API Gateway en `:8000`
- Prefect Server en `:4200`

### 4. Levantar el Frontend

```bash
cd frontend
npm install
npm run dev
# Disponible en http://localhost:5173
```

### 5. Registrar el flujo Prefect

```bash
cd saga/orchestration
python transfer_flow.py   # Despliega el flow en el servidor Prefect local
```

### 6. Iniciar los subscribers de coreografía

```bash
cd saga/choreography
python -m subscribers.account_subscriber &
python -m subscribers.risk_subscriber &
python -m subscribers.clearing_subscriber &
```

### Variables de entorno (.env)

```env
# Supabase Local
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
SUPABASE_URL=http://localhost:54321
SUPABASE_ANON_KEY=<generado por supabase start>
SUPABASE_SERVICE_KEY=<generado por supabase start>

# Redis
REDIS_URL=redis://localhost:6379

# Prefect
PREFECT_API_URL=http://localhost:4200/api

# Delays de observabilidad (segundos)
SAGA_STEP_DELAY_MIN=2
SAGA_STEP_DELAY_MAX=4

# Servicios internos
ACCOUNT_SERVICE_URL=http://localhost:8001
RISK_SERVICE_URL=http://localhost:8002
CLEARING_SERVICE_URL=http://localhost:8003
```

### Cuentas de prueba (seed.sql)

| Código | Propietario | Saldo inicial |
|--------|-------------|---------------|
| ACC-001 | Carlos Mendoza | $50,000.00 |
| ACC-002 | Laura Patiño | $30,000.00 |
| ACC-003 | NovaBank Reserve | $1,000,000.00 |

---

## 13. Diagrama de Flujo de la Saga

```
HAPPY PATH (CP-01)
──────────────────
Frontend ──POST /transfers──► Gateway
                               │
                               ├─► [Prefect Flow Start]
                               │
                               ├─[delay]─► AccountSvc.debit()       ✅
                               ├─[delay]─► RiskSvc.validate()        ✅
                               ├─[delay]─► ClearingSvc.settle()      ✅
                               └─[delay]─► AccountSvc.credit()       ✅
                                                    │
                               Gateway ◄────────────┘
                               │
Frontend ◄──WS: CONFIRMADO─────┘

COMPENSACIÓN CP-04 (Fallo Red)
──────────────────────────────
Frontend ──POST /transfers (force_timeout)──► Gateway
                                               │
                               ┌───────────────┘
                               ├─[delay]─► AccountSvc.debit()          ✅
                               ├─[delay]─► RiskSvc.validate()           ✅
                               ├─[delay]─► ClearingSvc.settle()         ❌ TIMEOUT
                               │
                               │  ← Orquestador detecta el fallo →
                               │
                               ├─[delay]─► RiskSvc.compensate()         ↩ REVERSED
                               └─[delay]─► AccountSvc.compensate()      ↩ REVERSED
                                                    │
                               Gateway ◄────────────┘
                               │
Frontend ◄──WS: RECHAZADO_RED──┘
```

---

## 14. Decisiones de Diseño y Comparativa

### Por qué Supabase local y no PostgreSQL puro

Supabase CLI (`supabase start`) levanta un PostgreSQL completo con Studio UI en local, lo que facilita:
- Inspección visual de tablas durante las demos
- Aplicación de migrations versionadas con `supabase db push`
- Row-Level Security para simular el aislamiento de datos por servicio

### Por qué Redis para la coreografía

Redis Pub/Sub es la opción más ligera para un entorno educativo local. Kafka o RabbitMQ añaden complejidad operacional innecesaria para el objetivo del taller. Redis Streams (alternativa) ofrece persistencia si se necesita replay de eventos.

### Por qué Prefect v2 y no Temporal o Conductor

Prefect v2 tiene una UI self-hosted extremadamente visual con cero configuración adicional, delays nativos entre tasks y una API Python idiomática. Esto maximiza la observabilidad requerida por la rúbrica sin overhead de aprendizaje.

### Garantía de consistencia eventual

En ambos modos (orquestación y coreografía), las compensaciones son **idempotentes**: ejecutar la misma compensación dos veces no produce efectos secundarios adicionales. Esto se garantiza verificando el estado actual en base de datos antes de aplicar cualquier reversa.

---

## ✅ Checklist de Rúbrica

| Criterio | Peso | Implementado por |
|----------|------|-----------------|
| Saga + Compensaciones en orden inverso (todos los CP) | 40% | `saga/orchestration/` + `saga/choreography/` |
| Orquestación Y Coreografía implementadas y contrastadas | 20% | Prefect flow + Redis subscribers |
| Observabilidad, delays 2-4s, trazabilidad de estados | 15% | Prefect UI + `saga_audit_log` + WebSocket |
| Frontend con switches de caos y timeline en RT | 10% | `frontend/src/components/` |
| Microservicios aislados + idempotencia (CP-05) | 10% | `services/` + `transfer_operations` table |
| Documentación, video y despliegue reproducible | 5% | `docs/` + `docker-compose.yml` + este README |

---

*Equipo: NovaBank Engineering · Taller Práctico de Arquitectura Distribuida*
