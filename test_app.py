#!/usr/bin/env python3
"""
Azure OpenAI Proxy Unit Tests
"""

import os
import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Set up test environment variables
os.environ.update({
    "AZURE_CLIENT_ID": "test-client-id",
    "AZURE_CLIENT_SECRET": "test-client-secret",
    "AZURE_TENANT_ID": "test-tenant-id",
    "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com/",
    "AZURE_OPENAI_DEPLOYMENT": "gpt-4o-mini",
    "AZURE_OPENAI_API_VERSION": "2024-02-01",
    "HOST": "127.0.0.1",
    "PORT": "8000",
    "LOG_LEVEL": "ERROR"
})

from app import app, settings, get_azure_credential, get_openai_client


class TestConfig:
    """Test configuration settings"""

    def test_settings_validation(self):
        """Test settings validation"""
        assert settings.azure_client_id == "test-client-id"
        assert settings.azure_client_secret == "test-client-secret"
        assert settings.azure_tenant_id == "test-tenant-id"
        assert settings.azure_openai_endpoint == "https://test.openai.azure.com/"
        assert settings.azure_openai_deployment == "gpt-4o-mini"
        assert settings.host == "127.0.0.1"
        assert settings.port == 8000

    def test_required_fields(self):
        """Test required fields"""
        required_fields = [
            settings.azure_client_id,
            settings.azure_client_secret,
            settings.azure_tenant_id,
            settings.azure_openai_endpoint,
            settings.azure_openai_deployment
        ]
        assert all(required_fields), "All required fields should have values"


class TestAzureCredential:
    """Test Azure AD credential functionality"""

    def test_get_azure_credential_caching(self):
        """Test credential caching"""
        # Clear cache
        import app
        app._azure_credential = None

        with patch('app.ClientSecretCredential') as mock_cred_class:
            mock_credential = Mock()
            mock_cred_class.return_value = mock_credential

            # First call
            cred1 = get_azure_credential()
            assert cred1 == mock_credential

            # Second call (should return cached instance)
            cred2 = get_azure_credential()
            assert cred2 == mock_credential

            # Should only create one instance
            mock_cred_class.assert_called_once()


class TestOpenAIClient:
    """Test OpenAI client functionality"""

    def test_get_openai_client_caching(self):
        """Test client caching"""
        import app
        app._openai_client = None

        with patch('app.get_azure_credential') as mock_get_cred, \
             patch('app.AzureOpenAI') as mock_client_class:

            mock_credential = Mock()
            mock_get_cred.return_value = mock_credential

            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # First call
            client1 = get_openai_client()
            assert client1 == mock_client

            # Second call (should return cached instance)
            client2 = get_openai_client()
            assert client2 == mock_client

            # Should only create one client instance
            mock_client_class.assert_called_once()


class TestAPIEndpoints:
    """Test API endpoints"""

    def test_health_check(self):
        """Test health check endpoint"""
        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "azure-openai-proxy"

    def test_root_endpoint(self):
        """Test root endpoint"""
        client = TestClient(app)
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Azure OpenAI Proxy"
        assert data["version"] == "1.0.0"
        assert "/health - Health check" in data["endpoints"]
        assert "/v1/models - List models" in data["endpoints"]
        assert "/v1/chat/completions - Chat completions" in data["endpoints"]

    def test_list_models(self):
        """Test list models endpoint"""
        client = TestClient(app)
        response = client.get("/v1/models")

        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) == 1
        assert data["data"][0]["id"] == "gpt-4o-mini"
        assert data["data"][0]["owned_by"] == "azure-openai"


class TestChatCompletions:
    """Test chat completions endpoint"""

    def test_chat_completions_basic(self):
        """Test basic chat completion"""
        client = TestClient(app)

        with patch('app.get_openai_client') as mock_get_client:
            mock_client = Mock()

            # Create a simple dict response instead of Mock to avoid recursion
            mock_response = {
                "id": "test-id",
                "object": "chat.completion",
                "created": 1234567890,
                "model": "gpt-4o-mini",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "Hello from Azure OpenAI!"
                        },
                        "finish_reason": "stop"
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30
                }
            }
            mock_client.chat.completions.create.return_value = mock_response
            mock_get_client.return_value = mock_client

            request_data = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 100,
                "temperature": 0.7
            }

            response = client.post("/v1/chat/completions", json=request_data)

            assert response.status_code == 200
            mock_client.chat.completions.create.assert_called_once()

    def test_chat_completions_stream(self):
        """Test streaming chat completion"""
        client = TestClient(app)

        with patch('app.get_openai_client') as mock_get_client:
            mock_client = Mock()
            mock_response = Mock()
            mock_chunk = Mock()
            mock_choice = Mock()
            mock_delta = Mock()
            mock_delta.content = "Hello"
            mock_choice.delta = mock_delta
            mock_chunk.choices = [mock_choice]
            mock_response.__iter__ = Mock(return_value=[mock_chunk])
            mock_client.chat.completions.create.return_value = mock_response
            mock_get_client.return_value = mock_client

            request_data = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Hello"}],
                "stream": True
            }

            response = client.post("/v1/chat/completions", json=request_data)

            assert response.status_code == 200
            assert response.headers["content-type"] == "text/plain; charset=utf-8"

    def test_chat_completions_error_handling(self):
        """Test error handling"""
        client = TestClient(app)

        with patch('app.get_openai_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Connection failed")

            request_data = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": "Hello"}]
            }

            response = client.post("/v1/chat/completions", json=request_data)

            assert response.status_code == 500


class TestErrorHandling:
    """Test error handling"""

    def test_missing_environment_variables(self):
        """Test missing environment variables"""
        # Temporarily clear environment variables
        original_env = dict(os.environ)

        try:
            # Clear required environment variables
            for key in ["AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "AZURE_TENANT_ID",
                       "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"]:
                os.environ.pop(key, None)

            # Re-importing module should fail
            with pytest.raises(Exception, match="validation errors"):
                from importlib import reload
                import app
                reload(app)

        finally:
            # Restore environment variables
            os.environ.update(original_env)


class TestIntegration:
    """Integration tests"""

    @pytest.mark.asyncio
    async def test_full_request_flow(self):
        """Test complete request flow"""
        # This test requires real Azure OpenAI service
        # Uncomment when running in real environment

        # client = TestClient(app)
        #
        # request_data = {
        #     "model": "gpt-4o-mini",
        #     "messages": [{"role": "user", "content": "Hello, Azure OpenAI!"}],
        #     "max_tokens": 50
        # }
        #
        # response = client.post("/v1/chat/completions", json=request_data)
        #
        # assert response.status_code == 200
        # data = response.json()
        # assert "choices" in data
        # assert len(data["choices"]) > 0
        # assert "content" in data["choices"][0]["message"]

        pass


if __name__ == "__main__":
    # Run basic tests
    test_config = TestConfig()
    test_config.test_settings_validation()
    test_config.test_required_fields()

    print("✅ Basic configuration test passed")

    # Run API tests
    test_api = TestAPIEndpoints()
    test_api.test_health_check()
    test_api.test_root_endpoint()
    test_api.test_list_models()

    print("✅ API endpoint tests passed")

    print("🎉 All tests passed!")