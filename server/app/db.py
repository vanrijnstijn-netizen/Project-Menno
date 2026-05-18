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


class MetricsDatabase:
    """Manages all SQLite database operations for monitoring metrics.

    Connection details and row limits are stored in __init__ so they do not
    need to be repeated on every call. Internal helpers (_get_connection,
    _cleanup_old_rows) are private because callers only need the public methods.
    """

    def __init__(self, db_file: str, data_dir: str, max_stored_rows_per_agent: int) -> None:
        self._db_file = db_file
        self._data_dir = data_dir
        self._max_stored_rows_per_agent = max_stored_rows_per_agent

    def _get_connection(self) -> sqlite3.Connection:
        """Create the data directory if needed and return a database connection.

        Private: all public methods call this instead of opening connections
        directly.

        Returns:
            sqlite3.Connection:
                Open database connection with Row row factory.
        """
        os.makedirs(self._data_dir, exist_ok=True)
        conn = sqlite3.connect(self._db_file)
        conn.row_factory = sqlite3.Row
        return conn

    def _cleanup_old_rows(self, hostname: str) -> None:
        """Keep only the latest rows for one hostname.

        Private: called automatically by insert_metric() after every insert.
        """
        conn = self._get_connection()
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
        """, (hostname, hostname, self._max_stored_rows_per_agent))

        conn.commit()
        conn.close()

    def init(self) -> None:
        """Create required database tables if they do not exist.

        Called once during application startup.
        """
        conn = self._get_connection()
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

    def insert_metric(self, data: Dict) -> None:
        """Insert one monitoring metric record into the database.

        Args:
            data:
                Dictionary containing monitoring values from one agent.

        Notes:
            After inserting, old rows for this hostname are cleaned up
            automatically.
        """
        conn = self._get_connection()
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
            self._cleanup_old_rows(hostname)

    def get_grouped_metrics(self, max_rows: int) -> Dict[str, List[Dict]]:
        """Return latest records grouped by hostname.

        Args:
            max_rows:
                Maximum number of rows to return for each hostname.

        Returns:
            dict:
                Dictionary where each key is a hostname and each value is a
                list of metric rows represented as dictionaries.
        """
        conn = self._get_connection()
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
            """, (hostname, max_rows))

            grouped[hostname] = [dict(row) for row in cur.fetchall()]

        conn.close()
        return grouped

    def get_graph_data(self) -> Dict[str, List[Dict]]:
        """Return graph-ready data grouped by hostname.

        Returns:
            dict:
                Dictionary where each key is a hostname and each value is a
                list of records ordered from oldest to newest.
        """
        conn = self._get_connection()
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


metrics_db = MetricsDatabase(DB_FILE, DATA_DIR, MAX_STORED_ROWS_PER_AGENT)
