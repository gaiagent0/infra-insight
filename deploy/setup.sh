#!/bin/bash
# Infra Insight — OCI AMD VM deploy
set -e

echo "[1/5] Update + deps..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv git nodejs npm

echo "[2/5] Clone / update repo..."
cd ~
if [ -d "infra-insight" ]; then
  cd infra-insight && git pull
else
  git clone git@github.com:gaiagent0/infra-insight.git
  cd infra-insight
fi

echo "[3/5] Backend venv..."
python3 -m venv backend/.venv
backend/.venv/bin/pip install -q -r backend/requirements.txt

echo "[4/5] Frontend build..."
cd frontend
npm install
npm run build
cd ..

echo "[5/5] Systemd service..."
sudo tee /etc/systemd/system/infra-insight.service > /dev/null <<SERVICE
[Unit]
Description=Infra Insight
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/infra-insight/backend
EnvironmentFile=/home/ubuntu/.env.infra-insight
ExecStart=/home/ubuntu/infra-insight/backend/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable infra-insight
sudo systemctl restart infra-insight

# Caddy config frissites
sudo tee /etc/caddy/Caddyfile > /dev/null <<CADDY
chat.istvanszechenyi.uk {
  reverse_proxy 127.0.0.1:8000
}

infra.istvanszechenyi.uk {
  reverse_proxy 127.0.0.1:8001
}
CADDY

sudo systemctl restart caddy
echo "Done! https://infra.istvanszechenyi.uk"
