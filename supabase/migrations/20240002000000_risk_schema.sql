-- ============================================================
-- MIGRATION 002: Risk & Fraud Service Schema
-- ============================================================

CREATE SCHEMA IF NOT EXISTS risk;

CREATE TABLE IF NOT EXISTS risk.validations (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transfer_id  UUID NOT NULL UNIQUE,
  status       TEXT NOT NULL CHECK (status IN ('APPROVED', 'REJECTED', 'REVERSED')),
  risk_score   NUMERIC(5,2),
  reason       TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS risk.daily_limits (
  account_id    TEXT NOT NULL,
  date          DATE NOT NULL DEFAULT CURRENT_DATE,
  total_debited NUMERIC(15, 2) NOT NULL DEFAULT 0,
  PRIMARY KEY (account_id, date)
);

CREATE INDEX IF NOT EXISTS idx_risk_transfer_id ON risk.validations(transfer_id);
