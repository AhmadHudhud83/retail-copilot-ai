import dspy
from agent.dspy_signatures import RouterSignature

# Connect to Ollama (Phi-3.5)

lm = dspy.LM("ollama_chat/phi3.5:3.8b-mini-instruct-q3_K_M", api_base="http://localhost:11434", api_key="")

dspy.configure(lm=lm)

# Test the Router
router = dspy.ChainOfThought(RouterSignature)
q = "Calculate the total revenue for beverages in 1997."
pred = router(question=q)

print(f"Question: {q}")
print(f"Classification: {pred.classification}")
print(f"Reasoning: {pred.reasoning}")