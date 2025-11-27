import dspy
from dspy.teleprompt import BootstrapFewShot
from agent.dspy_signatures import TextToSQL
from agent.tools.sqlite_tool import NorthwindDB
from agent.trainset import trainset   

# 1. Setup Model
lm = dspy.LM("ollama_chat/phi3.5:3.8b-mini-instruct-q3_K_M", api_base="http://localhost:11434", max_tokens=1024, temperature=0.0)
dspy.configure(lm=lm)

# 2. Metric: EXECUTION + CONTENT CHECK
def validate_sql_execution(example, pred, trace=None):
    sql = pred.sql_query
    
    # Clean up
    if "```" in sql: sql = sql.replace("```sql", "").replace("```", "")
    
    # Syntax Bans
    if "WITH" in sql: return False
    if "YEAR(" in sql: return False
    if "strftime('%b'" in sql: return False
    
    # Execution
    db = NorthwindDB()
    result = db.execute_query(sql)
    
    # Logic: Must return data
    if isinstance(result, list) and len(result) > 0:
        return True
    return False

# 3. Compile
print("🚀 Starting Streamlined DSPy Optimization...")

teleprompter = BootstrapFewShot(
    metric=validate_sql_execution, 
    max_bootstrapped_demos=10, 
    max_labeled_demos=10
)

class SimpleSQLModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.generate = dspy.Predict(TextToSQL)
    
    def forward(self, question, schema_context, context):
        return self.generate(question=question, schema_context=schema_context, context=context)

compiled_sql_gen = teleprompter.compile(SimpleSQLModule(), trainset=trainset)

print("✅ Optimization Complete. Saving to 'agent/optimized_sql_module.json'...")
compiled_sql_gen.save("agent/optimized_sql_module.json")
