# import chromadb
# from chromadb.utils import embedding_functions
# from datetime import datetime
from typing import List, Dict
# import uuid
# import json

MAX_HISTORY_TURNS = 10  # Mỗi turn = user + assistant

def trim_history(history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    # """Giới hạn số lượt trò chuyện trong lịch sử."""
    system = history[:1]
    turns = history[1:]
    return system + turns[-MAX_HISTORY_TURNS * 2:]


# class VectorHistory:
#     def __init__(self):
#         self.client = chromadb.PersistentClient(path="simple_memory/chat_history_db")
#         self.embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
#             model_name="paraphrase-multilingual-MiniLM-L12-v2"
#         )
#         self.collection = self.client.get_or_create_collection(
#             name="chat_history",
#             embedding_function=self.embedder,
#             metadata={"hnsw:space": "cosine"}  # Tối ưu cho semantic search
#         )

#     def add_message(self, session_id: str, message: Dict[str, str]):
#         """Lưu tin nhắn vào VectorDB với metadata đầy đủ"""
#         doc_id = str(uuid.uuid4())
#         metadata = {
#             "role": message["role"],
#             "session_id": session_id,
#             "timestamp": datetime.now().isoformat(),
#             "images": json.dumps(message.get("images", []))
#         }
        
#         self.collection.add(
#             documents=[message["content"]],
#             metadatas=[metadata],
#             ids=[doc_id]
#         )

#     def get_recent_history(self, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
#         """Lấy lịch sử gần nhất theo session (không dùng vector search)"""
#         results = self.collection.get(
#             where={"session_id": session_id},
#             limit=limit,
#             include=["metadatas", "documents"]
#         )
        
#         history = []
#         for doc, meta in zip(results["documents"], results["metadatas"]):
#             history.append({
#                 "role": meta["role"],
#                 "content": doc,
#                 "images": json.loads(meta["images"]),
#                 "timestamp": meta["timestamp"]
#             })
#         recent_history = sorted(history, key=lambda x: x["timestamp"])
#         return [{"role": his["role"], "content": his["content"], "images": his["images"]} for his in recent_history]

#     def search_context(self, session_id: str, query: str, k: int = 3) -> List[str]:
#         """Tìm tin nhắn liên quan trong lịch sử dùng Vector Search"""
#         results = self.collection.query(
#             query_texts=[query],
#             where={"session_id": session_id},  # Chỉ tìm trong session hiện tại
#             n_results=k,
#             include=["documents"]
#         )
#         return results["documents"][0]

# Singleton instance
# vector_history = VectorHistory()
# print(vector_history.get_recent_history("1363497131637211166"))