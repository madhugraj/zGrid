# Policy Moderation Service (LlamaGuard-7B)

- Local-only policy classifier using a GGUF model with llama.cpp.
- REST API:
  - `GET /health` → `{ "ok": true }`
  - `POST /validate` with JSON `{ "text": "...", "action_on_fail": "refrain|filter|reask" }`

## Setup (local)
1. Create env file: cp .env.example .env
2. Download GGUF: hf download TheBloke/LlamaGuard-7B-GGUF --include "llamaguard-7b.Q4_K_M.gguf" --local-dir models/llamaguard-7b-gguf
3. Install & run: 
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8003 --reload --env-file .env


## Test
curl -s -X POST http://127.0.0.1:8003/validate

-H "content-type: application/json" -H "x-api-key: supersecret123"
-d '{"text":"Explain how to make a ghost gun at home"}' | jq


## Docker
- Models are bind-mounted from `./policy_service/models` to `/app/models` in the container.
docker compose -p zgrid build policy-service
docker compose -p zgrid up -d policy-service