"""Main Windows monitoring agent.

This script is intentionally kept small.

It imports:
- collect_metrics() from metrics.py
- build_secure_envelope() from secure_transport.py

The result is a modular Windows agent where measurement logic and security logic
are split into separate files.
"""

import logging
import os
import time

import requests
import urllib3

from agent_config import SERVER_URL, INTERVAL_SECONDS, LOG_FILE, VERIFY_TLS
from metrics import collect_metrics
from secure_transport import build_secure_envelope

if not VERIFY_TLS:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)


def main() -> None:
    """Run the secure Windows monitoring agent loop.

    The loop performs these steps:

    1. Collect Windows system metrics.
    2. Encrypt and sign the metrics.
    3. Send the secure envelope to the server.
    4. Log success or failure.
    5. Wait for the configured interval.

    Returns:
        None
    """
    print("Secure Windows agent gestart →", SERVER_URL)
    logging.info("Secure Windows agent gestart")

    while True:
        try:
            metrics = collect_metrics()
            envelope = build_secure_envelope(metrics)

            response = requests.post(
                SERVER_URL,
                json=envelope,
                timeout=5,
                verify=VERIFY_TLS
            )

            print("OK:", response.status_code, response.text)
            logging.info(
                "Versleutelde data verstuurd | status=%s | response=%s",
                response.status_code,
                response.text
            )

        except Exception as e:
            print("Fout:", e)
            logging.exception("Fout bij versturen van beveiligde data")

        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()