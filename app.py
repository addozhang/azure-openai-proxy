#!/usr/bin/env python3
"""
Azure OpenAI Proxy Service
Provides OpenAI API-compatible proxy service with Azure AD authentication for Azure OpenAI
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from azure.identity import ClientSecretCredential
from openai import AzureOpenAI
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application configuration settings"""

    # Azure AD authentication configuration
    azure_client_id: str = Field(..., env="AZURE_CLIENT_ID")
    azure_client_secret: str = Field(..., env="AZURE_CLIENT_SECRET")
    azure_tenant_id: str = Field(..., env="AZURE_TENANT_ID")

    # Azure OpenAI configuration
    azure_openai_endpoint: str = Field(..., env="AZURE_OPENAI_ENDPOINT")
    azure_openai_deployment: str = Field(..., env="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_api_version: str = Field(default="2024-02-01", env="AZURE_OPENAI_API_VERSION")

    # Service configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Optional configuration
    request_timeout: int = Field(default=60, env="REQUEST_TIMEOUT")
    max_tokens: int = Field(default=4000, env="AZURE_OPENAI_MAX_TOKENS")
    temperature: float = Field(default=0.7, env="AZURE_OPENAI_TEMPERATURE")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global configuration instance
settings = Settings()

# Azure AD credential client cache
_azure_credential: Optional[ClientSecretCredential] = None
_openai_client: Optional[AzureOpenAI] = None


def get_azure_credential() -> ClientSecretCredential:
    """Get Azure AD credential with caching"""
    global _azure_credential
    if _azure_credential is None:
        _azure_credential = ClientSecretCredential(
            client_id=settings.azure_client_id,
            client_secret=settings.azure_client_secret,
            tenant_id=settings.azure_tenant_id
        )
    return _azure_credential


@lru_cache(maxsize=1)
def get_openai_client() -> AzureOpenAI:
    """Get Azure OpenAI client with caching"""
    credential = get_azure_credential()

    def token_provider():
        token = credential.get_token("https://cognitiveservices.azure.com/.default")
        return token.token

    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        azure_ad_token_provider=token_provider,
        api_version=settings.azure_openai_api_version
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management"""
    # Validate connection on startup
    try:
        client = get_openai_client()
        # Send a simple test request to validate connection
        response = client.chat.completions.create(
            model=settings.azure_openai_deployment,
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5
        )
        logger.info("✅ Azure OpenAI connection validation successful")
    except Exception as e:
        logger.error(f"❌ Azure OpenAI connection validation failed: {e}")
        raise

    yield

    # Cleanup resources
    logger.info("🧹 Cleaning up Azure OpenAI proxy resources")


# Create FastAPI application
app = FastAPI(
    title="Azure OpenAI Proxy",
    description="OpenAI API-compatible proxy service for Azure OpenAI",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatCompletionRequest(BaseModel):
    """Chat completion request model"""
    model: str = Field(default="", description="Model name")
    messages: list = Field(..., description="List of messages")
    max_tokens: Optional[int] = Field(None, description="Maximum number of tokens")
    temperature: Optional[float] = Field(0.7, description="Temperature parameter")
    top_p: Optional[float] = Field(1.0, description="Top-p parameter")
    n: Optional[int] = Field(1, description="Number of completions to generate")
    stream: Optional[bool] = Field(False, description="Whether to stream the response")
    stop: Optional[list] = Field(None, description="Stop sequences")
    presence_penalty: Optional[float] = Field(0.0, description="Presence penalty")
    frequency_penalty: Optional[float] = Field(0.0, description="Frequency penalty")
    logit_bias: Optional[dict] = Field(None, description="Logit bias")
    user: Optional[str] = Field(None, description="User identifier")
    tools: Optional[list] = Field(None, description="List of tools")
    tool_choice: Optional[str] = Field(None, description="Tool choice")


class ModelListResponse(BaseModel):
    """Model list response"""
    object: str = "list"
    data: list = Field(default_factory=lambda: [
        {
            "id": "gpt-4o-mini",
            "object": "model",
            "created": 1677610602,
            "owned_by": "azure-openai"
        }
    ])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "azure-openai-proxy"}


@app.get("/v1/models")
async def list_models():
    """Get list of available models"""
    return ModelListResponse()


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """Chat completions endpoint"""
    try:
        # Get Azure OpenAI client
        client = get_openai_client()

        # Prepare request parameters
        params = request.model_dump(exclude_unset=True)
        params["model"] = settings.azure_openai_deployment

        # Handle streaming requests
        if request.stream:
            return StreamingResponse(
                stream_chat_response(client, params),
                media_type="text/plain"
            )

        # Handle regular requests
        response = client.chat.completions.create(**params)
        return response

    except Exception as e:
        logger.error(f"Chat completion request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def stream_chat_response(client: AzureOpenAI, params: dict):
    """Streaming chat response generator"""
    try:
        response = client.chat.completions.create(**params)

        for chunk in response:
            if chunk.choices:
                yield f"data: {chunk.model_dump_json()}\n\n"

        yield "data: [DONE]\n\n"

    except Exception as e:
        logger.error(f"Streaming response failed: {e}")
        yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Azure OpenAI Proxy",
        "version": "1.0.0",
        "endpoints": [
            "/health - Health check",
            "/v1/models - List models",
            "/v1/chat/completions - Chat completions"
        ]
    }


def main():
    """Main function"""
    logger.info("🚀 Starting Azure OpenAI proxy service")
    logger.info(f"📍 Service address: http://{settings.host}:{settings.port}")
    logger.info(f"🔗 Azure OpenAI endpoint: {settings.azure_openai_endpoint}")
    logger.info(f"🎯 Deployment name: {settings.azure_openai_deployment}")

    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()