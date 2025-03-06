from urllib.parse import quote

import requests


class AzureSearchClient:
    """
    Client for Azure AI Search that supports vector embeddings and hybrid search.
    """

    def __init__(self, service_url: str, index_name: str, api_key: str,
                 vector_field: str, key_field: str = "id",
                 api_version: str = "2024-07-01"):
        """
        Initialize the AzureSearchClient.

        Parameters:
        - service_url: Azure Search service URL.
        - index_name: Name of the index to target.
        - api_key: Admin API key for Azure Search (for authentication).
        - vector_field: Name of the vector field in the index (e.g., 'contentVector').
        - key_field: Name of the key field (document ID field, default 'id').
        - api_version: API version for Azure Search endpoints (default '2024-07-01').
        """
        self.service_url = service_url
        self.api_key = api_key
        self.api_version = api_version
        self.index_name = index_name
        self.vector_field = vector_field
        self.key_field = key_field

        # Base URL for search service endpoints
        self.base_url = service_url
        # Common header with API key (admin key required for write operations)
        self.headers = {
            "Content-Type": "application/json",
            "api-key": api_key
        }

    def upload_document(self, doc_id: str, embedding: list, metadata: dict):
        """
        Upload a single document (or update if ID exists) with vector and metadata.

        Parameters:
        - doc_id: Unique identifier for the document (matches index key field).
        - embedding: List of floats (vector) from the embedding model (length 1536 for ada-002).
        - metadata: Dictionary of other fields/values to store with the document.

        Returns:
        - True if upload succeeded, raises exception on failure.
        """
        # Construct the document payload according to Azure schema.
        document = {
            "@search.action": "upload",  # upsert behavior
            self.key_field: doc_id,
            self.vector_field: embedding
        }
        # Merge metadata into the document payload, ensuring no key conflicts.
        for k, v in metadata.items():
            if k in document and k not in {self.key_field, self.vector_field}:
                raise ValueError(f"Metadata key '{k}' conflicts with reserved field names.")
            document[k] = v

        payload = {"value": [document]}
        url = f"{self.base_url}/indexes/{self.index_name}/docs/index?api-version={self.api_version}"
        response = requests.post(url, headers=self.headers, json=payload)
        try:
            response.raise_for_status()  # Raise HTTP errors (4xx, 5xx).
        except requests.exceptions.HTTPError as e:
            # Azure Search returns JSON with error details on failure
            error_info = response.text
            raise RuntimeError(f"Upload failed: {error_info}") from e

        # Azure responds with status per document in 'value' array.
        result = response.json()
        if ("value" in result and len(result["value"]) > 0
                and result["value"][0].get("status") is True):  # NoQA
            return True
        else:
            err = result["value"][0] if "value" in result and result["value"] else result
            raise RuntimeError(f"Upload error: {err}")

    def hybrid_search(self, text_query: str = None, embedding: list = None, top_k: int = 5):
        """
        Perform a hybrid search using both keyword and vector similarity.

        Parameters:
        - text_query: Keyword search query (None or empty for no keyword filtering).
        - embedding: Vector embedding for similarity search (None for text-only search).
        - top_k: Number of top results to return from vector search (and merged results).

        Returns:
        - List of matching documents (with their fields) sorted by relevance.
        """
        if text_query is None:
            text_query = "*"  # Use wildcard to match all if no text query.
        # Base search URL (using POST for complex queries).
        url = f"{self.base_url}/indexes/{self.index_name}/docs/search?api-version={self.api_version}"
        body = {
            "search": text_query,
            "top": top_k
        }
        # If embedding provided, include vector query.
        if embedding is not None:
            body["vectorQueries"] = [
                {
                    "kind": "vector",
                    "fields": self.vector_field,
                    "vector": embedding,
                    "k": top_k
                }
            ]
        # Use POST for search; include API key in headers (query key suffices for search).
        response = requests.post(url, headers=self.headers, json=body)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"Search request failed: {response.text}") from e

        # Parse results: Azure returns 'value' list of documents.
        results = response.json()
        return results.get("value", [])

    def delete_document(self, doc_id: str):
        """
        Delete a document by its ID.

        Parameters:
        - doc_id: Identifier of the document to delete.

        Returns:
        - True if deletion succeeded, False if document not found, else raises on error.
        """
        # Azure requires an indexing payload with @search.action = delete.
        document = {
            "@search.action": "delete",
            self.key_field: doc_id
        }
        payload = {"value": [document]}
        url = f"{self.base_url}/indexes/{self.index_name}/docs/index?api-version={self.api_version}"
        response = requests.post(url, headers=self.headers, json=payload)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"Delete failed: {response.text}") from e

        result = response.json()
        if ("value" in result and len(result["value"]) > 0):
            status_entry = result["value"][0]
            if status_entry.get("status") is True:
                return True
            # If document not found, Azure returns status false and 404 code.
            if status_entry.get("statusCode") == 404:
                return False
            # Other errors
            raise RuntimeError(f"Delete error: {status_entry}")
        # If no detailed info, assume failure
        return False

    def get_document(self, doc_id: str):
        """
        Retrieve a document by its ID (lookup operation).

        Parameters:
        - doc_id: Identifier of the document to retrieve.

        Returns:
        - Document (dict) if found, or None if not found.
        """
        # Use lookup API (GET). Need to quote the key to handle special chars.
        key_param = quote(doc_id, safe='')
        url = f"{self.base_url}/indexes/{self.index_name}/docs/{key_param}?api-version={self.api_version}"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 404:
            return None  # Document not found.
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"Lookup failed: {response.text}") from e
        return response.json()

    def list_documents(self, batch_size: int = 1000):
        """
        List all documents in the index.

        Parameters:
        - batch_size: Number of documents to retrieve per request (max 1000).

        Returns:
        - List of all documents in the index.
        """
        # Azure Search returns a maximum of 1000 results per query. Use '*' to match all docs.
        all_docs = []
        skip = 0
        while True:
            url = f"{self.base_url}/indexes/{self.index_name}/docs/search?api-version={self.api_version}"
            body = {
                "search": "*",    # Wildcard search to get all docs.
                "select": "*",    # Retrieve all fields (fields must be marked retrievable).
                "top": batch_size,
                "skip": skip
            }
            response = requests.post(url, headers=self.headers, json=body)
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                raise RuntimeError(f"List documents failed: {response.text}") from e
            results = response.json()
            docs = results.get("value", [])
            if not docs:
                break
            all_docs.extend(docs)
            # Check for continuation token or manual skip
            if "@odata.nextLink" in results or len(docs) == batch_size:
                skip += batch_size
                continue
            break
        return all_docs
