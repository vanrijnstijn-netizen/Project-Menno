[Unit]
Description=Monitoring Agent
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/monitoring-agent
ExecStart=/usr/bin/python3 /opt/monitoring-agent/agent.py

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target