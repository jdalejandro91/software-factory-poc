#!/bin/bash
set -e

# Crear unidad de servicio
cat <<EOF | sudo tee /etc/systemd/system/software-factory.service
[Unit]
Description=Software Factory POC
Requires=docker.service
After=docker.service network.target

[Service]
Type=oneshot
RemainAfterExit=yes
User=ubuntu
Group=docker
WorkingDirectory=/home/ubuntu/software-factory-poc
ExecStart=/usr/bin/docker compose up -d --remove-orphans
ExecStop=/usr/bin/docker compose down

[Install]
WantedBy=multi-user.target
EOF

# Activar servicio
sudo systemctl daemon-reload
sudo systemctl enable software-factory.service
sudo systemctl start software-factory.service || true
echo "✅ Servicio Systemd instalado y activado."
