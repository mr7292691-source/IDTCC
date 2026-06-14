"""Delivery channel adapters — SMS / WhatsApp / Email / Push / IVR voice.

Every channel resolves the citizen's contact through the privacy vault (never
from the analytic twin) and returns a `DeliveryReceipt`. Default mode is
`dry_run` — sends are *simulated* and audited, so the demo and tests never hit a
paid gateway or leak a real number. Wiring a real provider (Twilio / Gupshup) is
a single method body per channel.

SMS and IVR are flagged `offline_safe=True`: they reach a basic phone with no
internet — the channels that matter when the network is down.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from app.core.privacy.vault import mask, resolve_contact


class Channel(ABC):
    name: str = "base"
    offline_safe: bool = False

    @abstractmethod
    def _transmit(self, contact: str, body: str) -> str:
        """Return a provider message id (or a simulated one in dry_run)."""

    def send(self, pii_token: str, body: str, *, role: str = "dm_authority",
             dry_run: bool = True) -> Dict[str, object]:
        contact_rec = resolve_contact(pii_token, role=role, purpose="disaster_alert")
        if contact_rec is None:
            return {"channel": self.name, "status": "denied", "token": mask(pii_token)}
        contact = contact_rec.get("email" if self.name == "email" else "phone", "")
        if dry_run:
            msg_id = f"sim-{self.name}-{int(time.time()*1000)%100000}"
            status = "simulated"
        else:
            msg_id = self._transmit(contact, body)
            status = "sent"
        return {
            "channel": self.name, "status": status, "message_id": msg_id,
            "to": mask(contact), "chars": len(body), "offline_safe": self.offline_safe,
        }


class SMSChannel(Channel):
    name, offline_safe = "sms", True
    def _transmit(self, contact, body):  # pragma: no cover - provider stub
        # e.g. twilio.messages.create(to=contact, body=body)
        return f"sms-{hash(contact) & 0xffff}"


class WhatsAppChannel(Channel):
    name = "whatsapp"
    def _transmit(self, contact, body):  # pragma: no cover
        return f"wa-{hash(contact) & 0xffff}"


class EmailChannel(Channel):
    name = "email"
    def _transmit(self, contact, body):  # pragma: no cover
        return f"em-{hash(contact) & 0xffff}"


class PushChannel(Channel):
    name = "push"
    def _transmit(self, contact, body):  # pragma: no cover
        return f"ps-{hash(contact) & 0xffff}"


class VoiceChannel(Channel):
    """IVR text-to-speech call in the citizen's preferred language — the channel
    for elderly / visually-impaired citizens with no smartphone."""
    name, offline_safe = "voice", True
    def _transmit(self, contact, body):  # pragma: no cover
        return f"ivr-{hash(contact) & 0xffff}"


_REGISTRY = {c.name: c() for c in
             (SMSChannel, WhatsAppChannel, EmailChannel, PushChannel, VoiceChannel)}


def get_channel(name: str) -> Optional[Channel]:
    return _REGISTRY.get(name)


def available_channels() -> List[str]:
    return list(_REGISTRY)
