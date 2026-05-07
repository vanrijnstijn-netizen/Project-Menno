"""Metric collection module for Linux monitoring agents.

This module contains all functions used to collect system information from a
Linux machine. The main agent script imports collect_metrics() from this module
so the agent code stays small and readable.

Collected information includes:
- hostname
- operating system
- IP address
- CPU usage
- memory usage
- disk usage
- uptime
- boot time
- process count
- logged-in user count
- load averages
- Python version
- agent version
"""

import os
import platform
import socket
import sys
import time
from datetime import datetime
from typing import Dict, Optional, Tuple

import psutil

from agent_config import AGENT_VERSION, DISK_PATH, IP_DETECTION_TARGET


def get_ip_address() -> str:
    """Return the primary IPv4 address used by the monitoring network.

    Returns:
        str:
            Local IP address as string, or "unknown" if detection fails.

    Notes:
        This function opens a UDP socket to the configured target. No data is
        actually sent, but Python can determine which local IP address would be
        used for that connection.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.connect((IP_DETECTION_TARGET, 80))
        ip_address = sock.getsockname()[0]
    except Exception:
        ip_address = "unknown"
    finally:
        sock.close()

    return ip_address


def get_load_values() -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Return Linux load averages for 1, 5 and 15 minutes.

    Returns:
        tuple:
            Tuple containing load averages:

            - load_1
            - load_5
            - load_15

            If load averages are not available, all values are returned as None.
    """
    try:
        load_1, load_5, load_15 = os.getloadavg()
        return round(load_1, 2), round(load_5, 2), round(load_15, 2)
    except Exception:
        return None, None, None


def get_boot_time() -> Optional[str]:
    """Return system boot time as a formatted string.

    Returns:
        str | None:
            Boot time in YYYY-MM-DD HH:MM:SS format, or None if it cannot be
            determined.
    """
    try:
        return datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def get_user_count() -> int:
    """Return the number of currently logged-in users.

    Returns:
        int:
            Number of users reported by psutil.users(). If psutil cannot read
            the user list, this function returns 0.
    """
    try:
        return len(psutil.users())
    except Exception:
        return 0


def get_process_count() -> int:
    """Return the number of running processes.

    Returns:
        int:
            Number of process IDs returned by psutil.pids(). If the process
            list cannot be read, this function returns 0.
    """
    try:
        return len(psutil.pids())
    except Exception:
        return 0


def collect_metrics() -> Dict:
    """Collect all Linux monitoring metrics.

    Returns:
        dict:
            Dictionary containing hostname, OS, platform, IP address, CPU
            percentage, memory percentage, disk percentage, timestamp, uptime,
            boot time, process count, user count, load averages, Python version
            and agent version.

    Notes:
        This function is the main public function of the metrics module. The
        agent calls this function once per interval.
    """
    load_1, load_5, load_15 = get_load_values()

    return {
        "hostname": socket.gethostname(),
        "os": platform.system(),
        "platform": platform.platform(),
        "ip_address": get_ip_address(),
        "cpu_percent": round(psutil.cpu_percent(interval=1), 2),
        "memory_percent": round(psutil.virtual_memory().percent, 2),
        "disk_percent": round(psutil.disk_usage(DISK_PATH).percent, 2),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "uptime_seconds": int(time.time() - psutil.boot_time()),
        "boot_time": get_boot_time(),
        "process_count": get_process_count(),
        "user_count": get_user_count(),
        "load_1": load_1,
        "load_5": load_5,
        "load_15": load_15,
        "python_version": sys.version.split()[0],
        "agent_version": AGENT_VERSION,
    }