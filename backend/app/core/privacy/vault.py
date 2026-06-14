"""Privacy vault — tokenized contact resolution (no Aadhaar, DPDP-aligned).

In production this is an encrypted KMS-backed store: ``pii_token`` -> AES-GCM
ciphertext of {phone, email, name}, resolvable only with a valid role + purpose,
with every access written to the append-only audit log.

For the hackathon build it deterministically *derives* a masked, synthetic
contact from the token so the alerting pipeline is fully demoable without ever
handling real PII. The public surface (``resolve_contact`` + ``mask``) is
identical to the production contract, so swapping the backend is a one-file
change.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Dict, Optional

from app.core.logging_config import get_logger, log_event

log = get_logger("lifeshield.vault")

# Roles permitted to resolve raw contact details (least-privilege).
_ALLOWED_ROLES = {"dm_authority", "responder", "gov_admin"}


def _digits(token: str, n: int = 10) -> str:
    h = hashlib.sha256(token.encode()).hexdigest()
    num = int(h, 16)
    return str(num)[-n:].rjust(n, "0")


def mask(value: str, *, keep: int = 4) -> str:
    """Mask a contact value for display / logs, e.g. '+91 ******1234'."""
    if not value:
        return ""
    tail = value[-keep:]
    return f"{'*' * max(0, len(value) - keep)}{tail}"


def resolve_contact(
    pii_token: str,
    *,
    role: str = "dm_authority",
    purpose: str = "disaster_alert",
    audit: bool = True,
) -> Optional[Dict[str, str]]:
    """Resolve a token to a (synthetic) contact, enforcing role + audit.

    Returns None if the role is not permitted — callers must handle the deny
    rather than receive partial data. Phone is always present (SMS/IVR is the
    life-line channel); email is best-effort.
    """
    if role not in _ALLOWED_ROLES:
        if audit:
            log_event(log, logging.WARNING, "vault.access_denied",
                      token=mask(pii_token), role=role, purpose=purpose)
        return None

    phone = "+91" + _digits(pii_token, 10)
    email = f"{_digits(pii_token, 6)}@citizen.lifeshield.local"
    if audit:
        # Audit records the masked value only — never the cleartext contact.
        log_event(log, logging.INFO, "vault.resolve",
                  token=mask(pii_token), role=role, purpose=purpose,
                  phone=mask(phone))
    return {"phone": phone, "email": email}
