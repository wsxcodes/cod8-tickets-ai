import httpx
from urllib.parse import quote

class AzureSearchClient:
    """
    Async client for Azure AI Search that supports vector embeddings and hybrid search.
    """

    def __init__(self, service_url: str, index_name: str, api_key: str,
                 vector_field: str, key_field: str = "id",
                 api_version: str = "2024-07-01"):
        self.service_url = service_url
        self.api_key = api_key
        self.api_version = api_version
        self.index_name = index_name
        self.vector_field = vector_field
        self.key_field = key_field
        self.base_url = service_url
        self.headers = {
            "Content-Type": "application/json",
            "api-key": api_key
        }

    async def _post(self, url: str, json: dict):
        """Helper function to make async POST requests."""
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=json)
            response.raise_for_status()
            return response.json()

    async def hybrid_search(self, text_query: str = None, embedding: list = None, top_k: int = 5):
        """Perform hybrid search using both keyword and vector similarity."""
        url = f"{self.base_url}/indexes/{self.index_name}/docs/search?api-version={self.api_version}"
        body = {
            "search": text_query or "*",
            "top": top_k
        }
        if embedding is not None:
            body["vectorQueries"] = [
                {
                    "kind": "vector",
                    "fields": self.vector_field,
                    "vector": embedding,
                    "k": top_k
                }
            ]
        return await self._post(url, body)

    async def fulltext_search(self, text_query: str, top_k: int = 5):
        """Perform a full-text search using keyword search only."""
        url = f"{self.base_url}/indexes/{self.index_name}/docs/search?api-version={self.api_version}"
        body = {
            "search": text_query,
            "top": top_k
        }
        return await self._post(url, body)

    async def vector_search(self, embedding: list, top_k: int = 5):
        """Perform a vector-based search using similarity matching."""
        url = f"{self.base_url}/indexes/{self.index_name}/docs/search?api-version={self.api_version}"
        body = {
            "vectorQueries": [
                {
                    "kind": "vector",
                    "fields": self.vector_field,
                    "vector": embedding,
                    "k": top_k
                }
            ]
        }
        return await self._post(url, body)

    async def get_document(self, doc_id: str):
        """Retrieve a document by its ID."""
        key_param = quote(doc_id, safe='')
        url = f"{self.base_url}/indexes/{self.index_name}/docs/{key_param}?api-version={self.api_version}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()

    async def list_documents(self, batch_size: int = 1000, limit: int = None, offset: int = 0):
        """List documents in the index with optional limit and offset."""
        all_docs = []
        skip = offset
        while True:
            top = batch_size
            if limit is not None:
                remaining = limit - len(all_docs)
                if remaining <= 0:
                    break
                top = min(batch_size, remaining)
            url = f"{self.base_url}/indexes/{self.index_name}/docs/search?api-version={self.api_version}"
            body = {
                "search": "*",
                "select": "*",
                "top": top,
                "skip": skip
            }
            results = await self._post(url, body)
            docs = results.get("value", [])
            if not docs:
                break
            all_docs.extend(docs)
            if len(docs) < top:
                break
            skip += top
        return all_docs[:limit] if limit else all_docs
    