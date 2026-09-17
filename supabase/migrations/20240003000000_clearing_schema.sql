-- ============================================================
-- MIGRATION 003: Clearing Gateway Service Schema
-- ============================================================

CREATE SCHEMA IF NOT EXISTS clearing;

CREATE TABLE IF NOT EXISTS clearing.settlements (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transfer_id   UUID NOT NULL UNIQUE,
  external_ref  TEXT,
  status        TEXT NOT NULL CHECK (status IN ('PENDING', 'SETTLED', 'CANCELLED', 'FAILED')),
  attempted_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  settled_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_clearing_transfer_id ON clearing.settlements(transfer_id);
