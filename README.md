# Infra Insight

AI-powered DevOps dashboard — szerver metrika monitoring + Qwen AI elemzés, OCI hosted.

**Élő demo:** [infra.istvanszechenyi.uk](https://infra.istvanszechenyi.uk)

---

## Stack

| Réteg | Technológia |
|---|---|
| Backend | FastAPI (Python) + psutil |
| AI | Alibaba Qwen API (qwen-plus) — DevOps elemzés |
| Frontend | Astro (statikus build) |
| Reverse proxy | Caddy (auto HTTPS / Let's Encrypt) |
| Hosting | Oracle Cloud Always Free AMD VM |
| IaC | OpenTofu (Terraform) — lásd: [portfolio-infra](https://github.com/gaiagent0/portfolio-infra) |

---

## Architektúra

```
User → infra.istvanszechenyi.uk
         ↓ HTTPS (Caddy + Let's Encrypt)
       OCI AMD VM (Always Free)           ← ugyanaz a VM mint hu-ai-chat!
         ↓ reverse proxy → 127.0.0.1:8001
       FastAPI (uvicorn)
         ├── GET /api/metrics  → psutil: CPU, RAM, disk, network, uptime
         └── POST /api/analyze → Qwen AI elemzi a metrikákat, javaslatokat ad
```

### VM-en futó servicek (Caddy megosztás)

```
OCI AMD VM
  ├── hu-ai-chat   → port 8000  → chat.istvanszechenyi.uk
  └── infra-insight → port 8001 → infra.istvanszechenyi.uk
```

Az `infra-insight` figyeli azt a VM-et, amin mindkét app fut.
A Caddy konfigurációt az `infra-insight/deploy/setup.sh` írja ki — ez konfigurálja **mindkét** domaint egyszerre.

**Fontos:** ha `hu-ai-chat`-et telepíted először, az `infra-insight` setup.sh felülírja a Caddyfile-t és mindkét domaint beállítja. Ha fordított sorrendben telepítesz, manuálisan kell hozzáadni a `chat.*` blokkot.

---

## Függőségek

Ez a repo az OCI infrastruktúrára épül:

```
portfolio-infra  →  OCI VM létrehozása (Terraform/OpenTofu)
     ↓
infra-insight    →  deploy/setup.sh futtatása az új VM-en
     ↑
hu-ai-chat       →  szintén ugyanezen a VM-en fut (Caddy megosztás)
```

**Ajánlott telepítési sorrend:**
1. `portfolio-infra` → VM provisionálás
2. `hu-ai-chat` deploy (setup.sh)
3. `infra-insight` deploy (setup.sh) — ez írja ki a végleges Caddyfile-t mindkét domainnel

---

## Lokális fejlesztés (laptop)

### Előfeltételek

- Python 3.11+
- Node.js 18+
- Alibaba DashScope API key: [dashscope.aliyun.com](https://dashscope.aliyun.com)

### Backend indítása

```bash
git clone https://github.com/gaiagent0/infra-insight.git
cd infra-insight

# Python venv
python3 -m venv backend/.venv
source backend/.venv/bin/activate          # Windows: backend\.venv\Scripts\activate

# Függőségek
pip install -r backend/requirements.txt

# API key beállítása
echo "DASHSCOPE_API_KEY=sk-..." > .env
# vagy Windows PowerShell:
# "DASHSCOPE_API_KEY=sk-..." | Out-File .env

# Backend indítása
cd backend
uvicorn main:app --reload --host 127.0.0.1 --port 8001
# → http://127.0.0.1:8001/api/metrics
# → http://127.0.0.1:8001/health
```

### Frontend indítása (fejlesztési módban)

```bash
cd frontend
npm install
npm run dev
# → http://localhost:4321
```

> **Megjegyzés:** lokálisan a frontend a `127.0.0.1:8001`-re hív, de a `main.py` CORS-ban csak `https://infra.istvanszechenyi.uk` van engedélyezve. Lokális fejlesztéshez add hozzá a `http://localhost:4321`-et:
>
> ```python
> # backend/main.py — ideiglenesen fejlesztéshez:
> allow_origins=["https://infra.istvanszechenyi.uk", "http://localhost:4321"],
> ```

### API végpontok tesztelése

```bash
# Metrikák lekérése
curl http://127.0.0.1:8001/api/metrics

# AI elemzés kérése
curl -X POST http://127.0.0.1:8001/api/analyze \
  -H "Content-Type: application/json" \
  -d '{"metrics": {"cpu": 85, "memory": "7.2/8 GB"}, "question": "Kritikus-e az állapot?"}'
```

---

## OCI deploy (első telepítés)

> Előfeltétel: a VM már létezik (`portfolio-infra` után).

```bash
# 1. SSH az OCI VM-re
ssh ubuntu@<OCI_VM_IP>

# 2. API key beállítása
echo "DASHSCOPE_API_KEY=sk-..." > ~/.env.infra-insight

# 3. Deploy script futtatása
curl -fsSL https://raw.githubusercontent.com/gaiagent0/infra-insight/main/deploy/setup.sh | bash
# vagy:
git clone https://github.com/gaiagent0/infra-insight.git
bash infra-insight/deploy/setup.sh
```

A setup.sh elvégzi:
1. `apt` frissítés, Python + Node.js + Caddy telepítés
2. Repo klónozás / git pull
3. Python venv + pip install
4. Frontend build (`npm run build`)
5. systemd service beállítás (`infra-insight.service`, port 8001)
6. Caddyfile kiírása — **mindkét domain** (`chat.*` + `infra.*`)
7. Caddy újraindítás

### Frissítés (már telepített VM-en)

```bash
ssh ubuntu@<OCI_VM_IP>
cd ~/infra-insight && git pull
source backend/.venv/bin/activate && pip install -r backend/requirements.txt
cd frontend && npm install && npm run build && cd ..
sudo systemctl restart infra-insight
```

---

## Környezeti változók

| Változó | Hol kell | Leírás |
|---|---|---|
| `DASHSCOPE_API_KEY` | `~/.env.infra-insight` (VM) vagy `.env` (lokális) | Alibaba DashScope API kulcs |

Az API key beszerzése: [Alibaba Cloud Console → DashScope → API Keys](https://dashscope.console.aliyun.com/apiKey)

---

## Kapcsolódó repók

| Repo | Kapcsolat |
|---|---|
| [portfolio-infra](https://github.com/gaiagent0/portfolio-infra) | OCI VM provisionálás — **előfeltétel** |
| [hu-ai-chat](https://github.com/gaiagent0/hu-ai-chat) | Ugyanazon a VM-en fut, Caddy megosztással |

---

## Licensz

MIT
