import os
import shutil
from pathlib import Path
import redis
import chromadb
import hashlib
import sys

# Ensure kioku package can be imported if script is run directly
sys.path.append(str(Path(__file__).parent.parent / "src"))

from kioku.config import settings
from kioku.storage.markdown import read_entries

def restore():
    print(f"Starting restoration for User ID: {settings.user_id}")
    
    backup_dir = Path(__file__).parent / "memory"
    if not backup_dir.exists():
        print(f"Error: Backup directory {backup_dir} not found.")
        sys.exit(1)
        
    target_memory_dir = settings.memory_dir
    target_data_dir = settings.data_dir
    
    print(f"Target Memory Dir: {target_memory_dir}")
    print(f"Target Data Dir: {target_data_dir}")
    print("-" * 40)
    
    # 1. Copy markdown files
    target_memory_dir.mkdir(parents=True, exist_ok=True)
    target_data_dir.mkdir(parents=True, exist_ok=True)
    
    md_files = list(backup_dir.glob("*.md"))
    print(f"Found {len(md_files)} Markdown files to restore.")
    
    for f in md_files:
        dest = target_memory_dir / f.name
        shutil.copy2(f, dest)
        print(f"Copied {f.name}")
        
    print("-" * 40)
    print("Dropping existing databases to avoid duplication...")
    
    # 2. Drop databases
    fts_db = settings.sqlite_path
    if fts_db.exists():
        os.remove(fts_db)
        print(f"Deleted SQLite DB: {fts_db}")
        
    try:
        client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
        client.delete_collection(settings.chroma_collection)
        print(f"Deleted Chroma Collection: {settings.chroma_collection}")
    except Exception as e:
        print(f"Chroma DB (might not exist): {e}")
        
    try:
        r = redis.Redis(host=settings.falkordb_host, port=settings.falkordb_port, decode_responses=True)
        if r.exists(settings.falkordb_graph):
            r.delete(settings.falkordb_graph)
            print(f"Deleted Falkor Graph: {settings.falkordb_graph}")
    except Exception as e:
        print(f"Falkor DB: {e}")
        
    print("-" * 40)
    print("Re-indexing data using LLM and Embedders. This might take a while...")
    
    # 3. Re-index
    from kioku.service import KiokuService
    svc = KiokuService()
    
    from kioku.pipeline.keyword_writer import KeywordIndex
    keyword_index = KeywordIndex(fts_db)
    
    for md_file in md_files:
        date_str = md_file.stem
        entries = read_entries(target_memory_dir, date=date_str)
        print(f"Re-indexing {len(entries)} entries for date {date_str}...")
        
        for idx, e in enumerate(entries):
            print(f"  -> Processing entry {idx+1}/{len(entries)}")
            content_hash = hashlib.sha256(e.text.encode()).hexdigest()
            
            # Index to SQLite Full-text search
            keyword_index.index(
                content=e.text,
                date=date_str,
                timestamp=e.timestamp,
                mood=e.mood,
                content_hash=content_hash
            )
            
            # Index to ChromaDB Vector Store
            svc.vector_store.add(
                content=e.text,
                date=date_str,
                timestamp=e.timestamp,
                mood=e.mood,
                tags=e.tags
            )
            
            # Extract Graph data via LLM and save to FalkorDB
            extraction = svc.extractor.extract(e.text)
            if extraction and (extraction.entities or extraction.relationships):
                svc.graph_store.upsert(extraction, date_str, e.timestamp)
                
    print("-" * 40)
    print("✅ Restoration and Re-indexing completed successfully!")

if __name__ == "__main__":
    restore()
