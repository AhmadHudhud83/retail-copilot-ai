import sqlite3

# Connect to your SQLite database
conn = sqlite3.connect("data/northwind.sqlite")
cursor = conn.cursor()

# 1. Scan min/max OrderDate in orders
cursor.execute("SELECT MIN(OrderDate), MAX(OrderDate) FROM orders;")
min_date, max_date = cursor.fetchone()
print(f"Data range in orders table: {min_date} -> {max_date}\n")

# Define queries with placeholders for dates if needed
queries = {
    "top_category_qty_summer": f"""
        SELECT c.CategoryName, SUM(oi.Quantity) AS TotalQuantity
        FROM order_items oi
        JOIN products p ON oi.ProductID = p.ProductID
        JOIN categories c ON p.CategoryID = c.CategoryID
        JOIN orders o ON oi.OrderID = o.OrderID
        WHERE o.OrderDate BETWEEN '{min_date}' AND '{max_date}'
        GROUP BY c.CategoryName
        ORDER BY TotalQuantity DESC
        LIMIT 1;
    """,
    "aov_winter": f"""
        SELECT ROUND(SUM(oi.UnitPrice * oi.Quantity * (1 - oi.Discount)) / COUNT(DISTINCT oi.OrderID), 2) AS AverageOrderValue
        FROM order_items oi
        JOIN orders o ON oi.OrderID = o.OrderID
        WHERE o.OrderDate BETWEEN '{min_date}' AND '{max_date}';
    """,
    "revenue_beverages": f"""
        SELECT SUM(oi.UnitPrice * oi.Quantity * (1-oi.Discount)) AS Revenue
        FROM order_items oi
        JOIN orders o ON oi.OrderID = o.OrderID
        JOIN products p ON oi.ProductID = p.ProductID
        JOIN categories c ON p.CategoryID = c.CategoryID
        WHERE c.CategoryName = 'Beverages'
          AND o.OrderDate BETWEEN '{min_date}' AND '{max_date}';
    """,
    "top_customer_margin": f"""
        SELECT c.CustomerID, SUM((oi.UnitPrice * (1 - oi.Discount) * oi.Quantity) - COALESCE(oi.UnitPrice * 0.7 * oi.Quantity,0)) AS gross_margin
        FROM order_items oi
        JOIN orders o ON oi.OrderID = o.OrderID
        LEFT JOIN customers c ON o.CustomerID = c.CustomerID
        WHERE o.OrderDate BETWEEN '{min_date}' AND '{max_date}'
        GROUP BY c.CustomerID
        ORDER BY gross_margin DESC
        LIMIT 1;
    """
}

# Execute queries and print results
for name, query in queries.items():
    print(f"=== Executing query: {name} ===")
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        print(f"Result ({len(rows)} rows):")
        for row in rows:
            print(row)
    except sqlite3.Error as e:
        print(f"Error executing query {name}: {e}")
    print("\n")

conn.close()
