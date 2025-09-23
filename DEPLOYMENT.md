# Azure OpenAI Proxy Deployment Guide

## 📋 Deployment Overview

This guide explains how to deploy the Azure OpenAI proxy service, supporting multiple deployment methods:

- 🐳 Docker container deployment
- 🐧 Linux server deployment
- ☁️ Azure Container Instances deployment
- ☁️ Azure Web App deployment
- 🚀 Kubernetes deployment

## 🐳 Docker Deployment (Recommended)

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+

### Quick Deployment

1. **Clone the project**
    ```bash
   git clone <repository-url>
   cd azure-openai-proxy
   ```

2. **Configure environment variables**
    ```bash
    cp .env.example .env
    # Edit the .env file with your actual Azure configuration
    nano .env
   ```

3. **Start the service**
    ```bash
   docker-compose up -d
   ```

4. **Verify deployment**
    ```bash
    # Check service status
    docker-compose ps

    # View logs
    docker-compose logs -f azure-openai-proxy

    # Health check
    curl http://localhost:8000/health
   ```

### Production Environment Configuration

#### Using External Configuration Files
```bash
# Create configuration directory
mkdir -p config

# Copy configuration file
cp .env.example config/.env

# Edit configuration
nano config/.env

# Mount configuration file
docker run -v $(pwd)/config/.env:/app/.env \
  -p 8000:8000 \
  azure-openai-proxy
```

#### Using Environment Variables
```bash
docker run -d \
  --name azure-openai-proxy \
  -p 8000:8000 \
  -e AZURE_CLIENT_ID="your-client-id" \
  -e AZURE_CLIENT_SECRET="your-client-secret" \
  -e AZURE_TENANT_ID="your-tenant-id" \
  -e AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/" \
  -e AZURE_OPENAI_DEPLOYMENT="gpt-4o" \
  azure-openai-proxy
```

### Docker Configuration Options

#### Resource Limits
```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 1G
    reservations:
      cpus: '0.5'
      memory: 512M
```

#### Health Checks
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

## 🐧 Linux Server Deployment

### System Requirements

- Ubuntu 20.04+ / CentOS 8+ / RHEL 8+
- Python 3.11+
- 4GB RAM
- 2 CPU cores

### Installation Steps

1. **Update system**
    ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **Install Python and pip**
    ```bash
   sudo apt install python3.11 python3.11-pip python3.11-venv -y
   ```

3. **Create virtual environment**
    ```bash
   python3.11 -m venv azure-openai-proxy
   source azure-openai-proxy/bin/activate
   ```

4. **Clone the project**
    ```bash
   git clone <repository-url>
   cd azure-openai-proxy
   ```

5. **Install dependencies**
    ```bash
   pip install -r requirements.txt
   ```

6. **Configure environment variables**
    ```bash
    cp .env.example .env
    nano .env  # Edit configuration
    ```

7. **Create system service**

    Create `/etc/systemd/system/azure-openai-proxy.service`:
   ```ini
   [Unit]
   Description=Azure OpenAI Proxy Service
   After=network.target

   [Service]
   Type=simple
   User=www-data
   Group=www-data
   WorkingDirectory=/path/to/azure-openai-proxy
   Environment=PATH=/path/to/azure-openai-proxy/venv/bin
   ExecStart=/path/to/azure-openai-proxy/venv/bin/python app.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

8. **Start the service**
    ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable azure-openai-proxy
   sudo systemctl start azure-openai-proxy
   sudo systemctl status azure-openai-proxy
   ```

## ☁️ Azure Container Instances Deployment

### Prerequisites

- Azure CLI
- Azure subscription

### Deployment Steps

1. **Login to Azure**
    ```bash
   az login
   az account set --subscription "your-subscription-id"
   ```

2. **Create resource group**
    ```bash
   az group create --name azure-openai-proxy-rg --location eastus
   ```

3. **Create container instance**
    ```bash
   az container create \
       --resource-group azure-openai-proxy-rg \
       --name azure-openai-proxy \
       --image your-registry/azure-openai-proxy:latest \
       --ports 8000 \
       --environment-variables \
           AZURE_CLIENT_ID="your-client-id" \
           AZURE_CLIENT_SECRET="your-client-secret" \
           AZURE_TENANT_ID="your-tenant-id" \
           AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/" \
           AZURE_OPENAI_DEPLOYMENT="gpt-4o" \
       --cpu 1 \
       --memory 1 \
       --restart-policy Always
   ```

4. **Get public IP**
    ```bash
   az container show \
       --resource-group azure-openai-proxy-rg \
       --name azure-openai-proxy \
       --query ipAddress.ip \
       --output tsv
   ```

## ☁️ Azure Web App Deployment

### Deploy using Azure CLI

1. **Create web app**
    ```bash
   az webapp create \
       --resource-group azure-openai-proxy-rg \
       --plan azure-openai-proxy-plan \
       --name azure-openai-proxy-app \
       --runtime "PYTHON:3.11" \
       --startup-file "python app.py"
   ```

2. **Configure app settings**
    ```bash
   az webapp config appsettings set \
       --resource-group azure-openai-proxy-rg \
       --name azure-openai-proxy-app \
       --settings \
           AZURE_CLIENT_ID="your-client-id" \
           AZURE_CLIENT_SECRET="your-client-secret" \
           AZURE_TENANT_ID="your-tenant-id" \
           AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/" \
           AZURE_OPENAI_DEPLOYMENT="gpt-4o"
   ```

3. **Deploy code**
    ```bash
   az webapp deployment source config \
       --resource-group azure-openai-proxy-rg \
       --name azure-openai-proxy-app \
       --repo-url <repository-url> \
       --branch main \
       --manual-integration
   ```

### Deploy using GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Azure Web App

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Deploy to Azure Web App
        uses: azure/webapps-deploy@v2
        with:
          app-name: 'azure-openai-proxy-app'
          publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
```

## 🚀 Kubernetes Deployment

### Prerequisites

- Kubernetes cluster
- kubectl configuration

### Deployment Steps

1. **Create namespace**
    ```bash
   kubectl create namespace azure-openai-proxy
   ```

2. **Create ConfigMap**
    ```bash
   kubectl create configmap azure-openai-proxy-config \
       --from-env-file=.env \
       -n azure-openai-proxy
   ```

3. **Create Secret (sensitive information)**
    ```bash
   kubectl create secret generic azure-openai-proxy-secrets \
       --from-literal=azure-client-secret="your-client-secret" \
       -n azure-openai-proxy
   ```

4. **Create deployment**
    ```bash
   kubectl apply -f k8s-deployment.yaml -n azure-openai-proxy
   ```

### Kubernetes Manifest Files

Create `k8s-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: azure-openai-proxy
  labels:
    app: azure-openai-proxy
spec:
  replicas: 2
  selector:
    matchLabels:
      app: azure-openai-proxy
  template:
    metadata:
      labels:
        app: azure-openai-proxy
    spec:
      containers:
      - name: azure-openai-proxy
        image: your-registry/azure-openai-proxy:latest
        ports:
        - containerPort: 8000
        env:
        - name: AZURE_CLIENT_ID
          valueFrom:
            configMapKeyRef:
              name: azure-openai-proxy-config
              key: AZURE_CLIENT_ID
        - name: AZURE_CLIENT_SECRET
          valueFrom:
            secretKeyRef:
              name: azure-openai-proxy-secrets
              key: azure-client-secret
        - name: AZURE_TENANT_ID
          valueFrom:
            configMapKeyRef:
              name: azure-openai-proxy-config
              key: AZURE_TENANT_ID
        - name: AZURE_OPENAI_ENDPOINT
          valueFrom:
            configMapKeyRef:
              name: azure-openai-proxy-config
              key: AZURE_OPENAI_ENDPOINT
        - name: AZURE_OPENAI_DEPLOYMENT
          valueFrom:
            configMapKeyRef:
              name: azure-openai-proxy-config
              key: AZURE_OPENAI_DEPLOYMENT
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: azure-openai-proxy
spec:
  type: ClusterIP
  ports:
  - port: 8000
    targetPort: 8000
  selector:
    app: azure-openai-proxy
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: azure-openai-proxy
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
  - host: api.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: azure-openai-proxy
            port:
              number: 8000
```

## 📊 Monitoring and Logging

### Log Configuration

#### Docker Environment
```bash
# View logs
docker-compose logs -f azure-openai-proxy

# View specific service logs
docker-compose logs -f --tail=100 azure-openai-proxy
```

#### Kubernetes Environment
```bash
# View pod logs
kubectl logs -f deployment/azure-openai-proxy -n azure-openai-proxy

# View specific pod logs
kubectl logs -f pod/azure-openai-proxy-xxxxx -n azure-openai-proxy
```

### Health Checks

```bash
# Local testing
curl http://localhost:8000/health

# Remote testing
curl https://your-domain.com/health
```

### Metrics Monitoring

#### Using Prometheus

1. **Install Prometheus**
    ```bash
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm install prometheus prometheus-community/prometheus
   ```

2. **Configure metrics collection**
    ```yaml
    # Add to ConfigMap
    scrape_configs:
     - job_name: 'azure-openai-proxy'
       static_configs:
         - targets: ['azure-openai-proxy:8000']
       metrics_path: '/metrics'
   ```

#### Using Azure Monitor

```bash
# Enable Application Insights
az monitor app-insights component create \
    --app azure-openai-proxy-insights \
    --location eastus \
    --resource-group azure-openai-proxy-rg

# Configure connection string
az webapp config appsettings set \
    --resource-group azure-openai-proxy-rg \
    --name azure-openai-proxy-app \
    --settings APPLICATIONINSIGHTS_CONNECTION_STRING="your-connection-string"
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Environment variables not loaded
```bash
# Check environment variables
docker-compose exec azure-openai-proxy env | grep AZURE

# Verify .env file
cat .env
```

#### 2. Azure authentication failed
```bash
# Check Azure CLI login status
az account show

# Verify service principal permissions
az ad sp show --id "your-client-id"

# Test token acquisition
python3 -c "
from azure.identity import ClientSecretCredential
cred = ClientSecretCredential(
    client_id='your-client-id',
    client_secret='your-client-secret',
    tenant_id='your-tenant-id'
)
token = cred.get_token('https://cognitiveservices.azure.com/.default')
print('Token acquired successfully')
"
```

#### 3. OpenAI service connection failed
```bash
# Test direct connection
curl -X POST "https://your-resource.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2024-02-01" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "messages": [{"role": "user", "content": "test"}],
    "max_tokens": 10
  }'
```

#### 4. Performance issues
```bash
# Check resource usage
docker stats azure-openai-proxy

# View slow query logs
docker-compose logs azure-openai-proxy | grep -i "slow\|timeout\|error"
```

### Debug Mode

#### Enable detailed logging
```bash
# Set log level
export LOG_LEVEL=DEBUG

# Restart service
docker-compose restart azure-openai-proxy
```

#### Using debug tools
```bash
# Install debug tools
pip install ipython pdbpp

# Enter debug mode
python -m pdb app.py
```

## 🔒 Security Configuration

### Network Security

#### Configure firewall
```bash
# Azure environment
az network nsg rule create \
    --resource-group azure-openai-proxy-rg \
    --nsg-name azure-openai-proxy-nsg \
    --name Allow-HTTP \
    --protocol Tcp \
    --direction Inbound \
    --priority 100 \
    --source-address-prefixes "*" \
    --source-port-ranges "*" \
    --destination-address-prefixes "*" \
    --destination-port-ranges 8000 \
    --access Allow
```

#### Configure HTTPS
```bash
# Use Let's Encrypt
certbot certonly --webroot -w /app/static -d api.your-domain.com

# Configure SSL/TLS
docker run -d \
  --name nginx-proxy \
  -p 80:80 \
  -p 443:443 \
  -v /path/to/certs:/etc/nginx/certs \
  -v /path/to/config:/etc/nginx/conf.d \
  nginx:alpine
```

### Access Control

#### API key authentication
```python
# Add API key validation to the application
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != "your-secret-key":
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials
```

#### IP whitelist
```python
from fastapi import Request

ALLOWED_IPS = ["192.168.1.100", "10.0.0.50"]

@app.middleware("http")
async def ip_whitelist_middleware(request: Request, call_next):
    client_ip = request.client.host
    if client_ip not in ALLOWED_IPS:
        raise HTTPException(status_code=403, detail="IP not allowed")
    response = await call_next(request)
    return response
```

## 📈 Performance Optimization

### Cache Configuration

#### Redis cache
```bash
# Install Redis
docker run -d \
  --name redis \
  -p 6379:6379 \
  redis:alpine

# Configure application to use Redis
export REDIS_URL=redis://localhost:6379
```

#### Memory cache
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_response(query: str) -> str:
    # Cache logic
    pass
```

### Load Balancing

#### Using Nginx reverse proxy
```nginx
upstream azure-openai-proxy {
    server 192.168.1.10:8000;
    server 192.168.1.11:8000;
    server 192.168.1.12:8000;
}

server {
    listen 80;
    server_name api.your-domain.com;

    location / {
        proxy_pass http://azure-openai-proxy;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Database Configuration

#### Add database support
```bash
# PostgreSQL
docker run -d \
  --name postgres \
  -e POSTGRES_PASSWORD=your-password \
  -e POSTGRES_DB=azure_openai_proxy \
  -p 5432:5432 \
  postgres:15

# Configure connection string
export DATABASE_URL=postgresql://user:password@localhost:5432/azure_openai_proxy
```

## 🚀 Extended Features

### API Version Management

#### Support multiple API versions
```python
@app.get("/v1/models")
async def list_models(api_version: str = "v1"):
    if api_version == "v1":
        return ModelListResponse()
    else:
        raise HTTPException(status_code=400, detail="Unsupported API version")
```

### Batch Processing

#### Support batch requests
```python
@app.post("/v1/batch/chat/completions")
async def batch_chat_completions(requests: List[ChatCompletionRequest]):
    # Batch processing logic
    pass
```

### Streaming Processing Optimization

#### Improve streaming response
```python
async def stream_with_retry(client: AzureOpenAI, params: dict):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(**params)
            async for chunk in response:
                yield f"data: {chunk.model_dump_json()}\n\n"
            break
        except Exception as e:
            if attempt == max_retries - 1:
                yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            await asyncio.sleep(2 ** attempt)
```

## 📚 Reference Documentation

- [Azure OpenAI Documentation](https://docs.microsoft.com/azure/cognitive-services/openai/)
- [Azure AD Authentication Guide](https://docs.microsoft.com/azure/active-directory/develop/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Documentation](https://docs.docker.com/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)

## 🤝 Contribution Guidelines

Welcome to submit Issues and Pull Requests! Please ensure:

1. Follow existing code style
2. Add appropriate tests
3. Update relevant documentation
4. Provide detailed explanations

## 📄 License

This project uses the MIT License. See LICENSE file for details.

---

**⭐ If this deployment guide is helpful to you, please give the project a Star!**

*Last updated: September 23, 2025*