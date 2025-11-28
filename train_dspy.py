# train_dspy.py
import dspy
from dspy.teleprompt import BootstrapFewShot
from agent.dspy_signatures import TextToSQL
from agent.tools.sqlite_tool import NorthwindDB
from data.trainset import trainset
import argparse

# -----------------------------
# 1. Parse CLI Arguments
# -----------------------------
parser = argparse.ArgumentParser(description="Optimize SQL DSPy module with configurable parameters")
parser.add_argument("--max_bootstrapped_demos", type=int, default=10, help="Max bootstrapped demos")
parser.add_argument("--max_labeled_demos", type=int, default=10, help="Max labeled demos")
args = parser.parse_args()

# -----------------------------
# 2. Setup LM
# -----------------------------
lm = dspy.LM(
    "ollama_chat/phi3.5:3.8b-mini-instruct-q3_K_M",
    api_base="http://localhost:11434",
    max_tokens=1024,
    temperature=0.0
)
dspy.configure(lm=lm)

# -----------------------------
# 3. Metric: EXECUTION + CONTENT CHECK
# -----------------------------
def validate_sql_execution(example, pred, trace=None):
    sql = pred.sql_query
    if "```" in sql: sql = sql.replace("```sql", "").replace("```", "")

    # Syntax bans
    for banned in ["WITH", "YEAR(", "strftime('%b'"]:
        if banned in sql:
            return False

    # Execute query
    db = NorthwindDB()
    result = db.execute_query(sql)

    return isinstance(result, list) and len(result) > 0

# -----------------------------
# 4. Compile Module
# -----------------------------
print("🚀 Starting Streamlined DSPy Optimization...")

teleprompter = BootstrapFewShot(
    metric=validate_sql_execution,
    max_bootstrapped_demos=args.max_bootstrapped_demos,
    max_labeled_demos=args.max_labeled_demos
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
