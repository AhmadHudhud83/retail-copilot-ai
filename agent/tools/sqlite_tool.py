import sqlite3
import pandas as pd
from typing import List, Dict, Any, Union

class NorthwindDB:
    def __init__(self, db_path: str = "data/northwind.sqlite"):
        self.db_path = db_path

    def get_connection(self):
        """Creates a read-only connection to the DB."""
        # URI mode for read-only to prevent accidental data modification
        return sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)

    def get_schema(self) -> str:
        """
        Returns a compressed text representation of the DB schema 
        for the LLM to understand.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # We only care about the views we created or main tables
        target_tables = ['orders', 'order_items', 'products', 'customers', 'categories', 'suppliers']
        
        schema_str = []
        
        for table in target_tables:
            # Get column info: cid, name, type, notnull, dflt_value, pk
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            
            if not columns:
                continue
                
            col_strs = [f"{col[1]} ({col[2]})" for col in columns]
            schema_str.append(f"Table: {table}")
            schema_str.append(f"Columns: {', '.join(col_strs)}")
            schema_str.append("") # Empty line separator

        conn.close()
        return "\n".join(schema_str)

    def execute_query(self, sql: str) -> Union[List[Dict[str, Any]], str]:
        """
        Executes a SQL query and returns results as a list of dicts.
        Returns a string error message if execution fails.
        """
        try:
            conn = self.get_connection()
            # pandas is great here because it handles headers automatically
            df = pd.read_sql_query(sql, conn)
            conn.close()
            
            if df.empty:
                return []
            
            return df.to_dict(orient="records")
            
        except Exception as e:
            return f"SQL Error: {str(e)}"

# Simple test to verify it works
if __name__ == "__main__":
    db = NorthwindDB()
    print("--- Schema ---")
    print(db.get_schema())
    print("\n--- Test Query ---")
    print(db.execute_query("SELECT ProductName FROM products LIMIT 3"))