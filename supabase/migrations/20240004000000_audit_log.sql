-- ============================================================
-- MIGRATION 004: Audit Log global + Idempotencia
-- ============================================================

-- Bitácora de auditoría: cada cambio de estado de cada paso de la Saga
CREATE TABLE IF NOT EXISTS public.saga_audit_log (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transfer_id  UUID NOT NULL,
  saga_mode    TEXT NOT NULL CHECK (saga_mode IN ('orchestration', 'choreography')),
  step_name    TEXT NOT NULL,
  step_status  TEXT NOT NULL CHECK (step_status IN (
                 'STARTED', 'SUCCESS', 'FAILED',
                 'COMPENSATING', 'COMPENSATED'
               )),
  payload      JSONB,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_transfer_id ON public.saga_audit_log(transfer_id);
CREATE INDEX IF NOT EXISTS idx_audit_created_at  ON public.saga_audit_log(created_at);

-- Tabla de idempotencia: evita dobles cobros ante reintentos (CP-05)
CREATE TABLE IF NOT EXISTS public.transfer_operations (
  idempotency_key UUID PRIMARY KEY,
  transfer_id     UUID NOT NULL,
  status          TEXT NOT NULL,
  response_cache  JSONB,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
