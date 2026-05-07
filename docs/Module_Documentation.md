# Module Documentation

## app.agent_security

Security module for incoming monitoring agent data.

This module verifies and decrypts encrypted monitoring data sent by agents.
The payload is encrypted with Fernet and signed with HMAC-SHA256.

### Classes

#### AgentSecurityError(Exception)

Raised when agent authentication, signature validation or decryption fails.

### Functions

#### decode_secure_agent_request(envelope)

Verify, decrypt and return the original agent metric payload.

Args:

- `envelope`: Dictionary containing `agent_id`, `timestamp`, `payload` and `signature`.

Returns:

- Decrypted monitoring payload as dictionary.

Raises:

- `AgentSecurityError`: If validation, signature check or decryption fails.

---

#### decrypt_payload(encrypted_payload)

Decrypt the Fernet encrypted payload and return the JSON data.

Args:

- `encrypted_payload`: Fernet token as string.

Returns:

- Dictionary containing the original monitoring metrics.

Raises:

- `AgentSecurityError`: If the payload cannot be decrypted or parsed as JSON.

---

#### verify_signature(agent_id, timestamp, encrypted_payload, signature)

Verify the HMAC-SHA256 signature sent by the agent.

Args:

- `agent_id`: Unique ID of the sending agent.
- `timestamp`: Unix timestamp included in the message.
- `encrypted_payload`: Fernet encrypted payload as string.
- `signature`: HMAC-SHA256 signature sent by the agent.

Raises:

- `AgentSecurityError`: If the calculated signature does not match the received signature.

---

#### verify_timestamp(timestamp)

Reject requests that are too old or too far in the future.

Args:

- `timestamp`: Unix timestamp sent by the monitoring agent.

Raises:

- `AgentSecurityError`: If the timestamp is outside the allowed time window.

---

## app.db

Database module for the monitoring web application.

This module contains SQLite database logic for creating tables, inserting
metrics and reading dashboard data.

### Functions

#### ensure_data_dir()

Create the data directory if it does not exist.

Returns:

- `None`

---

#### get_db()

Return a SQLite connection with row factory enabled.

Returns:

- SQLite connection.

Notes:

- The caller is responsible for closing the connection.

---

#### init_db()

Create the `agent_metrics` table if it does not exist.

Returns:

- `None`

---

#### insert_metric(data)

Insert one monitoring metric record into the database.

Args:

- `data`: Dictionary containing monitoring metrics.

Returns:

- `None`

Notes:

- After inserting data, old rows for the same hostname are cleaned up.

---

#### cleanup_old_rows_for_agent(hostname)

Keep only the latest configured number of rows for one hostname.

Args:

- `hostname`: Hostname of the agent.

Returns:

- `None`

---

#### get_grouped_metrics(max_rows_per_agent)

Return latest records grouped by hostname for the dashboard table.

Args:

- `max_rows_per_agent`: Maximum number of rows per hostname.

Returns:

- Dictionary grouped by hostname.

---

#### get_graph_data()

Return graph-ready data grouped by hostname.

Returns:

- Dictionary grouped by hostname.

Notes:

- Used by the CPU, RAM and storage graph pages.

---

## app.utils

Utility functions for validating incoming monitoring data.

### Constants

#### REQUIRED_FIELDS

List of required fields that every decrypted agent payload must contain.

Required fields:

- `hostname`
- `os`
- `ip_address`
- `cpu_percent`
- `memory_percent`
- `disk_percent`
- `timestamp`

### Functions

#### validate_agent_data(data)

Validate decrypted agent metric data.

Args:

- `data`: Dictionary containing monitoring metrics.

Returns:

- Tuple `(is_valid, message)`.

Example:

```python
validate_agent_data({"hostname": "server1"})
# returns: (False, "Ontbrekend veld: os")