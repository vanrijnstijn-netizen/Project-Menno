"""Security module for incoming monitoring agent data.

This module verifies and decrypts encrypted monitoring data sent by agents.

The agent does not send plain JSON metrics anymore. Instead, it sends a secure
envelope containing:

- agent_id
- timestamp
- encrypted payload
- HMAC-SHA256 signature

Security features:
- Fernet encryption for confidentiality
- HMAC-SHA256 signature for authenticity and integrity
- timestamp validation to reduce replay attacks
"""

import hashlib
import hmac
import json
import time
from typing import Dict

from cryptography.fernet import Fernet, InvalidToken

from config import (
    AGENT_ENCRYPTION_KEY,
    AGENT_HMAC_SECRET,
    AGENT_MAX_CLOCK_SKEW_SECONDS,
)


class AgentSecurityError(Exception):
    """Raised when agent authentication, signature validation or decryption fails.

    This custom exception is used so routes.py can clearly separate security
    problems from other server errors.
    """


def _require_security_config() -> None:
    """Check if the server has all required agent security secrets configured.

    Raises:
        AgentSecurityError:
            If AGENT_ENCRYPTION_KEY or AGENT_HMAC_SECRET is missing.
    """
    if not AGENT_ENCRYPTION_KEY:
        raise AgentSecurityError("AGENT_ENCRYPTION_KEY is not configured")

    if not AGENT_HMAC_SECRET:
        raise AgentSecurityError("AGENT_HMAC_SECRET is not configured")


def verify_timestamp(timestamp: int) -> None:
    """Reject requests that are too old or too far in the future.

    Args:
        timestamp:
            Unix timestamp sent by the monitoring agent.

    Raises:
        AgentSecurityError:
            If the timestamp is outside the allowed time window.
    """
    now = int(time.time())

    if abs(now - int(timestamp)) > AGENT_MAX_CLOCK_SKEW_SECONDS:
        raise AgentSecurityError("Agent timestamp outside allowed time window")


def verify_signature(agent_id: str, timestamp: int, encrypted_payload: str, signature: str) -> None:
    """Verify the HMAC-SHA256 signature sent by the agent.

    Args:
        agent_id:
            Unique ID of the sending agent.
        timestamp:
            Unix timestamp included in the message.
        encrypted_payload:
            Fernet encrypted payload as string.
        signature:
            HMAC-SHA256 signature sent by the agent.

    Raises:
        AgentSecurityError:
            If the calculated signature does not match the received signature.

    Notes:
        hmac.compare_digest() is used to compare signatures safely.
    """
    _require_security_config()

    message = f"{agent_id}.{timestamp}.{encrypted_payload}".encode("utf-8")

    expected_signature = hmac.new(
        AGENT_HMAC_SECRET.encode("utf-8"),
        message,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        raise AgentSecurityError("Invalid agent signature")


def decrypt_payload(encrypted_payload: str) -> Dict:
    """Decrypt the Fernet encrypted payload and return the JSON data.

    Args:
        encrypted_payload:
            Fernet token as string.

    Returns:
        dict:
            Dictionary containing the original monitoring metrics.

    Raises:
        AgentSecurityError:
            If the payload cannot be decrypted or parsed as JSON.
    """
    _require_security_config()

    try:
        fernet = Fernet(AGENT_ENCRYPTION_KEY.encode("utf-8"))
        decrypted = fernet.decrypt(encrypted_payload.encode("utf-8"))
        return json.loads(decrypted.decode("utf-8"))

    except InvalidToken as exc:
        raise AgentSecurityError("Invalid encrypted payload") from exc

    except Exception as exc:
        raise AgentSecurityError(f"Could not decrypt payload: {exc}") from exc


def decode_secure_agent_request(envelope: Dict) -> Dict:
    """Verify, decrypt and return the original agent metric payload.

    Args:
        envelope:
            Dictionary containing agent_id, timestamp, payload and signature.

    Returns:
        dict:
            Decrypted monitoring payload as dictionary.

    Raises:
        AgentSecurityError:
            If required fields are missing, the timestamp is invalid, the
            signature does not match, or decryption fails.

    Example envelope:
        {
            "agent_id": "linux-agent-01",
            "timestamp": 1234567890,
            "payload": "encrypted-fernet-token",
            "signature": "hmac-sha256-hex"
        }
    """
    required_fields = ["agent_id", "timestamp", "payload", "signature"]

    for field in required_fields:
        if field not in envelope:
            raise AgentSecurityError(f"Missing secure envelope field: {field}")

    agent_id = str(envelope["agent_id"])
    timestamp = int(envelope["timestamp"])
    encrypted_payload = str(envelope["payload"])
    signature = str(envelope["signature"])

    verify_timestamp(timestamp)
    verify_signature(agent_id, timestamp, encrypted_payload, signature)

    payload = decrypt_payload(encrypted_payload)
    payload["agent_id"] = agent_id

    return payload