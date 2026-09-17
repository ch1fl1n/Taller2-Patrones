-- ============================================================
-- SEED: Cuentas de prueba para el taller NovaBank
-- ============================================================

INSERT INTO accounts.accounts (account_code, owner_name, balance) VALUES
  ('ACC-001', 'Carlos Mendoza',    50000.00),
  ('ACC-002', 'Laura Patiño',      30000.00),
  ('ACC-003', 'NovaBank Reserve', 1000000.00)
ON CONFLICT (account_code) DO NOTHING;
