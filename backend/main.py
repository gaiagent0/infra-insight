from fastapi import FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from openai import OpenAI
import psutil, os, datetime

app = FastAPI(title="Infra Insight API")

# --- API Key auth ---
APP_API_KEY = os.environ["APP_API_KEY"]
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(key: str = Security(api_key_header)):
    if key != APP_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://infra.istvanszechenyi.uk"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

client = OpenAI(
    api_key=os.environ["DASHSCOPE_API_KEY"],
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)

SYSTEM_PROMPT = """Te egy senior DevOps mernok AI asszisztens vagy.
Szerver metrikakat elemzel es konkret, akciokepes javaslatokat adsz magyarul.
Legy tomer, technikai es pontos. Ha kritikus problemat latsz, emeld ki."""

class AnalyzeRequest(BaseModel):
    metrics: dict
    question: str = "Elemezd a szerver allapotat es jelezd ha beavatkozas szukseges."

@app.get("/api/metrics", dependencies=[Security(verify_api_key)])
async def get_metrics():
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net = psutil.net_io_counters()
    boot = datetime.datetime.fromtimestamp(psutil.boot_time())
    uptime = str(datetime.datetime.now() - boot).split(".")[0]
    return {
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "cpu": {"percent": cpu, "count": psutil.cpu_count()},
        "memory": {
            "total_gb": round(mem.total / 1e9, 2),
            "used_gb": round(mem.used / 1e9, 2),
            "percent": mem.percent,
        },
        "disk": {
            "total_gb": round(disk.total / 1e9, 2),
            "used_gb": round(disk.used / 1e9, 2),
            "percent": disk.percent,
        },
        "network": {
            "bytes_sent_mb": round(net.bytes_sent / 1e6, 2),
            "bytes_recv_mb": round(net.bytes_recv / 1e6, 2),
        },
        "uptime": uptime,
    }

@app.post("/api/analyze", dependencies=[Security(verify_api_key)])
async def analyze(req: AnalyzeRequest):
    metrics_str = "\n".join(f"- {k}: {v}" for k, v in req.metrics.items())
    prompt = f"Szerver metrikak:\n{metrics_str}\n\nKerdes: {req.question}"
    try:
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=600,
        )
        return {"analysis": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}

app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")
