import dspy
trainset = [
    # ==========================================
    # Example 1: RAG — Beverages return days
    # ==========================================
    dspy.Example(
        question="How many days can I return unopened Beverages?",
        schema_context={},
        context="Check the product_policy document for return durations of different categories.",
        sql_query="",  # No SQL needed
    ).with_inputs("question", "schema_context", "context"),

    # ==========================================
    # Example 2: Hybrid — Top category quantity Summer 1997
    # ==========================================
    dspy.Example(
        question="Which product category had the highest quantity sold during Summer 1997?",
        schema_context={
            "orders": ["OrderID", "OrderDate"],
            "order_items": ["OrderID", "ProductID", "Quantity"],
            "products": ["ProductID", "CategoryID"],
            "categories": ["CategoryID", "CategoryName"]
        },
        context="Join order_items → orders → products → categories; sum quantities for 'Summer 1997' dates.",
        sql_query="""
SELECT c.CategoryName, SUM(od.Quantity) AS TotalQuantity
FROM "order_items" od
JOIN products p ON od.ProductID = p.ProductID
JOIN categories c ON p.CategoryID = c.CategoryID
JOIN orders o ON od.OrderID = o.OrderID
WHERE o."OrderDate" BETWEEN '1997-06-01' AND '1997-08-31'
GROUP BY c.CategoryName
ORDER BY TotalQuantity DESC
LIMIT 1;
        """
    ).with_inputs("question", "schema_context", "context"),

    # ==========================================
    # Example 3: Hybrid — AOV Winter 1997
    # ==========================================
    dspy.Example(
        question="What was the average order value in Winter 1997?",
        schema_context={
            "orders": ["OrderID", "OrderDate"],
            "order_items": ["OrderID", "UnitPrice", "Quantity", "Discount"]
        },
        context="Compute AOV using UnitPrice*Quantity*(1-Discount), for December 1997 orders.",
        sql_query="""
SELECT ROUND(SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) / COUNT(DISTINCT o.OrderID), 2) AS AvgOrderValue
FROM "Order Details" od
JOIN orders o ON od.OrderID = o.OrderID
WHERE strftime('%Y', o.OrderDate) = '1997'
AND strftime('%m-%d', o.OrderDate) BETWEEN '12-01' AND '12-31'
GROUP BY o.OrderID;
        """
    ).with_inputs("question", "schema_context", "context"),

    # ==========================================
    # Example 4: SQL — Top 3 products by revenue all-time
    # ==========================================
    dspy.Example(
        question="Which are the top 3 products by total revenue of all time?",
        schema_context={
            "order_items": ["OrderID", "ProductID", "UnitPrice", "Quantity", "Discount"],
            "products": ["ProductID", "ProductName"]
        },
        context="Sum revenue per product accounting for discounts, order descending, limit 3.",
        sql_query="""
SELECT p.ProductName, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) AS Revenue
FROM "Order Details" od
JOIN products p ON od.ProductID = p.ProductID
GROUP BY p.ProductName
ORDER BY Revenue DESC
LIMIT 3;
        """
    ).with_inputs("question", "schema_context", "context"),

    # ==========================================
    # Example 5: Hybrid — Revenue Beverages Summer 1997
    # ==========================================
    dspy.Example(
        question="What was the total revenue for Beverages during Summer 1997?",
        schema_context={
            "orders": ["OrderID", "OrderDate"],
            "order_items": ["OrderID", "ProductID", "UnitPrice", "Quantity", "Discount"],
            "products": ["ProductID", "CategoryID"],
            "categories": ["CategoryID", "CategoryName"]
        },
        context="Sum revenue for Beverages during Summer 1997 using UnitPrice*Quantity*(1-Discount).",
        sql_query="""
SELECT SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) AS Revenue
FROM "order_items" od
JOIN orders o ON od.OrderID = o.OrderID
JOIN products p ON od.ProductID = p.ProductID
JOIN categories c ON p.CategoryID = c.CategoryID
WHERE c.CategoryName = 'Beverages'
AND o.OrderDate BETWEEN '1997-06-01' AND '1997-06-30';
        """
    ).with_inputs("question", "schema_context", "context"),

    # ==========================================
    # Example 6: Hybrid — Best customer margin 1997
    # ==========================================
    dspy.Example(
        question="Which customer had the highest gross margin in 1997?",
        schema_context={
            "orders": ["OrderID", "CustomerID", "OrderDate"],
            "order_items": ["OrderID", "UnitPrice", "Quantity", "Discount"],
            "customers": ["CustomerID"]
        },
        context="Compute gross margin per customer using UnitPrice*Quantity*(1-Discount) minus estimated COGS (70% of UnitPrice if missing).",
        sql_query="""
SELECT c.CustomerID, SUM((od.UnitPrice * (1 - od.Discount) * od.Quantity) - COALESCE(NULLIF(od.UnitPrice, NULL) * 0.7, 0)) AS gross_margin
FROM "Order Details" od
JOIN orders o ON od.OrderID = o.OrderID
JOIN customers c ON o.CustomerID = c.CustomerID
WHERE strftime('%Y', o.OrderDate) = '1997'
GROUP BY c.CustomerID
ORDER BY gross_margin DESC
LIMIT 1;
        """
    ).with_inputs("question", "schema_context", "context"),

    # ==========================================
    # Example 7: Additional RAG — Product policy for perishable items
    # ==========================================
    dspy.Example(
        question="What is the return period for perishable products like Produce and Seafood?",
        schema_context={},
        context="Check the product_policy document for perishable items (Produce, Seafood, Dairy).",
        sql_query=""
    ).with_inputs("question", "schema_context", "context"),

    # ==========================================
    # Example 8: Hybrid — Category sales 1997
    # ==========================================
    dspy.Example(
        question="Which category generated the most sales in 1997?",
        schema_context={
            "orders": ["OrderID", "OrderDate"],
            "order_items": ["OrderID", "ProductID", "Quantity", "UnitPrice", "Discount"],
            "products": ["ProductID", "CategoryID"],
            "categories": ["CategoryID", "CategoryName"]
        },
        context="Sum revenue per category for the year 1997, considering discounts.",
        sql_query="""
SELECT c.CategoryName, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) AS Revenue
FROM "Order Details" od
JOIN orders o ON od.OrderID = o.OrderID
JOIN products p ON od.ProductID = p.ProductID
JOIN categories c ON p.CategoryID = c.CategoryID
WHERE strftime('%Y', o.OrderDate) = '1997'
GROUP BY c.CategoryName
ORDER BY Revenue DESC
LIMIT 1;
        """
    ).with_inputs("question", "schema_context", "context"),

    # ==========================================
    # Example 9: RAG — KPI definition for Average Order Value
    # ==========================================
    dspy.Example(
        question="How is Average Order Value (AOV) calculated?",
        schema_context={},
        context="Refer to KPI definitions document for the formula.",
        sql_query=""
    ).with_inputs("question", "schema_context", "context"),

    # ==========================================
    # Example 10: RAG — KPI definition for Gross Margin
    # ==========================================
    dspy.Example(
        question="How is Gross Margin calculated?",
        schema_context={},
        context="Refer to KPI definitions document for the gross margin formula.",
        sql_query=""
    ).with_inputs("question", "schema_context", "context"),
    
]
