-- ============================================================
-- MIGRATION 001: Account & Ledger Service Schema
-- Schema aislado para el servicio de cuentas y saldos
-- ============================================================

CREATE SCHEMA IF NOT EXISTS accounts;

-- Tabla principal de cuentas bancarias
CREATE TABLE IF NOT EXISTS accounts.accounts (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_code TEXT UNIQUE NOT NULL,         -- e.g. "ACC-001"
  owner_name   TEXT NOT NULL,
  balance      NUMERIC(15, 2) NOT NULL DEFAULT 0 CHECK (balance >= 0),
  is_active    BOOLEAN NOT NULL DEFAULT true,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Trigger para actualizar updated_at automáticamente
CREATE OR REPLACE FUNCTION accounts.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER accounts_updated_at
  BEFORE UPDATE ON accounts.accounts
  FOR EACH ROW EXECUTE FUNCTION accounts.update_updated_at();

-- Registro contable (ledger) de cada movimiento
-- Cada débito, crédito o reversa genera un entry
CREATE TABLE IF NOT EXISTS accounts.ledger_entries (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  transfer_id     UUID NOT NULL,             -- UUID de la transferencia (no FK entre schemas)
  account_id      UUID NOT NULL REFERENCES accounts.accounts(id),
  entry_type      TEXT NOT NULL CHECK (entry_type IN ('DEBIT', 'CREDIT', 'REVERSAL_DEBIT', 'REVERSAL_CREDIT')),
  amount          NUMERIC(15, 2) NOT NULL CHECK (amount > 0),
  balance_before  NUMERIC(15, 2) NOT NULL,
  balance_after   NUMERIC(15, 2) NOT NULL,
  status          TEXT NOT NULL DEFAULT 'APPLIED' CHECK (status IN ('APPLIED', 'REVERSED')),
  reversed_by     UUID REFERENCES accounts.ledger_entries(id),  -- apunta al entry de reversa
  notes           TEXT,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Índices para consultas frecuentes
CREATE INDEX IF NOT EXISTS idx_ledger_transfer_id ON accounts.ledger_entries(transfer_id);
CREATE INDEX IF NOT EXISTS idx_ledger_account_id  ON accounts.ledger_entries(account_id);
