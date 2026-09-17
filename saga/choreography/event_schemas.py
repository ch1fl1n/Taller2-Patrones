"""
saga/choreography/event_schemas.py
Definición de todos los eventos de dominio del canal Redis.

Canales (Redis Pub/Sub):
  novabank:transfer:requested
  novabank:debit:applied
  novabank:debit:failed
  novabank:risk:approved
  novabank:risk:rejected
  novabank:clearing:settled
  novabank:clearing:failed
  novabank:credit:applied
  novabank:transfer:confirmed
  novabank:transfer:compensated
  novabank:compensate:debit        ← triggerea la reversa del débito
  novabank:compensate:risk         ← triggerea la reversa de riesgo
"""

CHANNELS = {
    "TRANSFER_REQUESTED":   "novabank:transfer:requested",
    "DEBIT_APPLIED":        "novabank:debit:applied",
    "DEBIT_FAILED":         "novabank:debit:failed",
    "RISK_APPROVED":        "novabank:risk:approved",
    "RISK_REJECTED":        "novabank:risk:rejected",
    "CLEARING_SETTLED":     "novabank:clearing:settled",
    "CLEARING_FAILED":      "novabank:clearing:failed",
    "CREDIT_APPLIED":       "novabank:credit:applied",
    "TRANSFER_CONFIRMED":   "novabank:transfer:confirmed",
    "TRANSFER_COMPENSATED": "novabank:transfer:compensated",
    "COMPENSATE_DEBIT":     "novabank:compensate:debit",
    "COMPENSATE_RISK":      "novabank:compensate:risk",
    "COMPENSATE_CLEARING":  "novabank:compensate:clearing",
}
