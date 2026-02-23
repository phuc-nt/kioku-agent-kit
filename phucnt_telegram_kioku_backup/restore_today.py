import os
from pathlib import Path
import hashlib
import sys

# Ensure kioku package can be imported if script is run directly
sys.path.append(str(Path(__file__).parent.parent / "src"))

from kioku.config import settings
from kioku.storage.markdown import read_entries

def restore_today():
    print(f"Starting restoration for User ID: {settings.user_id}")
    
    target_memory_dir = settings.memory_dir
    target_data_dir = settings.data_dir
    
    print(f"Target Memory Dir: {target_memory_dir}")
    print(f"Target Data Dir: {target_data_dir}")
    print("-" * 40)
    
    # 3. Re-index
    from kioku.service import KiokuService
    svc = KiokuService()
    
    date_str = "2026-02-23"
    entries = read_entries(target_memory_dir, date=date_str)
    print(f"Re-indexing {len(entries)} entries for date {date_str}...")
    
    for idx, e in enumerate(entries):
        print(f"  -> Processing entry {idx+1}/{len(entries)}")
        
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
    restore_today()
