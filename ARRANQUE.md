# ARRANQUE — NovaBank Saga

Guía de levantamiento completo del stack local. Leer antes de arrancar.

---

## Prerequisitos (verificar manualmente)

- **Docker Desktop** debe estar **abierto y corriendo** (ícono de ballena en la barra de tareas sin círculo de carga)
- Supabase CLI instalado en `~\scoop\shims\supabase.exe`
- Python 3.12 en `C:\Users\chifl\AppData\Local\Programs\Python\Python312`
- Node.js 18+ instalado
- `venv` ya creado en la raíz del proyecto

Verificar Docker antes de todo:
```powershell
docker ps
# debe mostrar tabla vacía, sin error
```

---

## Orden de levantamiento

### 1. Supabase (PostgreSQL + Studio)

```powershell
cd C:\Users\chifl\Downloads\Taller2-Patrones
& "$env:USERPROFILE\scoop\shims\supabase.exe" start
```

Esperar hasta que imprima la tabla con Studio/DB/Auth Keys (~60s).  
Si ya arrancó antes, las imágenes están cacheadas y tarda ~15s.

**Puertos:**
- DB: `postgresql://postgres:postgres@127.0.0.1:54322/postgres`
- Studio UI: http://127.0.0.1:54323
- API: http://127.0.0.1:54321

> Las migrations y el seed se aplican automáticamente al hacer `start`.  
> Si las tablas están vacías hacer: `& "$env:USERPROFILE\scoop\shims\supabase.exe" db reset`

---

### 2. Redis

```powershell
docker run --rm --name novabank-redis -p 6379:6379 redis:7-alpine
```

Dejar corriendo en background (o en una terminal aparte).  
Verificar: `docker ps --filter name=novabank-redis`

---

### 3. Microservicios Python (4 terminales separadas)

Desde la raíz `C:\Users\chifl\Downloads\Taller2-Patrones`:

```powershell
# Terminal 1 — Account Service :8001
.\venv\Scripts\python -m uvicorn services.account.main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2 — Risk Service :8002
.\venv\Scripts\python -m uvicorn services.risk.main:app --host 0.0.0.0 --port 8002 --reload

# Terminal 3 — Clearing Service :8003
.\venv\Scripts\python -m uvicorn services.clearing.main:app --host 0.0.0.0 --port 8003 --reload

# Terminal 4 — API Gateway :8000
.\venv\Scripts\python -m uvicorn gateway.main:app --host 0.0.0.0 --port 8000 --reload
```

Esperar a ver `Application startup complete.` en cada uno.

---

### 4. Subscribers de Coreografía (3 terminales adicionales)

Necesarios para que el modo **Coreografía (Redis)** funcione.

```powershell
# Terminal 5
.\venv\Scripts\python -m saga.choreography.subscribers.account_subscriber

# Terminal 6
.\venv\Scripts\python -m saga.choreography.subscribers.risk_subscriber

# Terminal 7
.\venv\Scripts\python -m saga.choreography.subscribers.clearing_subscriber
```

Cada uno debe imprimir `[xxx-subscriber] Listening...`

---

### 5. Frontend React

```powershell
cd C:\Users\chifl\Downloads\Taller2-Patrones\frontend
npm run dev
```

Disponible en: **http://localhost:5173**

---

## Verificación rápida

```powershell
# Health check de los 4 servicios
@(8000,8001,8002,8003) | ForEach-Object {
  $r = Invoke-RestMethod "http://localhost:$_/health"
  Write-Host ":$_ $($r.service) = $($r.status)"
}

# Cuentas de prueba cargadas
Invoke-RestMethod "http://localhost:8000/accounts"
```

Debe mostrar: ACC-001 ($50.000), ACC-002 ($30.000), ACC-003 ($1.000.000)

---

## Estado completo cuando todo está arriba

| Servicio | URL | Comando |
|---------|-----|---------|
| Frontend | http://localhost:5173 | `npm run dev` |
| API Gateway | http://localhost:8000 | uvicorn puerto 8000 |
| Account Service | http://localhost:8001 | uvicorn puerto 8001 |
| Risk Service | http://localhost:8002 | uvicorn puerto 8002 |
| Clearing Service | http://localhost:8003 | uvicorn puerto 8003 |
| Redis | localhost:6379 | docker run |
| PostgreSQL | localhost:54322 | supabase start |
| Supabase Studio | http://127.0.0.1:54323 | supabase start |
| account-subscriber | — | python -m saga... |
| risk-subscriber | — | python -m saga... |
| clearing-subscriber | — | python -m saga... |

---

## Casos de prueba

| CP | Switch a activar | Resultado esperado | Duración |
|----|-----------------|-------------------|----------|
| CP-01 | Ninguno | CONFIRMADO — 4 pasos verdes | ~6-8s |
| CP-02 | Fondos insuficientes | RECHAZADO_FONDOS — inmediato | <1s |
| CP-03 | Forzar fraude | RECHAZADO_RIESGO — reversa débito | ~4-6s |
| CP-04 | Timeout red externa | RECHAZADO_RED — reversa riesgo+débito | ~8-10s |
| CP-05 | Copiar clave idempotencia y reenviar | Respuesta cacheada, sin doble cobro | <1s |

---

## Apagar todo

```powershell
# Detener Supabase
& "$env:USERPROFILE\scoop\shims\supabase.exe" stop

# Detener Redis
docker stop novabank-redis

# Los demás procesos: Ctrl+C en cada terminal
```

---

## Si algo falla

**`asyncpg` no conecta a la DB:**  
→ Supabase no está corriendo. Ejecutar `supabase start` primero.

**`redis.exceptions.ConnectionError`:**  
→ Redis no está corriendo. Ejecutar el `docker run` del paso 2.

**Frontend carga pero no aparecen cuentas:**  
→ El gateway no está corriendo o Supabase no tiene el seed.  
→ Verificar con `Invoke-RestMethod http://localhost:8000/health`

**CP-04 se queda colgado más de 15s:**  
→ El timeout de httpx expiró. Revisar que `orchestrator.py` tenga `timeout=30.0`.

**Coreografía no responde:**  
→ Los subscribers no están corriendo. Levantar paso 4.

**Supabase falla con `unhealthy`:**  
→ Analytics o Storage dando problema. Verificar que en `supabase/config.toml`:  
```toml
[analytics]
enabled = false

[storage]
enabled = false
```
