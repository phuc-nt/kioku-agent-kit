import sqlite3
import json

path = "/Users/phucnt/.kioku/data/kioku_fts.db"
conn = sqlite3.connect(path)
cur = conn.cursor()
try:
    cur.execute("ALTER TABLE memories ADD COLUMN tags TEXT DEFAULT '[]'")
    conn.commit()
    print("Tags column added")
except Exception as e:
    print(e)
conn.close()
