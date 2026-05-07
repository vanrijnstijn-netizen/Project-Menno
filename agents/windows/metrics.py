"""Metric collection module for Windows monitoring agents.

This module contains all functions used to collect system information from a
Windows machine. The main agent script imports collect_metrics() from this
module so the agent code stays small and readable.

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
- Python version
- agent version
"""

import platform
import socket
import sys
import time
from datetime import datetime
from typing import Dict, Optional
from urllib.parse import urlparse

import psutil

from agent_config import AGENT_VERSION, SERVER_URL, DISK_PATH


def get_ip_address() -> str:
    """Return the primary IPv4 address used to reach the monitoring server.

    Returns:
        str:
            Local IP address as string, or "unknown" if detection fails.

    Notes:
        This function opens a UDP socket to the monitoring server host. No data
        is actually sent, but Python can determine which local IP address would
        be used for that connection.
    """
    parsed_url = urlparse(SERVER_URL)
    target_host = parsed_url.hostname or "192.168.178.204"

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.connect((target_host, 443))
        ip_address = sock.getsockname()[0]
    except Exception:
        ip_address = "unknown"
    finally:
        sock.close()

    return ip_address


def get_boot_time() -> Optional[str]:
    """Return Windows boot time as a formatted string.

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
            Number of users reported by psutil.users().
    """
    try:
        return len(psutil.users())
    except Exception:
        return 0


def collect_metrics() -> Dict:
    """Collect all Windows monitoring metrics.

    Returns:
        dict:
            Dictionary containing hostname, OS, platform, IP address, CPU
            percentage, memory percentage, disk percentage, timestamp, uptime,
            boot time, process count, user count, Python version and agent
            version.

    Notes:
        This function is the main public function of the metrics module. The
        agent calls this function once per interval.
    """
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
        "process_count": len(psutil.pids()),
        "user_count": get_user_count(),
        "load_1": None,
        "load_5": None,
        "load_15": None,
        "python_version": sys.version.split()[0],
        "agent_version": AGENT_VERSION,
    }