# PII Protection Microservice - Deployment Guide

This guide provides step-by-step instructions for deploying the PII Protection microservice using Docker.

## Prerequisites

### 1. Install Docker

#### macOS
```bash
# Option 1: Install Docker Desktop (Recommended)
# Download from: https://www.docker.com/products/docker-desktop/

# Option 2: Install using Homebrew
brew install --cask docker

# Option 3: Install Docker CLI and Docker Compose separately
brew install docker docker-compose
```

#### Linux (Ubuntu/Debian)
```bash
# Update package index
sudo apt-get update

# Install required packages
sudo apt-get install ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Add user to docker group (optional, to run without sudo)
sudo usermod -aG docker $USER
```

#### Windows
```powershell
# Install Docker Desktop
# Download from: https://www.docker.com/products/docker-desktop/

# Or using Chocolatey
choco install docker-desktop
```

### 2. Verify Docker Installation
```bash
# Check Docker version
docker --version

# Check Docker Compose version
docker compose version
# or for older versions:
docker-compose --version

# Test Docker installation
docker run hello-world
```

## Deployment Options

### Option 1: Using Docker Compose (Recommended)

This is the easiest way to deploy the service with all configurations pre-set.

1. **Clone the repository:**
   ```bash
   git clone https://github.com/madhugraj/zGrid.git
   cd zGrid
   ```

2. **Start the service:**
   ```bash
   docker compose up --build -d
   ```

3. **Verify the service is running:**
   ```bash
   # Check container status
   docker compose ps

   # Check logs
   docker compose logs -f pii-service

   # Test health endpoint
   curl http://localhost:8000/health
   ```

4. **Test the API:**
   ```bash
   curl -X POST "http://localhost:8000/validate" \
     -H "Content-Type: application/json" \
     -H "X-API-Key: supersecret123" \
     -d '{
       "text": "My email is john.doe@example.com and my phone is +1-555-123-4567"
     }'
   ```

### Option 2: Using Docker directly

1. **Build the Docker image:**
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

3. **Verify the service:**
   ```bash
   # Check container status
   docker ps

   # Check logs
   docker logs pii-protection-service

   # Test health endpoint
   curl http://localhost:8000/health
   ```

## Configuration

### Environment Variables

You can customize the service behavior by modifying the environment variables in `docker-compose.yml`:

```yaml
environment:
  # Core settings
  - PRESIDIO_LANGUAGE=en
  - SPACY_MODEL=en_core_web_lg
  
  # GLiNER model settings
  - GLINER_LOCAL_DIR=/app/models/gliner_small-v2.1
  - GLINER_THRESHOLD=0.45
  - GLINER_LABELS=person,location,organization
  
  # PII detection settings
  - ENTITIES=EMAIL_ADDRESS,PHONE_NUMBER,CREDIT_CARD,US_SSN,PERSON,LOCATION,IN_AADHAAR,IN_PAN
  - ENTITY_THRESHOLDS={"EMAIL_ADDRESS":0.3,"PHONE_NUMBER":0.3,"PERSON":0.35,"LOCATION":0.4}
  - PLACEHOLDERS={"DEFAULT":"[REDACTED]","EMAIL_ADDRESS":"[EMAIL]","PHONE_NUMBER":"[PHONE]"}
  
  # Security and CORS
  - CORS_ALLOWED_ORIGINS=https://preview--zgrid-feature-flow.lovable.app,http://localhost:3000
  - PII_API_KEYS=supersecret123,piievalyavar
```

### Custom Configuration

1. **Create a custom environment file:**
   ```bash
   cp pii_service/.env pii_service/.env.local
   # Edit .env.local with your custom settings
   ```

2. **Update docker-compose.yml to use the custom file:**
   ```yaml
   services:
     pii-service:
       env_file:
         - ./pii_service/.env.local
   ```

## Production Deployment

### 1. Security Considerations

1. **Use strong API keys:**
   ```bash
   # Generate secure API keys
   openssl rand -hex 32
   ```

2. **Enable HTTPS:**
   ```yaml
   # Add nginx reverse proxy
   services:
     nginx:
       image: nginx:alpine
       ports:
         - "443:443"
         - "80:80"
       volumes:
         - ./nginx.conf:/etc/nginx/nginx.conf
         - ./ssl:/etc/nginx/ssl
   ```

3. **Restrict CORS origins:**
   ```yaml
   environment:
     - CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
   ```

### 2. Resource Management

Add resource limits to prevent memory issues:

```yaml
services:
  pii-service:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2'
        reservations:
          memory: 2G
          cpus: '1'
```

### 3. Monitoring and Logging

1. **Configure logging:**
   ```yaml
   services:
     pii-service:
       logging:
         driver: "json-file"
         options:
           max-size: "10m"
           max-file: "3"
   ```

2. **Add health checks:**
   ```yaml
   healthcheck:
     test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
     interval: 30s
     timeout: 10s
     retries: 3
     start_period: 40s
   ```

### 4. Backup and Recovery

1. **Backup model files:**
   ```bash
   # Create backup of models
   tar -czf models-backup-$(date +%Y%m%d).tar.gz pii_service/models/
   ```

2. **Database backup (if using external DB):**
   ```bash
   # Example for PostgreSQL
   docker exec postgres-container pg_dump -U username dbname > backup.sql
   ```

## Scaling and Load Balancing

### Horizontal Scaling

1. **Scale the service:**
   ```bash
   docker compose up --scale pii-service=3 -d
   ```

2. **Add load balancer:**
   ```yaml
   services:
     nginx:
       image: nginx:alpine
       ports:
         - "8000:80"
       volumes:
         - ./nginx-lb.conf:/etc/nginx/nginx.conf
       depends_on:
         - pii-service
   
     pii-service:
       deploy:
         replicas: 3
   ```

### nginx Load Balancer Configuration

Create `nginx-lb.conf`:
```nginx
upstream pii_backend {
    server pii-service:8000;
}

server {
    listen 80;
    
    location / {
        proxy_pass http://pii_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location /health {
        proxy_pass http://pii_backend/health;
    }
}
```

## Troubleshooting

### Common Issues

1. **Port already in use:**
   ```bash
   # Find process using port 8000
   lsof -i :8000
   
   # Kill the process or use different port
   docker compose -f docker-compose.yml up -d --scale pii-service=1 -p 8001:8000
   ```

2. **Model loading errors:**
   ```bash
   # Check if model files exist
   ls -la pii_service/models/gliner_small-v2.1/
   
   # Verify Git LFS files
   git lfs ls-files
   git lfs pull
   ```

3. **Memory issues:**
   ```bash
   # Check container memory usage
   docker stats pii-protection-service
   
   # Increase memory limits in docker-compose.yml
   ```

4. **CORS errors:**
   ```bash
   # Check CORS configuration
   docker compose logs pii-service | grep CORS
   
   # Update CORS_ALLOWED_ORIGINS in docker-compose.yml
   ```

### Debugging

1. **Access container shell:**
   ```bash
   docker compose exec pii-service /bin/bash
   ```

2. **View detailed logs:**
   ```bash
   docker compose logs -f --tail=100 pii-service
   ```

3. **Check container health:**
   ```bash
   docker compose ps
   docker inspect pii-protection-service
   ```

## Maintenance

### Updates

1. **Update the service:**
   ```bash
   git pull origin main
   docker compose down
   docker compose up --build -d
   ```

2. **Update only the image:**
   ```bash
   docker compose pull pii-service
   docker compose up -d pii-service
   ```

### Cleanup

1. **Remove containers and images:**
   ```bash
   docker compose down --rmi all --volumes
   ```

2. **Clean up Docker system:**
   ```bash
   docker system prune -a
   ```

## Integration with Frontend

### API Endpoint

The service will be available at:
- **Local development:** `http://localhost:8000`
- **Production:** `https://your-domain.com` (with reverse proxy)

### Frontend Integration Example

```javascript
// Configure API base URL
const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? 'https://your-pii-service.com' 
  : 'http://localhost:8000';

// PII detection function
async function detectPII(text) {
  const response = await fetch(`${API_BASE_URL}/validate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': 'your-api-key'
    },
    body: JSON.stringify({ text })
  });
  
  return response.json();
}
```

### CORS Configuration

Make sure to update the CORS settings in your deployment to include your frontend domain:

```yaml
environment:
  - CORS_ALLOWED_ORIGINS=https://preview--zgrid-feature-flow.lovable.app,https://your-frontend-domain.com
```

## Support

For issues and questions:
1. Check the logs: `docker compose logs pii-service`
2. Review the troubleshooting section above
3. Check the GitHub repository issues
4. Verify your Docker and system requirements

## Performance Optimization

1. **Use multi-stage builds** for smaller images
2. **Enable model caching** (already configured)
3. **Use SSD storage** for model files
4. **Monitor memory usage** and adjust limits
5. **Consider using GPU** for faster inference (requires NVIDIA Docker)

This deployment guide should help you successfully containerize and deploy your PII Protection microservice!
