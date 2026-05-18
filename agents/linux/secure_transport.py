"""Secure transport module for the Linux monitoring agent.

This module handles encryption and digital signing of monitoring data before it
is sent to the server.

The main agent script should not need to know how Fernet or HMAC work. It only
instantiates SecureTransport and calls build_secure_envelope(payload).
"""

import hashlib
import hmac
import json
import time
from typing import Dict

from cryptography.fernet import Fernet

from agent_config import AGENT_ID, AGENT_ENCRYPTION_KEY, AGENT_HMAC_SECRET


class SecureTransport:
    """Handles encryption and signing of monitoring payloads.

    All cryptographic details (Fernet, HMAC-SHA256) are hidden behind the
    single public method build_secure_envelope(). The caller only needs to
    pass a plain metrics dictionary and receives a ready-to-send envelope.
    """

    def __init__(self, agent_id: str, encryption_key: str, hmac_secret: str) -> None:
        self._agent_id = agent_id
        self._encryption_key = encryption_key
        self._hmac_secret = hmac_secret

    def _encrypt_payload(self, payload: Dict) -> str:
        """Encrypt a monitoring payload with Fernet.

        Private: callers use build_secure_envelope(), not this method directly.
        """
        fernet = Fernet(self._encryption_key.encode("utf-8"))
        raw_payload = json.dumps(payload).encode("utf-8")
        return fernet.encrypt(raw_payload).decode("utf-8")

    def _sign_message(self, timestamp: int, encrypted_payload: str) -> str:
        """Create a HMAC-SHA256 signature over agent_id, timestamp and payload.

        Private: callers use build_secure_envelope(), not this method directly.
        The server calculates the same signature and rejects the request if they
        do not match.
        """
        message = f"{self._agent_id}.{timestamp}.{encrypted_payload}".encode("utf-8")

        return hmac.new(
            self._hmac_secret.encode("utf-8"),
            message,
            hashlib.sha256,
        ).hexdigest()

    def build_secure_envelope(self, payload: Dict) -> Dict:
        """Build the encrypted and signed JSON request body for the server.

        Args:
            payload:
                Plain monitoring metrics collected by the Linux agent.

        Returns:
            dict:
                Secure envelope containing:

                - agent_id
                - timestamp
                - encrypted payload
                - signature
        """
        timestamp = int(time.time())
        encrypted_payload = self._encrypt_payload(payload)
        signature = self._sign_message(timestamp, encrypted_payload)

        return {
            "agent_id": self._agent_id,
            "timestamp": timestamp,
            "payload": encrypted_payload,
            "signature": signature,
        }
