from sentence_transformers import SentenceTransformer, util
import faiss
import numpy as np
import os
import re
import pickle
from pdf_processing import process_uploaded_pdfs
from models import model
from llm import guess_document_type, split_text, split_text_by_sections

MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
# MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
INDEX_DIR = "data/embeddings"
# INDEX_PATH = "data/embeddings/index.faiss"
# METADATA_PATH = "data/embeddings/metadata.pkl"

# Load model
model = SentenceTransformer(MODEL_NAME)

# FAISS is Approximate Nearest Neighbor (ANN) search library. 벡터 중 쿼리와 유사한 벡터값 찾기.근사값기준으로 top_k 청크 추출.
# It is vector search library, it is fast. but not the most accurate.
# semantic re-ranking is needed for better accuracy. FAISS가 가져온 top_k 청크를 다시 정렬하는 것.query_embedding과 각각의 chunk_embedding 사이의 cosine similarity 재계산.가장 의미적으로 가까운 순서로 정렬 
# cosine similarity is used for semantic search.
# FAISS supports inner product and L2 distance.
# To use cosine similarity with FAISS, normalize all vectors and use inner product.

# total docs contents (vector embedding)
# numerous embedded vectors (FAISS)
# Top 30 chunks (semantic search) -> re-ranking (cosine similarity)
# -> top 8 chunks (final answer)
# -> generate final answer (LLM)



# now changing the indexing for individual pdf files. individual FAISS and pkl


def create_index():
    return faiss.IndexFlatL2(768)

def save_individual_index(pdf_filename, index, metadata):
    index_path = os.path.join(INDEX_DIR, f"{pdf_filename}.faiss")
    meta_path = os.path.join(INDEX_DIR, f"{pdf_filename}.pkl")
    faiss.write_index(index, index_path)
    with open(meta_path, "wb") as f:
        pickle.dump(metadata, f)

# def save_index(index, metadata):
#     os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
#     faiss.write_index(index, INDEX_PATH)
#     with open(METADATA_PATH, "wb") as f:
#         pickle.dump(metadata, f)

def load_individual_index(pdf_filename):
    index_path = os.path.join(INDEX_DIR, f"{pdf_filename}.faiss")
    meta_path = os.path.join(INDEX_DIR, f"{pdf_filename}.pkl")
    if not os.path.exists(index_path):
        return create_index(), []
    index = faiss.read_index(index_path)
    with open(meta_path, "rb") as f:
        metadata = pickle.load(f)
    return index, metadata

# def load_index():
#     if not os.path.exists(INDEX_PATH):
#         return create_index(), []
#     index = faiss.read_index(INDEX_PATH)
#     with open(METADATA_PATH, "rb") as f:
#         metadata = pickle.load(f)
#     return index, metadata

def embed_and_store_individual(text_data):
    for item in text_data:
        index, metadata = create_index(), []
        text = item["text"]
        if not text.strip():
            continue
        
        doc_type = guess_document_type(text)
        has_sections = bool(re.search(r'\b\d+(\.\d+)*\s+[^\n]+', text))

        if doc_type == "academic" and has_sections:
            chunks = split_text_by_sections(text)

        else:
            chunks = split_text(text)
        # chunks = split_text_by_sections(text) if doc_type == "academic" else split_text(text)

        embeddings = model.encode(chunks)
        index.add(np.array(embeddings))
        metadata.extend([{"filename": item["filename"], "chunk": chunk, "doc_type": doc_type} for chunk in chunks])

        save_individual_index(item["filename"], index, metadata)

# def embed_and_store(text_data):
#     index, metadata = load_index()
#     for item in text_data:
#         text = item["text"]
#         if not text.strip():
#             continue
        
#         doc_type = guess_document_type(text)
#         print(f"\n\n>> Document type: {doc_type}\n\n")
#         if doc_type == "academic":
#             chunks = split_text_by_sections(text)
#         else:
#             chunks = split_text(text)

#         embeddings = model.encode(chunks)
#         index.add(np.array(embeddings))
#         metadata.extend([{"filename": item["filename"], "chunk": chunk, "doc_type": doc_type} for chunk in chunks])
#     save_index(index, metadata)


def search_unified(query, filenames, top_k=50):
    query_vec = model.encode([query])
    combined_chunks = []

    for filename in filenames:
        index, metadata = load_individual_index(filename)
        if len(metadata) == 0:
            continue
        D, I = index.search(np.array(query_vec), top_k)
        results = [metadata[i] for i in I[0] if i < len(metadata)]
        combined_chunks.extend(results)

    return combined_chunks[:top_k]

# def search(query, top_k=10):
#     index, metadata = load_index()
#     query_vec = model.encode([query])
#     D, I = index.search(np.array(query_vec), top_k)
#     return [metadata[i] for i in I[0] if i < len(metadata)]

# def search_with_keywords(query, metadata, top_k=10):
#     query_vec = model.encode([query])
#     index = create_index()
#     chunks = []
#     for item in metadata:
#         embedding = model.encode([item["chunk"]])
#         index.add(np.array(embedding))
#         chunks.append(item)
    
#     D, I = index.search(np.array(query_vec), top_k)
#     return [chunks[i] for i in I[0] if i < len(chunks)]


def store_embedding_for_pdf(pdf_path: str):
    text_data = process_uploaded_pdfs(os.path.dirname(pdf_path))
    embed_and_store_individual(text_data)
    # embed_and_store(text_data)




