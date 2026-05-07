"""Secure transport module for the Windows monitoring agent.

This module handles encryption and digital signing of monitoring data before it
is sent to the server.

The main agent script should not need to know how Fernet or HMAC work. It only
calls build_secure_envelope(payload).
"""

import hashlib
import hmac
import json
import time
from typing import Dict

from cryptography.fernet import Fernet

from agent_config import AGENT_ID, AGENT_ENCRYPTION_KEY, AGENT_HMAC_SECRET


def encrypt_payload(payload: Dict) -> str:
    """Encrypt a monitoring payload with Fernet.

    Args:
        payload:
            Dictionary containing monitoring metrics.

    Returns:
        str:
            Encrypted Fernet token as a string.

    Notes:
        The payload is first converted to JSON and then encrypted. The server
        uses the same Fernet key to decrypt it.
    """
    fernet = Fernet(AGENT_ENCRYPTION_KEY.encode("utf-8"))
    raw_payload = json.dumps(payload).encode("utf-8")
    return fernet.encrypt(raw_payload).decode("utf-8")


def sign_message(agent_id: str, timestamp: int, encrypted_payload: str) -> str:
    """Create a HMAC-SHA256 signature for the encrypted payload.

    Args:
        agent_id:
            Unique ID of the Windows agent.
        timestamp:
            Unix timestamp used in the secure envelope.
        encrypted_payload:
            Fernet encrypted payload.

    Returns:
        str:
            HMAC-SHA256 signature as hexadecimal string.

    Notes:
        The server calculates the same signature and compares it with the
        received signature. If they do not match, the request is rejected.
    """
    message = f"{agent_id}.{timestamp}.{encrypted_payload}".encode("utf-8")

    return hmac.new(
        AGENT_HMAC_SECRET.encode("utf-8"),
        message,
        hashlib.sha256
    ).hexdigest()


def build_secure_envelope(payload: Dict) -> Dict:
    """Build the encrypted and signed JSON request body for the server.

    Args:
        payload:
            Plain monitoring metrics collected by the Windows agent.

    Returns:
        dict:
            Secure envelope containing:

            - agent_id
            - timestamp
            - encrypted payload
            - signature
    """
    timestamp = int(time.time())
    encrypted_payload = encrypt_payload(payload)
    signature = sign_message(AGENT_ID, timestamp, encrypted_payload)

    return {
        "agent_id": AGENT_ID,
        "timestamp": timestamp,
        "payload": encrypted_payload,
        "signature": signature,
    }