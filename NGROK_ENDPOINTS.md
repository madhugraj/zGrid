# Public API Endpoints via ngrok

Both PII and Toxicity services are now accessible via public HTTPS URLs through ngrok tunnels.

## Service URLs

### PII Protection Service
- **Public URL**: `https://abdf3702eebc.ngrok-free.app`
- **Local URL**: `http://localhost:8000`
- **API Key**: `supersecret123` or `piievalyavar`

### Toxicity Detection Service
- **Public URL**: `https://b61c95edbd24.ngrok-free.app`
- **Local URL**: `http://localhost:8001`
- **API Key**: `supersecret123` or `toxevalyavar`

## API Usage Examples

### PII Service

#### Health Check
```bash
curl -s https://abdf3702eebc.ngrok-free.app/health
```

#### Validate Text for PII
```bash
curl -X POST https://abdf3702eebc.ngrok-free.app/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: supersecret123" \
  -d '{"text":"My name is John Doe and my email is john@example.com"}'
```

### Toxicity Service

#### Health Check
```bash
curl -s https://b61c95edbd24.ngrok-free.app/health
```

#### Validate Text for Toxicity
```bash
curl -X POST https://b61c95edbd24.ngrok-free.app/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: supersecret123" \
  -d '{"text":"This is a test message"}'
```

## Frontend Integration

For your Lovable frontend, use these public URLs instead of localhost:

```javascript
// PII Service
const piiResponse = await fetch('https://abdf3702eebc.ngrok-free.app/validate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'supersecret123'
  },
  body: JSON.stringify({ text: userInput })
});

// Toxicity Service
const toxResponse = await fetch('https://b61c95edbd24.ngrok-free.app/validate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'supersecret123'
  },
  body: JSON.stringify({ text: userInput })
});
```

## Important Notes

1. **ngrok Free Account**: These URLs are active as long as the ngrok process is running
2. **Session Management**: Both tunnels run from a single ngrok session to avoid free account limitations
3. **CORS**: Services are configured to accept requests from your Lovable preview domains
4. **Authentication**: All API requests require the `X-API-Key` header
5. **HTTPS Only**: ngrok provides HTTPS endpoints by default

## Status

- ✅ Both services are running and healthy
- ✅ ngrok tunnels are active and accessible
- ✅ CORS configured for Lovable frontend
- ✅ API authentication working
- ✅ Ready for frontend integration
