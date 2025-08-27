# zGrid Services Deployment Guide

## Overview
This guide covers how to deploy and run the PII and Toxicity services using Docker Desktop and integrate them with your UI application.

## Services Available
- **PII Service**: Port 8000 - Detects and redacts personally identifiable information
- **Toxicity Service**: Port 8001 - Detects and filters toxic/harmful content

## 🐳 Docker Desktop Setup

### Prerequisites
1. Ensure Docker Desktop is installed and running
2. Make sure you have at least 4GB RAM available for Docker
3. Ensure ports 8000 and 8001 are available

### Option 1: Using Docker Compose (Recommended for Production)

#### Step 1: Fix Docker Build Issues
The toxicity service Docker build failed due to missing OpenSSL. To fix this, update the tox_service Dockerfile:

```bash
# Add these packages to the RUN command in tox_service/Dockerfile
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    build-essential \
    pkg-config \
    libssl-dev \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && . ~/.cargo/env \
    && rm -rf /var/lib/apt/lists/*
```

#### Step 2: Build and Run with Docker Compose
```bash
# Navigate to your project directory
cd /Users/yavar/Documents/CoE/zGrid

# Build and start both services
docker-compose up --build -d

# Check if services are running
docker-compose ps

# View logs if needed
docker-compose logs pii-service
docker-compose logs tox-service

# Stop services
docker-compose down
```

### Option 2: Using Virtual Environments (Current Working Setup)

#### Step 1: Start PII Service
```bash
cd /Users/yavar/Documents/CoE/zGrid/pii_service
source ../guards/bin/activate
python -m uvicorn app:app --host 0.0.0.0 --port 8000 &
```

#### Step 2: Start Toxicity Service
```bash
cd /Users/yavar/Documents/CoE/zGrid/tox_service
source ../guards311/bin/activate
python -m uvicorn app:app --host 0.0.0.0 --port 8001 &
```

#### Step 3: Verify Services
```bash
# Check health endpoints
curl http://localhost:8000/health
curl http://localhost:8001/health
```

## 🔧 Service Configuration

### Environment Variables
Both services use environment variables for configuration:

**PII Service (.env)**:
- `PII_API_KEYS`: Comma-separated API keys for authentication
- `CORS_ALLOWED_ORIGINS`: Allowed origins for CORS
- `ENTITIES`: Types of PII to detect
- `PLACEHOLDERS`: Replacement text for detected PII

**Toxicity Service (.env)**:
- `TOX_API_KEYS`: Comma-separated API keys for authentication
- `DETOXIFY_THRESHOLD`: Threshold for toxicity detection (0.5)
- `TOX_MODE`: Processing mode (sentence/text)
- `ACTION_ON_FAIL`: Action when toxicity detected (remove_sentences/redact)

## 🌐 UI Application Integration

### API Endpoints

#### PII Service (Port 8000)
```javascript
// Health check
GET http://localhost:8000/health

// Validate and redact PII
POST http://localhost:8000/validate
Headers: {
  "Content-Type": "application/json",
  "X-API-Key": "supersecret123"  // or use Authorization: Bearer <token>
}
Body: {
  "text": "Your text content here",
  "entities": ["EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON"], // optional
  "return_spans": true // optional, default true
}
```

#### Toxicity Service (Port 8001)
```javascript
// Health check
GET http://localhost:8001/health

// Validate and filter toxicity
POST http://localhost:8001/validate
Headers: {
  "Content-Type": "application/json",
  "X-API-Key": "supersecret123"  // or use Authorization: Bearer <token>
}
Body: {
  "text": "Your text content here",
  "tox_threshold": 0.5, // optional
  "mode": "sentence", // optional: sentence or text
  "action_on_fail": "remove_sentences", // optional
  "return_spans": true // optional
}
```

### JavaScript Integration Examples

#### PII Service Integration
```javascript
async function validatePII(text) {
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
    
    const result = await response.json();
    
    if (result.status === 'fixed') {
      console.log('PII detected and redacted');
      console.log('Clean text:', result.redacted_text);
      console.log('Detected entities:', result.entities);
      return result.redacted_text;
    } else {
      console.log('No PII detected');
      return text;
    }
  } catch (error) {
    console.error('PII validation error:', error);
    return text; // Return original text on error
  }
}
```

#### Toxicity Service Integration
```javascript
async function validateToxicity(text) {
  try {
    const response = await fetch('http://localhost:8001/validate', {
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
    
    const result = await response.json();
    
    if (result.status === 'fixed') {
      console.log('Toxicity detected and filtered');
      console.log('Clean text:', result.clean_text);
      console.log('Toxic content:', result.flagged);
      return result.clean_text;
    } else {
      console.log('No toxicity detected');
      return text;
    }
  } catch (error) {
    console.error('Toxicity validation error:', error);
    return text; // Return original text on error
  }
}
```

#### Combined Validation Pipeline
```javascript
async function validateContent(text) {
  // First, remove PII
  const piiCleanText = await validatePII(text);
  
  // Then, filter toxicity
  const finalCleanText = await validateToxicity(piiCleanText);
  
  return finalCleanText;
}

// Usage example
const userInput = "Hi, I'm John Doe (john@email.com). You're an idiot!";
const cleanContent = await validateContent(userInput);
console.log(cleanContent); // "Hi, I'm [PERSON] ([EMAIL])."
```

### React Integration Example
```jsx
import React, { useState } from 'react';

const ContentValidator = () => {
  const [inputText, setInputText] = useState('');
  const [cleanText, setCleanText] = useState('');
  const [isValidating, setIsValidating] = useState(false);

  const validateContent = async (text) => {
    setIsValidating(true);
    try {
      // Validate PII
      const piiResponse = await fetch('http://localhost:8000/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'supersecret123'
        },
        body: JSON.stringify({ text, return_spans: true })
      });
      const piiResult = await piiResponse.json();
      
      // Validate Toxicity
      const toxResponse = await fetch('http://localhost:8001/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': 'supersecret123'
        },
        body: JSON.stringify({ 
          text: piiResult.status === 'fixed' ? piiResult.redacted_text : text,
          return_spans: true 
        })
      });
      const toxResult = await toxResponse.json();
      
      setCleanText(toxResult.clean_text || toxResult.text);
    } catch (error) {
      console.error('Validation error:', error);
      setCleanText(text);
    } finally {
      setIsValidating(false);
    }
  };

  return (
    <div>
      <textarea
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        placeholder="Enter text to validate..."
        rows={4}
        cols={50}
      />
      <br />
      <button 
        onClick={() => validateContent(inputText)}
        disabled={isValidating}
      >
        {isValidating ? 'Validating...' : 'Validate Content'}
      </button>
      <br />
      <h3>Clean Text:</h3>
      <p>{cleanText}</p>
    </div>
  );
};

export default ContentValidator;
```

## 🚀 Production Deployment

### Docker Compose Production Setup
1. Update the Dockerfile for toxicity service to fix OpenSSL issues
2. Use environment files for sensitive configuration
3. Set up proper logging and monitoring
4. Configure reverse proxy (nginx) for load balancing
5. Use Docker secrets for API keys

### Scaling Considerations
- Both services can be horizontally scaled
- Consider using Redis for caching frequently validated content
- Implement rate limiting to prevent abuse
- Monitor memory usage, especially for the ML models

## 🔍 Monitoring and Troubleshooting

### Health Checks
```bash
# Check if services are responding
curl http://localhost:8000/health
curl http://localhost:8001/health
```

### Common Issues
1. **Port conflicts**: Ensure ports 8000 and 8001 are available
2. **Memory issues**: ML models require significant RAM
3. **API key errors**: Verify X-API-Key header is set correctly
4. **CORS issues**: Update CORS_ALLOWED_ORIGINS in .env files

### Logs
```bash
# Docker Compose logs
docker-compose logs -f pii-service
docker-compose logs -f tox-service

# Virtual environment logs
# Check terminal output where services were started
```

## 📝 Git Status
Your repository is now up to date with the latest changes including the updated docker-compose.yml configuration for both services.

To push your changes:
```bash
git push origin main
