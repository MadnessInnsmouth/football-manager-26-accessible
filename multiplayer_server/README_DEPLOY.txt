Football Manager Quick Multiplayer VPS Deployment

Server file:
- server.py

Recommended quick deploy on Ubuntu:
1. sudo apt update
2. sudo apt install -y python3 python3-venv ufw
3. mkdir -p ~/fm_server
4. Upload/copy server.py into ~/fm_server
5. cd ~/fm_server
6. python3 -m venv .venv
7. source .venv/bin/activate
8. python server.py

Open firewall port:
- sudo ufw allow 34888/tcp
- sudo ufw enable

Systemd service example:
[Unit]
Description=Football Manager Multiplayer Server
After=network.target

[Service]
User=root
WorkingDirectory=/root/fm_server
ExecStart=/root/fm_server/.venv/bin/python /root/fm_server/server.py
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target

Then:
- sudo systemctl daemon-reload
- sudo systemctl enable fm-multiplayer
- sudo systemctl start fm-multiplayer
- sudo systemctl status fm-multiplayer
