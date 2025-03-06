from typing import Any, Dict, List, Optional, Union

import requests

try:
    from azure.identity import DefaultAzureCredential
except ImportError:
    DefaultAzureCredential = None  # If azure.identity is not installed or needed


class AzureOpenAI:
    def __init__(self, endpoint: str, api_version: str,
                 api_key: Optional[str] = None,
                 azure_credential: Optional[Any] = None):
        """
        Initialize the AzureOpenAI client.
        :param endpoint: Azure OpenAI endpoint URL, e.g. 'https://<resource>.openai.azure.com/'
        :param api_version: API version (string), e.g. '2024-10-21' or the version your resource requires.
        :param api_key: (optional) API key for Azure OpenAI.
        :param azure_credential: (optional) Azure credential (from azure.identity) for AAD auth.
        """
        self.endpoint = endpoint.rstrip("/")  # ensure no trailing slash
        self.api_version = api_version
        # Determine authentication method
        self.session = requests.Session()
        if azure_credential:
            # Use Azure AD token from provided credential
            token = azure_credential.get_token("https://cognitiveservices.azure.com/.default")
            self.session.headers.update({"Authorization": f"Bearer {token.token}"})
        elif api_key:
            # Use API key for auth
            self.session.headers.update({"api-key": api_key})
        else:
            raise ValueError("Authentication required: provide an api_key or an azure_credential.")
        # Set common headers
        self.session.headers.update({"Content-Type": "application/json"})
        # Optional: you could add a custom User-Agent here if needed for identification

    def _request(self, deployment: str, operation: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Internal helper to send a POST request to the specified deployment/operation."""
        url = f"{self.endpoint}/openai/deployments/{deployment}/{operation}?api-version={self.api_version}"
        try:
            response = self.session.post(url, json=payload, timeout=30)
        except requests.RequestException as e:
            # Network or connection error
            raise RuntimeError(f"Failed to connect to Azure OpenAI endpoint: {e}")
        # Check for HTTP errors
        if not response.ok:
            # Try to get error details from response
            error_msg = ""
            try:
                err_info = response.json()
                # Azure OpenAI errors usually in err_info['error']['message']
                if "error" in err_info:
                    error_msg = err_info["error"].get("message") or str(err_info["error"])
                else:
                    error_msg = str(err_info)
            except ValueError:
                # Not JSON response
                error_msg = response.text or response.reason
            code = response.status_code
            raise RuntimeError(f"Azure OpenAI API error (status {code}): {error_msg}")
        return response.json()

    def generate_text(self, deployment: str, prompt: str, **kwargs) -> str:
        """
        Generate a text completion using the specified deployed model.
        :param deployment: Name of the deployment (the model deployment name in Azure OpenAI).
        :param prompt: Prompt string to generate text from.
        :param **kwargs: Additional parameters like max_tokens, temperature, top_p, etc.
        :return: The generated completion text.
        """
        payload = {"prompt": prompt}
        payload.update(kwargs)
        result = self._request(deployment, "completions", payload)
        # Legacy completion models (e.g., GPT-3) return text in 'choices'
        completion_text = result.get("choices",[{}])[0].get("text")  # NoQA
        if completion_text is None:
            # In case the deployment actually uses chat model but called via this method
            completion_text = result.get("choices",[{}])[0].get("message", {}).get("content")  # NoQA
        return completion_text

    def chat_completion(self, deployment: str, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Get a chat completion (assistant response) for a conversation.
        :param deployment: Name of the chat model deployment (e.g., GPT-4 or GPT-3.5 Turbo).
        :param messages: List of message dicts, each with 'role' and 'content'.
        :param **kwargs: Additional parameters like max_tokens, temperature, etc.
        :return: The assistant's reply message content.
        """
        payload = {"messages": messages}
        payload.update(kwargs)
        result = self._request(deployment, "chat/completions", payload)
        # Extract the assistant message content from the response
        return result.get("choices",[{}])[0].get("message", {}).get("content")  # NoQA

    def get_embedding(self, deployment: str, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Retrieve embedding vector(s) for the given input text or texts.
        :param deployment: Name of the embedding model deployment.
        :param text: A string or a list of strings to embed.
        :return: Embedding vector (list of floats) for single text, or list of vectors for list input.
        """
        # Azure OpenAI expects the input as a list (even if single item)
        if isinstance(text, str):
            input_data = [text]
        else:
            input_data = text
        payload = {"input": input_data}
        result = self._request(deployment, "embeddings", payload)
        data = result.get("data", [])
        # Each item in data has an 'embedding' key with the vector
        embeddings = [item.get("embedding") for item in data]
        if isinstance(text, str):
            # If single text input, return the single embedding vector
            return embeddings[0] if embeddings else None
        else:
            # If multiple inputs, return list of embedding vectors
            return embeddings
