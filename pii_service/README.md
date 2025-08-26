# PII Protection Microservice

A containerized FastAPI microservice for detecting and redacting Personally Identifiable Information (PII) using Presidio and GLiNER models.

## Features

- **Multi-engine PII Detection**: Uses both Microsoft Presidio and GLiNER for comprehensive PII detection
- **Configurable Redaction**: Customizable placeholders and thresholds for different PII types
- **API Key Authentication**: Secure access with configurable API keys
- **CORS Support**: Pre-configured for web application integration
- **Health Monitoring**: Built-in health check endpoint
- **Containerized**: Ready-to-deploy Docker container

## Supported PII Types

- Email addresses
- Phone numbers
- Credit card numbers
- Social Security Numbers (US)
- Aadhaar numbers (India)
- PAN numbers (India)
- Person names
- Locations
- Organizations
- IP addresses
- Passport numbers

## Quick Start

### Using Docker Compose (Recommended)

1. **Build and start the service:**
   ```bash
   docker-compose up --build -d
   ```

2. **Check service health:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Test PII detection:**
   ```bash
   curl -X POST "http://localhost:8000/validate" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: supersecret123" \
     -d '{
       "text": "My email is john.doe@example.com and my phone is +1-555-123-4567"
     }'
   ```

### Using Docker directly

1. **Build the image:**
   ```bash
   cd pii_service
   docker build -t pii-service .
   ```

2. **Run the container:**
   ```bash
   docker run -d \
     --name pii-protection-service \
     -p 8000:8000 \
     -e PII_API_KEYS=supersecret123,piievalyavar \
     -e CORS_ALLOWED_ORIGINS=https://preview--zgrid-feature-flow.lovable.app \
     -v $(pwd)/models:/app/models:ro \
     pii-service
   ```

## API Documentation

### Authentication

The service supports two authentication methods:

1. **X-API-Key header:**
   ```bash
   curl -H "X-API-Key: supersecret123" ...
   ```

2. **Authorization Bearer token:**
   ```bash
   curl -H "Authorization: Bearer supersecret123" ...
   ```

### Endpoints

#### Health Check
```
GET /health
```

**Response:**
```json
{
  "ok": true
}
```

#### PII Validation and Redaction
```
POST /validate
```

**Headers:**
- `Content-Type: application/json`
- `X-API-Key: <your-api-key>` or `Authorization: Bearer <your-api-key>`

**Request Body:**
```json
{
  "text": "Text to analyze for PII",
  "entities": ["EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON"],
  "gliner_labels": ["person", "location", "organization"],
  "gliner_threshold": 0.45,
  "thresholds": {
    "EMAIL_ADDRESS": 0.3,
    "PERSON": 0.35
  },
  "return_spans": true,
  "language": "en"
}
```

**Parameters:**
- `text` (required): Text to analyze
- `entities` (optional): List of PII types to detect
- `gliner_labels` (optional): GLiNER semantic labels to use
- `gliner_threshold` (optional): Confidence threshold for GLiNER
- `thresholds` (optional): Per-entity confidence thresholds
- `return_spans` (optional): Whether to return detected spans (default: true)
- `language` (optional): Language code (default: "en")

**Response:**
```json
{
  "status": "fixed",
  "redacted_text": "My email is [EMAIL] and my phone is [PHONE]",
  "entities": [
    {
      "type": "EMAIL_ADDRESS",
      "value": "john.doe@example.com",
      "start": 12,
      "end": 32,
      "score": 0.95,
      "replacement": "[EMAIL]"
    },
    {
      "type": "PHONE_NUMBER",
      "value": "+1-555-123-4567",
      "start": 50,
      "end": 65,
      "score": 0.90,
      "replacement": "[PHONE]"
    }
  ],
  "steps": [
    {
      "name": "presidio",
      "passed": true,
      "details": {"count": 2}
    },
    {
      "name": "gliner",
      "passed": true,
      "details": {"count": 0, "labels": ["person", "location"]}
    }
  ],
  "reasons": ["PII redacted"]
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PRESIDIO_LANGUAGE` | Language for Presidio analysis | `en` |
| `SPACY_MODEL` | spaCy model to use | `en_core_web_lg` |
| `GLINER_LOCAL_DIR` | Local path to GLiNER model | `/app/models/gliner_small-v2.1` |
| `GLINER_THRESHOLD` | Default GLiNER confidence threshold | `0.45` |
| `ENTITIES` | Comma-separated list of PII types to detect | See defaults |
| `ENTITY_THRESHOLDS` | JSON object with per-entity thresholds | `{}` |
| `PLACEHOLDERS` | JSON object with replacement placeholders | See defaults |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed origins | `*` |
| `PII_API_KEYS` | Comma-separated list of valid API keys | Empty (auth disabled) |

### Default Entity Types
```
EMAIL_ADDRESS,PHONE_NUMBER,CREDIT_CARD,US_SSN,PERSON,LOCATION,IN_AADHAAR,IN_PAN
```

### Default Placeholders
```json
{
  "DEFAULT": "[REDACTED]",
  "EMAIL_ADDRESS": "[EMAIL]",
  "PHONE_NUMBER": "[PHONE]",
  "CREDIT_CARD": "[CARD]",
  "US_SSN": "[SSN]",
  "PERSON": "[PERSON]",
  "LOCATION": "[LOCATION]",
  "IN_AADHAAR": "[AADHAAR]",
  "IN_PAN": "[PAN]"
}
```

## Integration with UI

### Frontend Integration Example

```javascript
// Example integration for your UI at https://preview--zgrid-feature-flow.lovable.app/
async function detectPII(text) {
  try {
    const response = await fetch('http://localhost:8000/validate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'supersecret123'
      },
      body: JSON.stringify({
        text: text,
        return_spans: true
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const result = await response.json();
    return result;
  } catch (error) {
    console.error('PII detection failed:', error);
    throw error;
  }
}

// Usage in PII Protection card click handler
document.getElementById('pii-protection-card').addEventListener('click', async () => {
  const inputText = document.getElementById('text-input').value;
  
  if (!inputText.trim()) {
    alert('Please enter some text to analyze');
    return;
  }
  
  try {
    const result = await detectPII(inputText);
    
    // Display results
    document.getElementById('redacted-text').textContent = result.redacted_text;
    document.getElementById('pii-count').textContent = result.entities.length;
    
    // Show detected entities
    const entitiesList = document.getElementById('entities-list');
    entitiesList.innerHTML = result.entities.map(entity => 
      `<li>${entity.type}: ${entity.value} (confidence: ${entity.score.toFixed(2)})</li>`
    ).join('');
    
  } catch (error) {
    alert('Failed to analyze text for PII. Please try again.');
  }
});
```

## Monitoring and Logs

### View logs:
```bash
docker-compose logs -f pii-service
```

### Monitor health:
```bash
# Check if service is healthy
docker-compose ps

# Manual health check
curl http://localhost:8000/health
```

## Troubleshooting

### Common Issues

1. **Service fails to start:**
   - Check if port 8000 is available
   - Verify the GLiNER model files are present in `models/` directory
   - Check Docker logs: `docker-compose logs pii-service`

2. **Authentication errors:**
   - Verify API key is set in environment variables
   - Check the `X-API-Key` header is included in requests

3. **CORS errors:**
   - Update `CORS_ALLOWED_ORIGINS` to include your frontend domain
   - Restart the service after configuration changes

4. **Model loading issues:**
   - Ensure the `models/gliner_small-v2.1/` directory contains all model files
   - Check that Git LFS has properly downloaded the model files

### Performance Optimization

- The service includes model caching for better performance
- First request may be slower due to model loading
- Consider using a reverse proxy (nginx) for production deployments
- Monitor memory usage as ML models can be memory-intensive

## Production Deployment

For production deployment, consider:

1. **Use a reverse proxy** (nginx, Traefik)
2. **Enable HTTPS** with proper SSL certificates
3. **Set up monitoring** (Prometheus, Grafana)
4. **Configure log aggregation** (ELK stack, Fluentd)
5. **Use secrets management** for API keys
6. **Set resource limits** in Docker Compose
7. **Enable container restart policies**

Example production docker-compose.yml additions:
```yaml
services:
  pii-service:
    # ... existing configuration
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2'
        reservations:
          memory: 2G
          cpus: '1'
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
