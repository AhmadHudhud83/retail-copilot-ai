import sqlite3

# ==========================
# CONFIG
# ==========================
DB_PATH = "data/northwind.sqlite"

# ==========================
# HELPERS
# ==========================
def connect_db(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def execute_sql(conn, query, params=None):
    params = params or {}
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    return [dict(row) for row in rows]

# ==========================
# SQL QUERIES
# ==========================

# 1. Top 3 products by revenue all-time
SQL_TOP3_PRODUCTS = """
SELECT 
    p.ProductName AS product,
    ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) AS revenue
FROM "Order Details" od
JOIN Products p ON p.ProductID = od.ProductID
GROUP BY p.ProductID
ORDER BY revenue DESC
LIMIT 3;
"""

# 2. Total revenue for Beverages during Summer Beverages 2016
SQL_REVENUE_BEVERAGES_SUMMER_2016 = """
SELECT 
    ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)), 2) AS revenue
FROM "Order Details" od
JOIN Orders o ON o.OrderID = od.OrderID
JOIN Products p ON p.ProductID = od.ProductID
JOIN Categories c ON c.CategoryID = p.CategoryID
WHERE c.CategoryName = 'Beverages'
  AND o.OrderDate BETWEEN '2016-07-01' AND '2016-07-31';
"""

# 3. Top customer by gross margin in 2016
SQL_TOP_CUSTOMER_MARGIN_2016 = """
SELECT 
    c.CompanyName AS customer,
    ROUND(SUM((od.UnitPrice - od.UnitPrice*0.7) * od.Quantity * (1 - od.Discount)), 2) AS margin
FROM "Order Details" od
JOIN Orders o ON o.OrderID = od.OrderID
JOIN Customers c ON c.CustomerID = o.CustomerID
WHERE o.OrderDate BETWEEN '2016-01-01' AND '2016-12-31'
GROUP BY c.CustomerID
ORDER BY margin DESC
LIMIT 1;
"""

# 4. AOV Winter Classics 2016
SQL_AOV_WINTER_2016 = """
SELECT 
    ROUND(
        SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) * 1.0 / COUNT(DISTINCT o.OrderID),
        2
    ) AS aov
FROM "Order Details" od
JOIN Orders o ON o.OrderID = od.OrderID
WHERE o.OrderDate BETWEEN '2016-12-01' AND '2016-12-31';
"""

# 5. Top category by quantity during Summer Beverages 2016
SQL_TOP_CATEGORY_QTY_SUMMER_2016 = """
SELECT 
    c.CategoryName AS category,
    SUM(od.Quantity) AS quantity
FROM "Order Details" od
JOIN Orders o ON o.OrderID = od.OrderID
JOIN Products p ON p.ProductID = od.ProductID
JOIN Categories c ON c.CategoryID = p.CategoryID
WHERE o.OrderDate BETWEEN '2016-07-01' AND '2016-07-31'
GROUP BY c.CategoryID
ORDER BY quantity DESC
LIMIT 1;
"""

# ==========================
# MAIN EXECUTION
# ==========================
if __name__ == "__main__":
    conn = connect_db()

    # --- Top 3 Products ---
    results = execute_sql(conn, SQL_TOP3_PRODUCTS)
    print("=== Top 3 Products by Revenue (All-Time) ===")
    print({"final_answer": results})

    # --- Revenue Beverages Summer 2016 ---
    results = execute_sql(conn, SQL_REVENUE_BEVERAGES_SUMMER_2016)
    print("\n=== Revenue Beverages Summer 2016 ===")
    print({"final_answer": results[0]['revenue']})

    # --- Top Customer by Gross Margin 2016 ---
    results = execute_sql(conn, SQL_TOP_CUSTOMER_MARGIN_2016)
    print("\n=== Top Customer by Gross Margin 2016 ===")
    print({"final_answer": {"customer": results[0]['customer'], "margin": results[0]['margin']}})

    # --- AOV Winter 2016 ---
    results = execute_sql(conn, SQL_AOV_WINTER_2016)
    print("\n=== AOV Winter Classics 2016 ===")
    print({"final_answer": results[0]['aov']})

    # --- Top Category Qty Summer 2016 ---
    results = execute_sql(conn, SQL_TOP_CATEGORY_QTY_SUMMER_2016)
    print("\n=== Top Category by Quantity Summer Beverages 2016 ===")
    print({"final_answer": {"category": results[0]['category'], "quantity": results[0]['quantity']}})

    conn.close()
