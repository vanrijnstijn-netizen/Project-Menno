"""Utility functions for the monitoring web application.

This module contains helper functions that do not directly belong to routing,
database access or encryption. Currently it is used for validating decrypted
agent data before that data is stored in the database.
"""

REQUIRED_FIELDS = [
    "hostname",
    "os",
    "ip_address",
    "cpu_percent",
    "memory_percent",
    "disk_percent",
    "timestamp",
]


def validate_agent_data(data):
    """Validate decrypted agent metric data.

    Args:
        data:
            Dictionary containing monitoring metrics from an agent. This data
            should already be decrypted and signature-checked before calling
            this function.

    Returns:
        tuple:
            A tuple containing:

            - bool: True if the data is valid, False otherwise.
            - str: A message explaining the validation result.

    Example:
        >>> validate_agent_data({"hostname": "server1"})
        (False, 'Ontbrekend veld: os')
    """
    if not isinstance(data, dict):
        return False, "JSON body ontbreekt of is ongeldig"

    for field in REQUIRED_FIELDS:
        if field not in data:
            return False, f"Ontbrekend veld: {field}"

    return True, "OK"