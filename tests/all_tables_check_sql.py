import sqlite3
import pandas as pd

# ===============================
# 1. Connect to Northwind SQLite DB
# ===============================
db_path = "data/northwind.sqlite"
conn = sqlite3.connect(db_path)

# ===============================
# 2. Get all tables and views
# ===============================
tables_query = """
SELECT name, type
FROM sqlite_master
WHERE type IN ('table', 'view')
ORDER BY type, name;
"""
tables_and_views = pd.read_sql(tables_query, conn)

print("Tables and Views found:")
print(tables_and_views)

# ===============================
# 3. Inspect sample rows for each
# ===============================
sample_size = 5  # number of rows per table/view

for idx, row in tables_and_views.iterrows():
    name = row['name']
    ttype = row['type']
    print(f"\n===== {ttype.upper()}: {name} =====")
    try:
        sample_df = pd.read_sql(f"SELECT * FROM '{name}' LIMIT {sample_size}", conn)
        print(sample_df)
    except Exception as e:
        print(f"Error reading {name}: {e}")

# ===============================
# 4. Close connection
# ===============================
conn.close()
