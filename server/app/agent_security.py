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


class AgentSecurityVerifier:
    """Verifies and decrypts secure envelopes sent by monitoring agents.

    All cryptographic details (Fernet, HMAC-SHA256, timestamp validation) are
    hidden behind the single public method decode_secure_agent_request(). The
    caller only needs to pass the raw envelope and receives the plain payload.
    """

    def __init__(self, encryption_key: str, hmac_secret: str, max_clock_skew: int) -> None:
        self._encryption_key = encryption_key
        self._hmac_secret = hmac_secret
        self._max_clock_skew = max_clock_skew

    def _require_security_config(self) -> None:
        """Raise AgentSecurityError if required secrets are missing.

        Private: called internally before any cryptographic operation.
        """
        if not self._encryption_key:
            raise AgentSecurityError("AGENT_ENCRYPTION_KEY is not configured")

        if not self._hmac_secret:
            raise AgentSecurityError("AGENT_HMAC_SECRET is not configured")

    def _verify_timestamp(self, timestamp: int) -> None:
        """Reject requests that are too old or too far in the future.

        Private: called internally by decode_secure_agent_request().

        Raises:
            AgentSecurityError:
                If the timestamp is outside the allowed time window.
        """
        now = int(time.time())

        if abs(now - int(timestamp)) > self._max_clock_skew:
            raise AgentSecurityError("Agent timestamp outside allowed time window")

    def _verify_signature(
        self,
        agent_id: str,
        timestamp: int,
        encrypted_payload: str,
        signature: str,
    ) -> None:
        """Verify the HMAC-SHA256 signature sent by the agent.

        Private: called internally by decode_secure_agent_request().

        Raises:
            AgentSecurityError:
                If the calculated signature does not match the received signature.
        """
        self._require_security_config()

        message = f"{agent_id}.{timestamp}.{encrypted_payload}".encode("utf-8")

        expected_signature = hmac.new(
            self._hmac_secret.encode("utf-8"),
            message,
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, signature):
            raise AgentSecurityError("Invalid agent signature")

    def _decrypt_payload(self, encrypted_payload: str) -> Dict:
        """Decrypt the Fernet encrypted payload and return the JSON data.

        Private: called internally by decode_secure_agent_request().

        Raises:
            AgentSecurityError:
                If the payload cannot be decrypted or parsed as JSON.
        """
        self._require_security_config()

        try:
            fernet = Fernet(self._encryption_key.encode("utf-8"))
            decrypted = fernet.decrypt(encrypted_payload.encode("utf-8"))
            return json.loads(decrypted.decode("utf-8"))

        except InvalidToken as exc:
            raise AgentSecurityError("Invalid encrypted payload") from exc

        except Exception as exc:
            raise AgentSecurityError(f"Could not decrypt payload: {exc}") from exc

    def decode_secure_agent_request(self, envelope: Dict) -> Dict:
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
        """
        required_fields = ["agent_id", "timestamp", "payload", "signature"]

        for field in required_fields:
            if field not in envelope:
                raise AgentSecurityError(f"Missing secure envelope field: {field}")

        agent_id = str(envelope["agent_id"])
        timestamp = int(envelope["timestamp"])
        encrypted_payload = str(envelope["payload"])
        signature = str(envelope["signature"])

        self._verify_timestamp(timestamp)
        self._verify_signature(agent_id, timestamp, encrypted_payload, signature)

        payload = self._decrypt_payload(encrypted_payload)
        payload["agent_id"] = agent_id

        return payload


security_verifier = AgentSecurityVerifier(
    AGENT_ENCRYPTION_KEY,
    AGENT_HMAC_SECRET,
    AGENT_MAX_CLOCK_SKEW_SECONDS,
)
