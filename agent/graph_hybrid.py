import dspy
from typing import List, Dict, Any, TypedDict, Union
from langgraph.graph import StateGraph, END
from rich.console import Console

from agent.tools.sqlite_tool import NorthwindDB
from agent.rag.retrieval import LocalRetriever
from agent.dspy_signatures import (
    RouterSignature, 
    TextToSQL, 
    GenerateAnswer, 
)
from agent.rag.utils.debug_utils import tracker

console = Console()

# --- 0. Planner Signature (Local) ---
class PlannerSignature(dspy.Signature):
    """
    Analyze the docs and question to produce SQL constraints.
    
    CRITICAL DATE RULES:
    - If the docs mention a specific date range (e.g. "Summer 1997: 1997-06-01 to 1997-06-30"), 
      YOU MUST output standard SQL: "OrderDate BETWEEN '1997-06-01' AND '1997-06-30'".
    - Do NOT use the current year. Use ONLY the years found in the docs (usually 1996-1998).
    
    KPI RULES:
    - If 'Gross Margin' is mentioned, output: "Margin = (UnitPrice - UnitPrice*0.7) * Quantity".
    """
    context_docs = dspy.InputField(desc="Retrieved documentation content")
    question = dspy.InputField()
    
    constraints = dspy.OutputField(desc="SQL snippets (e.g. 'OrderDate BETWEEN...')")
    reasoning = dspy.OutputField(desc="Why these constraints were chosen")

# --- 1. Graph State ---
class AgentState(TypedDict):
    question: str
    format_hint: str
    
    # Analysis
    classification: str
    
    # Data Context
    doc_chunks: List[Dict]
    doc_context_str: str
    extracted_constraints: str 
    
    # SQL
    schema_context: str
    sql_query: str
    sql_result: Union[List[Dict], str]
    
    # Output
    final_answer: Any
    citations: List[str] # Final definitive list
    explanation: str
    
    # Repair Loop
    retry_count: int
    error: str

# --- 2. Module Wrapper ---
class SimpleSQLModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.generate = dspy.Predict(TextToSQL)
    
    def forward(self, question, schema_context, context):
        return self.generate(question=question, schema_context=schema_context, context=context)

# --- 3. Node Functions ---

def router_node(state: AgentState):
    console.print(f"\n[bold cyan]🔀 Router[/bold cyan]")
    predictor = dspy.Predict(RouterSignature)
    result = predictor(question=state["question"])
    
    raw_cls = getattr(result, "classification", "rag_only").lower()
    final_cls = "rag_only"
    if "sql" in raw_cls: final_cls = "sql_only"
    if "hybrid" in raw_cls: final_cls = "hybrid"
    
    console.print(f"  [dim]Classified as: {final_cls}[/dim]")
    return {"classification": final_cls}

def retrieval_node(state: AgentState):
    console.print(f"\n[bold cyan]📚 Retriever[/bold cyan]")
    retriever = LocalRetriever()
    # Increased k to 4 to ensure calendar + policies both fit
    chunks = retriever.search(state["question"], k=4)
    
    context_str = "\n\n".join([f"Source: {c['id']}\nContent: {c['text']}" for c in chunks])
    citations = [c['id'] for c in chunks]
    
    console.print(f"  [green]Found {len(chunks)} chunks[/green]")
    return {
        "doc_chunks": chunks, 
        "doc_context_str": context_str,
        "citations": citations # partial citations
    }

def planner_node(state: AgentState):
    """
    CRITICAL STEP: Translates "Summer 1997" -> "1997-06-01..."
    """
    console.print(f"\n[bold cyan]🗺️  Planner[/bold cyan]")
    
    planner = dspy.Predict(PlannerSignature)
    result = planner(
        context_docs=state["doc_context_str"], 
        question=state["question"]
    )
    
    constraints = getattr(result, "constraints", "No specific constraints.")
    reasoning = getattr(result, "reasoning", "")
    
    console.print(f"  [dim]Reasoning: {reasoning[:100]}...[/dim]")
    console.print(f"  [bold yellow]Constraints: {constraints}[/bold yellow]")
    
    return {"extracted_constraints": constraints}

def sql_generation_node(state: AgentState):
    console.print(f"\n[bold cyan]⚙️  SQL Generator[/bold cyan]")
    
    db = NorthwindDB()
    schema = db.get_schema()
    
    # Try loading optimized module
    generator = SimpleSQLModule()
    try:
        generator.load("agent/optimized_sql_module.json")
    except:
        pass

    # Logic: Combine Planner Constraints into the prompt
    planner_context = state.get("extracted_constraints", "")
    
    # Handle Retries
    retries = state.get("retry_count", 0)
    if state.get("error"):
        retries += 1
        planner_context += f"\n\nIMPORTANT: Previous query failed with error: {state['error']}. Fix the syntax."
        console.print(f"  [red]Repairing SQL (Attempt {retries}/2)[/red]")

    pred = generator(
        question=state["question"],
        schema_context=schema,
        context=planner_context
    )
    
    sql = getattr(pred, "sql_query", "")
    # Clean markdown
    sql = sql.replace("```sql", "").replace("```", "").strip()
    
    console.print(f"  [dim]{sql[:80]}...[/dim]")
    return {
        "schema_context": schema,
        "sql_query": sql,
        "retry_count": retries
    }

def sql_execution_node(state: AgentState):
    console.print(f"\n[bold cyan]▶️  Executor[/bold cyan]")
    db = NorthwindDB()
    
    if not state.get("sql_query"):
        return {"sql_result": "No SQL generated", "error": "No SQL"}
        
    result = db.execute_query(state["sql_query"])
    
    if isinstance(result, str) and result.startswith("SQL Error"):
        console.print(f"  [bold red]{result}[/bold red]")
        return {"sql_result": result, "error": result}
        
    console.print(f"  [green]Success: {len(result)} rows[/green]")
    
    # Add Tables to citations if successful
    new_citations = state.get("citations", [])
    lower_sql = state["sql_query"].lower()
    if "orders" in lower_sql: new_citations.append("Orders")
    if "order_items" in lower_sql: new_citations.append("Order Details")
    if "products" in lower_sql: new_citations.append("Products")
    if "customers" in lower_sql: new_citations.append("Customers")
    
    return {"sql_result": result, "error": None, "citations": list(set(new_citations))}

def synthesis_node(state: AgentState):
    console.print(f"\n[bold cyan]🎯 Synthesizer[/bold cyan]")
    
    # We use the Base Signature but IGNORE the model's citation output
    synthesizer = dspy.Predict(GenerateAnswer)
    
    sql_res = str(state.get("sql_result", ""))[:2000] # Truncate large results
    
    pred = synthesizer(
        question=state["question"],
        sql_query=state.get("sql_query", ""),
        sql_result=sql_res,
        doc_context=state.get("doc_context_str", ""),
        format_hint=state["format_hint"]
    )
    
    # 1. Answer & Explanation
    final_ans = getattr(pred, "final_answer", None)
    explanation = getattr(pred, "explanation", "No explanation.")
    
    # 2. Strict Type Casting (The "Audit" step)
    fmt = state["format_hint"]
    try:
        if fmt == "int":
            # Extract first number found
            import re
            nums = re.findall(r"[-+]?\d+", str(final_ans))
            final_ans = int(nums[0]) if nums else 0
        elif fmt == "float":
            import re
            # Find float pattern
            nums = re.findall(r"[-+]?\d*\.\d+|\d+", str(final_ans))
            final_ans = float(nums[0]) if nums else 0.0
    except:
        console.print(f"  [yellow]⚠ Type cast failed for {fmt}, keeping raw string[/yellow]")

    # 3. Programmatic Citations (Reliable)
    # We take the accumulated citations from Retriever + Executor
    final_citations = state.get("citations", [])
    
    return {
        "final_answer": final_ans,
        "explanation": explanation,
        "citations": final_citations, # Overwrite whatever the model might have thought
        "confidence": 1.0 if not state.get("error") else 0.0
    }

# --- 4. Edges ---

def decide_route(state: AgentState):
    return state["classification"]

def check_sql_health(state: AgentState):
    if state.get("error") and state.get("retry_count", 0) < 2:
        return "repair"
    return "synthesize"

# --- 5. Build ---

def build_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("router", router_node)
    workflow.add_node("retriever", retrieval_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("sql_gen", sql_generation_node)
    workflow.add_node("executor", sql_execution_node)
    workflow.add_node("synthesizer", synthesis_node)
    
    workflow.set_entry_point("router")
    
    workflow.add_conditional_edges(
        "router",
        decide_route,
        {"rag_only": "retriever", "sql_only": "sql_gen", "hybrid": "retriever"}
    )
    
    workflow.add_conditional_edges(
        "retriever",
        lambda x: "planner" if x["classification"] == "hybrid" else "synthesizer",
        {"planner": "planner", "synthesizer": "synthesizer"}
    )
    
    workflow.add_edge("planner", "sql_gen")
    workflow.add_edge("sql_gen", "executor")
    
    workflow.add_conditional_edges(
        "executor",
        check_sql_health,
        {"repair": "sql_gen", "synthesize": "synthesizer"}
    )
    
    workflow.add_edge("synthesizer", END)
    
    return workflow.compile()