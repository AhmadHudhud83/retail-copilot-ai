import dspy
from agent.dspy_signatures import TextToSQL
from agent.tools.sqlite_tool import NorthwindDB
from agent.graph_hybrid import SimpleSQLModule

# 1. Setup Model
lm = dspy.LM("ollama_chat/phi3.5:3.8b-mini-instruct-q3_K_M", api_base="http://localhost:11434", max_tokens=600, temperature=0.0)
dspy.configure(lm=lm)

# 2. Validation Dataset (Questions NOT in your training set)
val_questions = [
    "How many products are in the Beverages category?",
    "What is the total revenue for 1997?", 
    "List the top 5 customers by order count.",
    "What is the average unit price of products?",
    "How many orders did we have in May 1997?",
    "Total quantity of Tofu sold all time.",
    "Who is the employee with the most orders?",
    "Revenue for the product 'Chai' in 1997"
]

def check_sql_validity(sql):
    if "YEAR(" in sql or "WITH" in sql: return False
    db = NorthwindDB()
    res = db.execute_query(sql)
    # Valid if it returns a list (even empty list), invalid if returns Error String
    if isinstance(res, str) and res.startswith("SQL Error"):
        return False
    return True

def evaluate_module(module, name):
    print(f"\n--- Testing {name} ---")
    correct = 0
    for q in val_questions:
        print(f"Q: {q}")
        try:
            # We create a dummy schema context for the test
            db = NorthwindDB()
            pred = module(question=q, schema_context=db.get_schema(), context="")
            sql = pred.sql_query
            
            is_valid = check_sql_validity(sql)
            status = "✅" if is_valid else "❌"
            if is_valid: correct += 1
            print(f"  {status} SQL: {sql[:80]}...")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            
    score = (correct / len(val_questions)) * 100
    print(f"👉 {name} Accuracy: {score:.1f}%")
    return score

if __name__ == "__main__":
    # 1. Test Baseline (Zero-Shot)
    base_module = SimpleSQLModule()
    score_before = evaluate_module(base_module, "Baseline (Zero-Shot)")
    
    # 2. Test Optimized (Few-Shot)
    opt_module = SimpleSQLModule()
    try:
        opt_module.load("agent/optimized_sql_module.json")
        score_after = evaluate_module(opt_module, "Optimized (Few-Shot)")
        
        print("\n=================================")
        print(f"📉 Before: {score_before:.1f}%")
        print(f"📈 After:  {score_after:.1f}%")
        print(f"🚀 Delta:  +{score_after - score_before:.1f}%")
        print("=================================")
    except Exception as e:
        print(f"\nCould not load optimized module: {e}")
        print("Did you run 'python train_dspy.py'?")