import os
import shutil
from pathlib import Path
import chromadb
from falkordb import FalkorDB
import redis

def migrate():
    print("Migrating memory and data files...")
    
    # 1. Move folders
    old_mem = Path(os.path.expanduser("~/.kioku/memory"))
    old_data = Path(os.path.expanduser("~/.kioku/data"))
    
    new_mem = Path(os.path.expanduser("~/.kioku/users/telegram/memory"))
    new_data = Path(os.path.expanduser("~/.kioku/users/telegram/data"))
    
    new_mem.parent.mkdir(parents=True, exist_ok=True)
    
    if old_mem.exists() and not new_mem.exists():
        shutil.move(str(old_mem), str(new_mem))
        print(f"Moved {old_mem} to {new_mem}")
    
    if old_data.exists() and not new_data.exists():
        shutil.move(str(old_data), str(new_data))
        print(f"Moved {old_data} to {new_data}")
        
    print("Migrating Vector DB (Chroma)...")
    # 2. Migrate ChromaDB
    client = chromadb.HttpClient(host="localhost", port=8000)
    try:
        old_col = client.get_collection("memories")
        print("Found old 'memories' collection.")
        
        # If new collection exists, we might want to drop it to avoid mixing with previous test data
        try:
            client.delete_collection("memories_telegram")
            print("Dropped intermediate test collection 'memories_telegram'")
        except Exception:
            pass
            
        new_col = client.create_collection("memories_telegram", metadata={"hnsw:space": "cosine"})
        
        data = old_col.get(include=["embeddings", "metadatas", "documents"])
        if data["ids"]:
            new_col.add(
                ids=data["ids"],
                embeddings=data["embeddings"],
                metadatas=data["metadatas"],
                documents=data["documents"]
            )
            print(f"Migrated {len(data['ids'])} vectors to 'memories_telegram'")
        
        client.delete_collection("memories")
        print("Deleted old 'memories' collection")
    except Exception as e:
        print(f"ChromaDB migration info: {e}")
        
    print("Migrating Knowledge Graph (FalkorDB)...")
    # 3. Migrate FalkorDB by renaming the redis key
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    if r.exists("kioku"):
        if r.exists("kioku_kg_telegram"):
            r.delete("kioku_kg_telegram")
            print("Dropped intermediate test graph 'kioku_kg_telegram'")
        r.rename("kioku", "kioku_kg_telegram")
        print("Renamed graph 'kioku' to 'kioku_kg_telegram'")
    else:
        print("Old graph 'kioku' not found.")
        
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
