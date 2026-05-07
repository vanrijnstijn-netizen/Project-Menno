"""Database module for the monitoring web application.

This module contains all SQLite database logic:
- opening the database
- creating tables
- inserting monitoring records
- reading dashboard and graph data
- cleaning old rows per agent
"""

import os
import sqlite3
from typing import Dict, List

from config import DATA_DIR, DB_FILE, MAX_STORED_ROWS_PER_AGENT


def ensure_data_dir() -> None:
    """Create the data directory if it does not exist."""
    os.makedirs(DATA_DIR, exist_ok=True)


def get_db() -> sqlite3.Connection:
    """Return a SQLite connection with row_factory enabled."""
    ensure_data_dir()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the agent_metrics table if it does not exist."""
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
    """Keep only the latest configured number of rows for one hostname."""
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
    """Insert one monitoring metric record into the database."""
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
    """Return latest records grouped by hostname for the dashboard table."""
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
    """Return graph-ready data grouped by hostname."""
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