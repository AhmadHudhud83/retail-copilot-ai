import os
import sqlite3
import requests
import json

# Paths
DATA_DIR = "data"
DOCS_DIR = "docs"
DB_PATH = os.path.join(DATA_DIR, "northwind.sqlite")
EVAL_FILE = "sample_questions_hybrid_eval.jsonl"

def setup_directories():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)
    print(f"✅ Directories created: {DATA_DIR}, {DOCS_DIR}")

def download_database():
    url = "https://raw.githubusercontent.com/jpwhite3/northwind-SQLite3/main/dist/northwind.db"
    if not os.path.exists(DB_PATH):
        print("⬇️  Downloading Northwind Database...")
        r = requests.get(url)
        with open(DB_PATH, 'wb') as f:
            f.write(r.content)
        print("✅ Database downloaded.")
    else:
        print("ℹ️  Database already exists.")

def create_db_views():
    views_sql = """
    CREATE VIEW IF NOT EXISTS orders AS SELECT * FROM Orders;
    CREATE VIEW IF NOT EXISTS order_items AS SELECT * FROM "Order Details";
    CREATE VIEW IF NOT EXISTS products AS SELECT * FROM Products;
    CREATE VIEW IF NOT EXISTS customers AS SELECT * FROM Customers;
    """
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(views_sql)
    conn.close()
    print("✅ Database views created (lowercase aliases).")

def create_documents():
    # Updated dates to match actual data range
    docs = {
        "marketing_calendar.md": """# Northwind Marketing Calendar (2016)
## Summer Beverages 2016
- Dates: 2016-07-01 to 2016-07-31
- Notes: Focus on Beverages and Condiments.
## Winter Classics 2016
- Dates: 2016-12-01 to 2016-12-31
- Notes: Push Dairy Products and Confections for holiday gifting.""",
        
        "kpi_definitions.md": """# KPI Definitions
## Average Order Value (AOV)
- AOV = SUM(UnitPrice * Quantity * (1 - Discount)) / COUNT(DISTINCT OrderID)
## Gross Margin
- GM = SUM((UnitPrice - CostOfGoods) * Quantity * (1 - Discount))
- If cost is missing, approximate with category-level average (document your approach).""",
        
        "catalog.md": """# Catalog Snapshot
- Categories include Beverages, Condiments, Confections, Dairy Products, Grains/Cereals, Meat/Poultry, Produce, Seafood.
- Products map to categories as in the Northwind DB.""",
        
        "product_policy.md": """# Returns & Policy
- Perishables (Produce, Seafood, Dairy): 3–7 days.
- Beverages unopened: 14 days; opened: no returns.
- Non-perishables: 30 days."""
    }
    
    for filename, content in docs.items():
        with open(os.path.join(DOCS_DIR, filename), "w", encoding="utf-8") as f:
            f.write(content)
    print("✅ Markdown documents created in docs/")

def create_eval_file():
    # Updated date ranges to match actual orders in DB
    questions = [
        {"id":"rag_policy_beverages_return_days",
         "question":"According to the product policy, what is the return window (days) for unopened Beverages? Return an integer.",
         "format_hint":"int"},
        
        {"id":"hybrid_top_category_qty_summer_2016",
         "question":"During 'Summer Beverages 2016' as defined in the marketing calendar, which product category had the highest total quantity sold? Return {category:str, quantity:int}.",
         "format_hint":"{category:str, quantity:int}"},
        
        {"id":"hybrid_aov_winter_2016",
         "question":"Using the AOV definition from the KPI docs, what was the Average Order Value during 'Winter Classics 2016'? Return a float rounded to 2 decimals.",
         "format_hint":"float"},
        
        {"id":"sql_top3_products_by_revenue_alltime",
         "question":"Top 3 products by total revenue all-time. Revenue uses Order Details: SUM(UnitPrice*Quantity*(1-Discount)). Return list[{product:str, revenue:float}].",
         "format_hint":"list[{product:str, revenue:float}]"},
        
        {"id":"hybrid_revenue_beverages_summer_2016",
         "question":"Total revenue from the 'Beverages' category during 'Summer Beverages 2016' dates. Return a float rounded to 2 decimals.",
         "format_hint":"float"},
        
        {"id":"hybrid_best_customer_margin_2016",
         "question":"Per the KPI definition of gross margin, who was the top customer by gross margin in 2016? Assume CostOfGoods is approximated by 70% of UnitPrice if not available. Return {customer:str, margin:float}.",
         "format_hint":"{customer:str, margin:float}"}
    ]
    
    with open(EVAL_FILE, 'w') as f:
        for q in questions:
            f.write(json.dumps(q) + "\n")
    print(f"✅ Eval file created: {EVAL_FILE}")

if __name__ == "__main__":
    setup_directories()
    download_database()
    create_db_views()
    create_documents()
    create_eval_file()
    print("\n🚀 Setup Complete! You are ready to build.")
