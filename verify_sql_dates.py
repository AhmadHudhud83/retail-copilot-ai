import sqlite3
DB_PATH = "data/northwind.sqlite"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# 1️⃣ أعلى و أقل تاريخ موجود في orders
cur.execute("SELECT MIN(OrderDate), MAX(OrderDate) FROM orders;")
print("Order date range:", cur.fetchall())

# 2️⃣ عدد الصفوف في order_items
cur.execute("SELECT COUNT(*) FROM order_items;")
print("Total order_items rows:", cur.fetchall())

# 3️⃣ تحقق من وجود المنتجات حسب CategoryName
cur.execute("""
SELECT DISTINCT p.CategoryID, c.CategoryName
FROM products p
JOIN categories c ON p.CategoryID = c.CategoryID;
""")
print("Categories:", cur.fetchall())


# 4️⃣ مثال: أول 5 أوامر مع تفاصيل
cur.execute("""
SELECT o.OrderID, o.OrderDate, od.ProductID, od.Quantity, od.UnitPrice
FROM orders o
JOIN order_items od ON o.OrderID = od.OrderID
LIMIT 5;
""")
print("Sample orders:", cur.fetchall())

conn.close()
