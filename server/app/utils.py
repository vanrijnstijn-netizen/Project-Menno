"""Utility module for the monitoring web application.

This module contains helper classes that do not directly belong to routing,
database access or encryption. Currently it is used for validating decrypted
agent data before that data is stored in the database.
"""

from typing import Tuple


class AgentDataValidator:
    """Validates decrypted agent metric data before it is stored.

    Required fields are defined once in __init__ so they are easy to extend
    without touching the validate() method.
    """

    def __init__(self) -> None:
        self._required_fields = [
            "hostname",
            "os",
            "ip_address",
            "cpu_percent",
            "memory_percent",
            "disk_percent",
            "timestamp",
        ]

    def validate(self, data) -> Tuple[bool, str]:
        """Validate decrypted agent metric data.

        Args:
            data:
                Dictionary containing monitoring metrics from an agent.

        Returns:
            tuple:
                A tuple containing:

                - bool: True if the data is valid, False otherwise.
                - str: A message explaining the validation result.
        """
        if not isinstance(data, dict):
            return False, "JSON body ontbreekt of is ongeldig"

        for field in self._required_fields:
            if field not in data:
                return False, f"Ontbrekend veld: {field}"

        return True, "OK"


validator = AgentDataValidator()
