import sqlite3
import re

class NorthwindDB:
    def __init__(self, db_path="data/northwind.sqlite"):
        self.db_path = db_path

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def get_schema(self):
        """
        Returns a compact schema string focusing on the lowercase views 
        to help the LLM avoid quoting hell.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # We focus on the views we created in the setup
        target_tables = ['orders', 'order_items', 'products', 'customers', 'categories', 'suppliers']
        schema_str = ""

        for table in target_tables:
            # Check if table/view exists first
            try:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                if columns:
                    col_str = ", ".join([f"{col[1]} ({col[2]})" for col in columns])
                    schema_str += f"Table '{table}': [{col_str}]\n"
            except:
                continue
                
        conn.close()
        return schema_str

    def execute_query(self, query: str):
        # 1. Safety Sanity Check
        if not query or not query.strip():
            return "SQL Error: Empty query"
            
        # 2. Hard-Fix Common Hallucinations (Safety Net)
        # Phi-3.5 loves YEAR() but SQLite hates it.
        if "YEAR(" in query:
            query = re.sub(r"YEAR\(([^)]+)\)", r"strftime('%Y', \1)", query)
        if "MONTH(" in query:
            query = re.sub(r"MONTH\(([^)]+)\)", r"strftime('%m', \1)", query)
            
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            # Get column names
            headers = [description[0] for description in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            conn.close()
            
            # Return list of dicts for easier processing
            results = []
            for row in rows:
                results.append(dict(zip(headers, row)))
            return results
            
        except sqlite3.Error as e:
            conn.close()
            return f"SQL Error: {str(e)}"