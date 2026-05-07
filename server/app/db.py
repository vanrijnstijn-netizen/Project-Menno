"""Database module for the monitoring web application.

This module contains all SQLite database logic for the monitoring dashboard.

Responsibilities:
- create the data directory
- open SQLite connections
- create the agent_metrics table
- insert monitoring data
- clean old rows per agent
- return table data for the dashboard
- return graph data for Plotly pages

Keeping this code in a separate module keeps routes.py smaller and easier to
understand.
"""

import os
import sqlite3
from typing import Dict, List

from config import DATA_DIR, DB_FILE, MAX_STORED_ROWS_PER_AGENT


def ensure_data_dir() -> None:
    """Create the data directory if it does not exist.

    The SQLite database file is stored inside DATA_DIR. This function makes
    sure that directory exists before opening the database.
    """
    os.makedirs(DATA_DIR, exist_ok=True)


def get_db() -> sqlite3.Connection:
    """Return a SQLite database connection.

    The connection uses sqlite3.Row as row factory. This allows rows to be
    accessed like dictionaries, for example row["hostname"].

    Returns:
        sqlite3.Connection:
            Open database connection.

    Notes:
        The caller is responsible for closing the connection.
    """
    ensure_data_dir()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create required database tables if they do not exist.

    This function is called during application startup. It creates the
    agent_metrics table that stores all received monitoring data.

    Returns:
        None
    """
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS agent_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname TEXT NOT NULL,
            os TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            cpu_percent REAL NOT NULL,
            memory_percent REAL NOT NULL,
            disk_percent REAL NOT NULL,
            timestamp TEXT NOT NULL,
            platform TEXT,
            uptime_seconds INTEGER,
            boot_time TEXT,
            process_count INTEGER,
            user_count INTEGER,
            load_1 REAL,
            load_5 REAL,
            load_15 REAL,
            python_version TEXT,
            agent_version TEXT
        )
    """)

    conn.commit()
    conn.close()


def cleanup_old_rows_for_agent(hostname: str) -> None:
    """Keep only the latest configured number of rows for one hostname.

    Args:
        hostname:
            Hostname of the agent for which old rows should be removed.

    Returns:
        None

    Notes:
        The maximum number of stored rows per agent is configured with
        MAX_STORED_ROWS_PER_AGENT.
    """
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM agent_metrics
        WHERE hostname = ?
          AND id NOT IN (
              SELECT id
              FROM agent_metrics
              WHERE hostname = ?
              ORDER BY id DESC
              LIMIT ?
          )
    """, (hostname, hostname, MAX_STORED_ROWS_PER_AGENT))

    conn.commit()
    conn.close()


def insert_metric(data: Dict) -> None:
    """Insert one monitoring metric record into the database.

    Args:
        data:
            Dictionary containing monitoring values from one agent. Expected
            keys include hostname, os, ip_address, cpu_percent, memory_percent,
            disk_percent and timestamp. Optional keys such as load average and
            uptime are also stored if present.

    Returns:
        None

    Notes:
        After inserting the new row, this function calls
        cleanup_old_rows_for_agent() to prevent the database from growing
        indefinitely.
    """
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO agent_metrics (
            hostname,
            os,
            ip_address,
            cpu_percent,
            memory_percent,
            disk_percent,
            timestamp,
            platform,
            uptime_seconds,
            boot_time,
            process_count,
            user_count,
            load_1,
            load_5,
            load_15,
            python_version,
            agent_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("hostname"),
        data.get("os"),
        data.get("ip_address"),
        data.get("cpu_percent"),
        data.get("memory_percent"),
        data.get("disk_percent"),
        data.get("timestamp"),
        data.get("platform"),
        data.get("uptime_seconds"),
        data.get("boot_time"),
        data.get("process_count"),
        data.get("user_count"),
        data.get("load_1"),
        data.get("load_5"),
        data.get("load_15"),
        data.get("python_version"),
        data.get("agent_version"),
    ))

    conn.commit()
    conn.close()

    hostname = data.get("hostname")
    if hostname:
        cleanup_old_rows_for_agent(hostname)


def get_grouped_metrics(max_rows_per_agent: int) -> Dict[str, List[Dict]]:
    """Return latest records grouped by hostname.

    Args:
        max_rows_per_agent:
            Maximum number of rows to return for each hostname.

    Returns:
        dict:
            Dictionary where each key is a hostname and each value is a list of
            metric rows represented as dictionaries.

    Example:
        {
            "client1": [{...}, {...}],
            "client2": [{...}]
        }
    """
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT DISTINCT hostname FROM agent_metrics ORDER BY hostname")
    hostnames = [row["hostname"] for row in cur.fetchall()]

    grouped = {}

    for hostname in hostnames:
        cur.execute("""
            SELECT *
            FROM agent_metrics
            WHERE hostname = ?
            ORDER BY id DESC
            LIMIT ?
        """, (hostname, max_rows_per_agent))

        grouped[hostname] = [dict(row) for row in cur.fetchall()]

    conn.close()
    return grouped


def get_graph_data() -> Dict[str, List[Dict]]:
    """Return graph-ready data grouped by hostname.

    Returns:
        dict:
            Dictionary where each key is a hostname and each value is a list of
            records ordered from oldest to newest.

    Notes:
        This function is used by the Plotly pages for CPU, RAM and storage.
    """
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT DISTINCT hostname FROM agent_metrics ORDER BY hostname")
    hostnames = [row["hostname"] for row in cur.fetchall()]

    graph_data = {}

    for hostname in hostnames:
        cur.execute("""
            SELECT
                id,
                timestamp,
                cpu_percent,
                memory_percent,
                disk_percent,
                load_1,
                load_5,
                load_15,
                process_count,
                user_count,
                uptime_seconds
            FROM agent_metrics
            WHERE hostname = ?
            ORDER BY id ASC
        """, (hostname,))

        graph_data[hostname] = [dict(row) for row in cur.fetchall()]

    conn.close()
    return graph_data