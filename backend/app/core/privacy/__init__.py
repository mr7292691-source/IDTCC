"""Privacy-first layer — consent, tokenization, RBAC, audit.

LifeShield AI never touches Aadhaar or biometric identity. Citizens are
pseudonymous: analytic agents see only a ``citizen_id`` + features and an opaque
``pii_token``. Contact details (phone/email) are resolvable solely through the
privacy vault, gated by purpose + role, and every resolution is auditable.
"""
