import chromadb
from pathlib import Path
from backend.config import cfg

_chroma_path = str(Path(__file__).parent.parent.parent / cfg['paths']['chroma_dir'])
chroma = chromadb.PersistentClient(path=_chroma_path)

COLLECTIONS = [
    'jobflow_decisions',
    'jobflow_messages',
    'jobflow_profiles',
    'jobflow_briefings',
    'jobflow_stories',
]


def get_collection(name: str):
    return chroma.get_or_create_collection(name)


def embed(collection: str, doc_id: str, text: str, metadata: dict) -> str:
    get_collection(collection).upsert(
        ids=[doc_id],
        documents=[text],
        metadatas=[metadata]
    )
    return doc_id


def search(collection: str, query: str, n: int = None) -> list:
    n = n or cfg['memory']['semantic_search_results']
    col = get_collection(collection)
    # Handle case where collection has fewer documents than n
    try:
        count = col.count()
        if count == 0:
            return []
        n = min(n, count)
        results = col.query(query_texts=[query], n_results=n)
    except Exception:
        return []

    output = []
    ids = results.get('ids', [[]])[0]
    docs = results.get('documents', [[]])[0]
    metas = results.get('metadatas', [[]])[0]
    distances = results.get('distances', [[]])[0]

    for i, doc_id in enumerate(ids):
        output.append({
            'id': doc_id,
            'text': docs[i] if i < len(docs) else '',
            'metadata': metas[i] if i < len(metas) else {},
            'distance': distances[i] if i < len(distances) else None,
        })
    return output


def get_by_id(collection: str, doc_id: str):
    try:
        result = get_collection(collection).get(ids=[doc_id])
        if result['ids']:
            return {
                'id': result['ids'][0],
                'text': result['documents'][0] if result.get('documents') else '',
                'metadata': result['metadatas'][0] if result.get('metadatas') else {},
            }
    except Exception:
        pass
    return None


def delete(collection: str, doc_id: str):
    get_collection(collection).delete(ids=[doc_id])
