import os
import shutil
from pathlib import Path
import redis
import chromadb
import hashlib

from kioku.config import settings
from kioku.storage.markdown import read_entries

print(f"Targeting user_id: {settings.user_id}")
print(f"Memory dir: {settings.memory_dir}")

date = "2026-02-22"
entries = read_entries(settings.memory_dir, date)
print(f"Loaded {len(entries)} entries before filtering.")

good_entries = []
for e in entries:
    txt = e.text.lower()
    # Filter out dummy / mock data
    if "mai" in txt and "openclaw" in txt: continue
    if "hùng" in txt and "kioku" in txt: continue
    if "phở thin" in txt: continue
    if "minh" in txt and "deadlift" in txt: continue
    
    good_entries.append(e)

print(f"Keeping {len(good_entries)} actual user entries.")

# Rewrite markdown
md_path = settings.memory_dir / f"{date}.md"
with open(md_path, "w") as f:
    f.write(f"# Kioku — {date}\n\n")
    for e in good_entries:
        f.write("---\n")
        f.write(f'time: "{e.timestamp}"\n')
        f.write(f'mood: "{e.mood}"\n')
        f.write(f"tags: {e.tags}\n")
        f.write("---\n")
        f.write(f"{e.text}\n\n")

print(f"Cleaned {md_path}")

# Drop DBs
fts_db = settings.sqlite_path
if fts_db.exists():
    os.remove(fts_db)
    print("Deleted SQLite FTS DB")

client = chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
try:
    client.delete_collection(settings.chroma_collection)
    print(f"Deleted Chroma Collection {settings.chroma_collection}")
except Exception as e:
    print("Chroma skip:", e)

r = redis.Redis(host=settings.falkordb_host, port=settings.falkordb_port, decode_responses=True)
if r.exists(settings.falkordb_graph):
    r.delete(settings.falkordb_graph)
    print(f"Deleted Falkor Graph {settings.falkordb_graph}")

# Reindex using server tools
from kioku.server import vector_store, graph_store, extractor, embedder
from kioku.pipeline.keyword_writer import KeywordIndex

# Re-init SQLite because we deleted the file
keyword_index = KeywordIndex(fts_db)

print("Starting background re-indexing into DBs (this will hit LLM for extraction)...")
for idx, e in enumerate(good_entries):
    print(f"Reindexing {idx+1}/{len(good_entries)}...")
    content_hash = hashlib.sha256(e.text.encode()).hexdigest()
    
    keyword_index.index(
        content=e.text,
        date=date,
        timestamp=e.timestamp,
        mood=e.mood,
        content_hash=content_hash
    )
    
    vector_store.add(
        content=e.text,
        date=date,
        timestamp=e.timestamp,
        mood=e.mood,
        tags=e.tags
    )
    
    extraction = extractor.extract(e.text)
    if extraction and (extraction.entities or extraction.relationships):
        graph_store.upsert(extraction, date, e.timestamp)

print("Finished clean and re-index!")
