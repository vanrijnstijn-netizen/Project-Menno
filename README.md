# Monitoring Project

Flask monitoring dashboard met Linux agents.

## Onderdelen

- Flask webserver
- SQLite database
- Amazon OAuth login
- Plotly grafieken
- Linux monitoring agent
- Secure agent posts met Fernet encryptie en HMAC-SHA256 signature
- Eigen modules voor database, validatie, security, metrics en secure transport

## Installatie server

```bash
dnf install -y python3 python3-pip git
cd /opt
git clone <jouw-repo-url> monitoring-project

mkdir -p /opt/monitoring-web
cp -r /opt/monitoring-project/server/* /opt/monitoring-web/

cd /opt/monitoring-web
cp config.py.example config.py
pip3 install -r /opt/monitoring-project/requirements.txt