#!/bin/bash

echo "🚀 INSTALANDO INSTINTO CAÇADOR NO VPS..."

apt-get update -y
apt-get upgrade -y

apt-get install -y python3 python3-pip git zip unzip

mkdir -p /root/instinto
cd /root/instinto

pip3 install aiohttp aiosqlite ccxt python-telegram-bot certifi typing_extensions urllib3 yarl

cat > /etc/systemd/system/instinto.service << EOF
[Unit]
Description=Instinto Caçador
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/instinto
ExecStart=/usr/bin/python3 main_cacador.py
Restart=always
RestartSec=10
OOMScoreAdjust=-900
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable instinto

echo "✅ INSTALAÇÃO COMPLETA!"
echo "📊 Para iniciar: systemctl start instinto"
echo "📊 Para ver status: systemctl status instinto"
