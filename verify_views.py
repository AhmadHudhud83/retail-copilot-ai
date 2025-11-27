import sqlite3

DB_PATH = "data/northwind.sqlite"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("All views found:")
cursor.execute("""
    SELECT name 
    FROM sqlite_master 
    WHERE type='view';
""")
views = cursor.fetchall()

if not views:
    print("No views found in this DB at all.")
else:
    for v in views:
        print("-", v[0])

conn.close()
