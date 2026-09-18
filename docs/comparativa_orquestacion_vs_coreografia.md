# Comparativa: Orquestación vs. Coreografía en el Patrón Saga

**Proyecto:** NovaBank International — Transferencias Interbancarias  
**Módulo:** Arquitectura de Software Distribuida & Sistemas Transaccionales

---

## 1. Contexto

El Patrón Saga resuelve el problema de las transacciones distribuidas en microservicios sin usar bloqueos globales (2PC). Cuando una operación abarca múltiples servicios independientes, la Saga divide esa operación en transacciones locales y, si alguna falla, ejecuta **transacciones de compensación en orden inverso** para restituir la consistencia.

Este proyecto implementa **ambas modalidades** sobre el mismo dominio bancario, permitiendo contrastarlas directamente.

---

## 2. Orquestación — El Coordinador Central

### ¿Cómo funciona?

Existe un componente central (`saga/orchestration/orchestrator.py`) que **sabe toda la secuencia** y comanda cada paso explícitamente via HTTP.

```
Gateway
  └─► Orquestador (orchestrator.py)
        ├─[delay 1-2s]─► POST account:8001/debit        ✅
        ├─[delay 1-2s]─► POST risk:8002/validate        ✅
        ├─[delay 1-2s]─► POST clearing:8003/settle      ❌ falla
        │
        │  ← detecta el error, ejecuta compensaciones en reversa ←
        │
        ├─[delay 1-2s]─► POST risk:8002/compensate/approval     ↩
        └─[delay 1-2s]─► POST account:8001/compensate/debit     ↩
```

### Flujo del código

```python
# orchestrator.py — cada paso es explícito y secuencial
completed = []   # registro de qué pasos tuvieron éxito

# Paso 1
result = await call("POST", f"{ACCOUNT_URL}/debit", {...})
completed.append("DEBIT")

# Paso 2
result = await call("POST", f"{RISK_URL}/validate", {...})
completed.append("RISK")

# Paso 3 — si falla:
except HTTPStatusError:
    # compensar en ORDEN INVERSO de completed
    for step in reversed(completed):   # → RISK, luego DEBIT
        await compensate(step)
```

### Características

| Aspecto | Detalle |
|---------|---------|
| **Coordinación** | Un solo componente conoce y dirige toda la secuencia |
| **Comunicación** | Llamadas HTTP síncronas directas a cada servicio |
| **Compensación** | El orquestador llama explícitamente a cada endpoint de reversa |
| **Observabilidad** | Un único punto de verdad: el orquestador sabe en qué paso está |
| **Trazabilidad** | Fácil: el orquestador registra cada paso en `saga_audit_log` |
| **Acoplamiento** | Alto: el orquestador conoce las URLs y contratos de todos los servicios |
| **Punto único de fallo** | Sí: si el orquestador cae, la saga queda incompleta |

---

## 3. Coreografía — Sin Coordinador Central

### ¿Cómo funciona?

No existe ningún componente que dirija el flujo. Cada servicio **escucha eventos de Redis** y reacciona de forma autónoma emitiendo nuevos eventos.

```
Gateway publica ──► [Redis: TRANSFER_REQUESTED]
                         │
                    Account Subscriber escucha
                         │ debita
                         └──► [Redis: DEBIT_APPLIED]
                                    │
                               Risk Subscriber escucha
                                    │ valida
                                    └──► [Redis: RISK_APPROVED]
                                               │
                                          Clearing Subscriber escucha
                                               │ liquida ❌ falla
                                               └──► [Redis: CLEARING_FAILED]
                                                         │
                                                    Risk Subscriber escucha
                                                         │ revierte aprobación
                                                         └──► [Redis: COMPENSATE_DEBIT]
                                                                    │
                                                               Account Subscriber escucha
                                                                    │ revierte débito
                                                                    └──► [Redis: TRANSFER_COMPENSATED]
```

### Canales de eventos

```
novabank:transfer:requested   → Inicia la saga
novabank:debit:applied        → Débito exitoso
novabank:debit:failed         → Débito falló (fondos insuficientes)
novabank:risk:approved        → Riesgo aprobado
novabank:risk:rejected        → Riesgo rechazado → dispara compensación
novabank:clearing:settled     → Liquidación exitosa
novabank:clearing:failed      → Liquidación falló → dispara compensación en cadena
novabank:credit:applied       → Crédito exitoso
novabank:transfer:confirmed   → Saga completada exitosamente
novabank:transfer:compensated → Saga revertida exitosamente
novabank:compensate:debit     → Orden de revertir el débito
novabank:compensate:risk      → Orden de revertir la aprobación de riesgo
```

### Características

| Aspecto | Detalle |
|---------|---------|
| **Coordinación** | Ninguna: cada servicio reacciona de forma autónoma |
| **Comunicación** | Eventos asíncronos publicados en Redis Pub/Sub |
| **Compensación** | Cada servicio escucha el evento de compensación y actúa solo |
| **Observabilidad** | Difícil: el flujo está distribuido entre múltiples procesos |
| **Trazabilidad** | Requiere correlacionar eventos por `transfer_id` en Redis |
| **Acoplamiento** | Bajo: los servicios solo conocen los nombres de los eventos |
| **Punto único de fallo** | No: ningún componente es indispensable para arrancar el flujo |

---

## 4. Tabla Comparativa Directa

| Criterio | Orquestación | Coreografía |
|----------|-------------|-------------|
| **¿Quién dirige el flujo?** | Orquestador central | Nadie — cada servicio reacciona |
| **Protocolo** | HTTP síncrono | Redis Pub/Sub asíncrono |
| **Visibilidad del flujo** | Alta — un solo punto de verdad | Baja — flujo emergente |
| **Facilidad de debug** | Alta — stack trace lineal | Baja — hay que correlacionar eventos |
| **Acoplamiento** | Alto — orquestador conoce a todos | Bajo — servicios solo conocen eventos |
| **Resiliencia** | Menor — orquestador es SPOF | Mayor — sin punto único de fallo |
| **Escalabilidad** | Limitada por el orquestador | Alta — cada subscriber es independiente |
| **Orden de compensaciones** | Garantizado — lista `reversed(completed)` | Garantizado — cadena de eventos inversa |
| **Consistencia eventual** | Sí | Sí |
| **Idempotencia** | Sí — verificación en cada compensación | Sí — verificación en cada compensación |
| **Cuándo usarlo** | Flujos complejos, pocas etapas, baja carga | Flujos simples, muchos servicios, alta carga |

---

## 5. Ejemplo Concreto: CP-04 (Caída de red) en ambos modos

### Orquestación (orchestrator.py)

```
1. Orquestador llama POST /debit       → éxito, completed = ["DEBIT"]
2. Orquestador llama POST /validate    → éxito, completed = ["DEBIT","RISK"]
3. Orquestador llama POST /settle      → falla 504
4. Orquestador itera reversed(completed):
   - Llama POST /compensate/approval   → Risk revertido
   - Llama POST /compensate/debit      → Débito revertido
5. Retorna RECHAZADO_RED
```

El orquestador tiene **control total** del orden de compensación porque mantiene la lista `completed` y la itera en reversa.

### Coreografía (Redis events)

```
1. Gateway publica TRANSFER_REQUESTED
2. Account subscriber escucha → debita → publica DEBIT_APPLIED
3. Risk subscriber escucha → valida → publica RISK_APPROVED
4. Clearing subscriber escucha → falla → publica CLEARING_FAILED
                                       → publica COMPENSATE_RISK   ← dispara cadena
5. Risk subscriber escucha COMPENSATE_RISK → revierte → publica COMPENSATE_DEBIT
6. Account subscriber escucha COMPENSATE_DEBIT → revierte → publica TRANSFER_COMPENSATED
```

La compensación también es en orden inverso, pero está **codificada en los propios eventos**: clearing le dice a risk que se revierta, y risk le dice a account. No hay nadie que "sepa" el orden — emerge de la cadena de eventos.

---

## 6. ¿Cuál elegir?

**Usa Orquestación cuando:**
- El flujo tiene muchas condiciones y bifurcaciones
- Necesitas visibilidad clara del estado en todo momento
- El equipo prefiere debugging lineal
- La saga tiene pocas etapas (< 5)

**Usa Coreografía cuando:**
- Los servicios deben ser completamente autónomos
- Necesitas escalar horizontalmente los subscribers
- El sistema debe tolerar la caída del "coordinador"
- El flujo es relativamente lineal sin muchas bifurcaciones

**En NovaBank usamos ambas** para demostrar el contraste: la orquestación es observable paso a paso en el Timeline del frontend, mientras la coreografía muestra cómo los servicios se coordinan sin ningún componente central, usando solo Redis como bus de mensajes.

---

## 7. Consistencia Eventual Garantizada

En ambos modos, la consistencia se garantiza mediante:

1. **Compensaciones idempotentes**: cada endpoint de reversa verifica si ya fue revertido antes de actuar, evitando dobles reversas.
2. **Registro en audit_log**: cada cambio de estado queda registrado en `public.saga_audit_log` con timestamp.
3. **Tabla de idempotencia**: `public.transfer_operations` cachea el resultado de cada operación por `idempotency_key`, evitando dobles cobros (CP-05).
4. **Check de saldo atómico**: el débito usa `FOR UPDATE` en PostgreSQL para evitar race conditions.

> **Principio BASE aplicado:** el sistema no garantiza atomicidad global (como haría 2PC), sino que garantiza que *eventualmente* — a través de las compensaciones — todos los servicios convergen a un estado consistente: o todos confirman la transferencia, o todos la revierten.
