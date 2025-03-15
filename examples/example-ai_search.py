import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend import config  # NoQA
from backend.interfaces.azure_ai_search import AzureSearchClient  # NoQA

search_client = AzureSearchClient(
    service_url=config.AZURE_AI_SEARCH_SERVICE,
    index_name="ticket_index",
    api_key=config.AZURE_AI_SEARCH_API_KEY,
    api_version=config.AZURE_AI_API_VERSION,
    vector_field="vector"
)

# Upload document with vector
# embedding = [0.5] * 1536  # A dummy 1536-dimensional vector
# metadata = {"id":"id6", "title": "title6", "status": "open"}
# search_client.upload_document(doc_id=metadata["id"], embedding=embedding, metadata=metadata)

# all_docs = search_client.list_documents(batch_size=1000)
# print(f"Retrieved {len(all_docs)} documents from the index.")
# print(all_docs)

# Hybrid search: keyword + vector
# query_embedding = [0.1] * 1536
# results = search_client.hybrid_search(text_query="wireless network", embedding=query_embedding, top_k=10)
# for doc in results:
#     print(doc["id"], doc.get("title"), doc.get("@search.score"))


text_query = "Do you have a different solution, or did someo"
results = search_client.fulltext_search(text_query=text_query, top_k=10)
for doc in results:
    print(doc["id"], doc.get("ticket_id"), doc.get("title"), doc.get("@search.score"))
