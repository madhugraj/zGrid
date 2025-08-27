# Toxicity & Profanity Microservice (Z-Grid)

FastAPI microservice that detects & handles **toxic language** (Detoxify) and **profanity** (lexicon) locally.

## Endpoints
- `GET /health` → `{"ok": true}`
- `POST /validate` → body:
```json
{
  "text": "string",
  "mode": "sentence|text",
  "tox_threshold": 0.5,
  "labels": ["toxicity","insult","threat", "..."],
  "action_on_fail": "remove_sentences|remove_all|redact",
  "profanity_enabled": true,
  "profanity_action": "mask|remove",
  "return_spans": true
}
