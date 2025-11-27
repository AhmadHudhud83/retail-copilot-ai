# graph_hybrid.py
import dspy
from typing import  List, Dict, Any, TypedDict, Union
from langgraph.graph import StateGraph, END
from rich.console import Console

from agent.tools.sqlite_tool import NorthwindDB
from agent.rag.retrieval import LocalRetriever
from agent.dspy_signatures import (
    RouterSignature, 
    TextToSQL, 
    GenerateAnswer, 
)
# Import the enhanced debugger
from agent.rag.utils.debug_utils import tracker

console = Console()

# --- 1. Graph State ---
class AgentState(TypedDict):
    question: str
    format_hint: str
    
    # Analysis
    classification: str  # rag_only, sql_only, hybrid
    search_queries: List[str]
    
    # Data Context
    doc_chunks: List[Dict]  # From Retriever
    doc_context_str: str    # Stringified docs for DSPy
    extracted_constraints: str # From Planner (dates, formulas)
    
    # SQL
    schema_context: str
    sql_query: str
    sql_result: Union[List[Dict], str] # Result list or Error string
    
    # Output
    final_answer: Any
    citations: List[str]
    explanation: str
    
    # Repair Loop
    retry_count: int
    error: str


class SimpleSQLModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.generate = dspy.Predict(TextToSQL)
    
    def forward(self, question, schema_context, context):
        return self.generate(question=question, schema_context=schema_context, context=context)

# --- 2. Node Functions ---

def router_node(state: AgentState):
    console.print(f"\n[bold cyan]🔀 Router Node[/bold cyan]")
    console.print(f"[dim]Question: {state['question'][:80]}...[/dim]")
    
    # Use Predict instead of ChainOfThought for more stability on classification
    predictor = dspy.Predict(RouterSignature)
    result = predictor(question=state["question"])
    
    # Enhanced debug logging
    tracker.inspect_last_call("Router")
    
    # Robust extraction
    if hasattr(result, "classification"):
        cls = result.classification.lower()
    else:
        cls = "rag_only" # Default fallback
        
    final_cls = "rag_only"
    if "sql" in cls: final_cls = "sql_only"
    if "hybrid" in cls: final_cls = "hybrid"
    
    # Log summary
    tracker.print_step_summary("Router Decision", {
        "classification": final_cls,
        "raw_output": cls if hasattr(result, "classification") else "N/A"
    })
    
    console.print(f"[green]✓ Route selected: {final_cls}[/green]")
    return {"classification": final_cls}

def retrieval_node(state: AgentState):
    """Fetches documents."""
    console.print(f"\n[bold cyan]📚 Retrieval Node[/bold cyan]")
    
    retriever = LocalRetriever()
    chunks = retriever.search(state["question"], k=3)
    
    context_str = "\n\n".join([f"[{c['id']}] {c['text']}" for c in chunks])
    citations = [c['id'] for c in chunks]
    
    # Log what was retrieved
    tracker.print_step_summary("Documents Retrieved", {
        "num_chunks": len(chunks),
        "citations": citations,
        "top_score": f"{chunks[0]['score']:.3f}" if chunks else "N/A"
    })
    
    console.print(f"[green]✓ Retrieved {len(chunks)} document chunks[/green]")
    
    return {
        "doc_chunks": chunks, 
        "doc_context_str": context_str,
        "citations": citations
    }

def planner_node(state: AgentState):
    """
    (Hybrid Only) Look at retrieved docs and extract constraints.
    """
    console.print(f"\n[bold cyan]🗺️  Planner Node[/bold cyan]")
    console.print(f"[dim]Analyzing {len(state.get('doc_chunks', []))} documents...[/dim]")
    
    # Define a simple extractor
    class PlannerSig(dspy.Signature):
        """
        Read the docs and the question. Extract specific SQL constraints.
        Examples:
        - "Summer 1997" -> "OrderDate BETWEEN '1997-06-01' AND '1997-06-30'"
        - "Beverages" -> "CategoryName = 'Beverages'"
        """
        docs = dspy.InputField()
        question = dspy.InputField()
        constraints = dspy.OutputField(desc="SQL snippets (dates, IDs, formulas)")

    planner = dspy.Predict(PlannerSig)
    result = planner(docs=state["doc_context_str"], question=state["question"])
    
    # Log DSPy interaction
    tracker.inspect_last_call("Planner")
    
    # Log extracted constraints
    tracker.print_step_summary("Extracted Constraints", {
        "constraints": result.constraints
    })
    
    console.print(f"[green]✓ Constraints extracted[/green]")
    return {"extracted_constraints": result.constraints}

def sql_generation_node(state: AgentState):
    """Generates SQL using Schema + Optional Constraints."""
    console.print(f"\n[bold cyan]⚙️  SQL Generation Node[/bold cyan]")
    
    db = NorthwindDB()
    schema = db.get_schema()
    
    # LOAD THE OPTIMIZED MODULE
    optimizer_path = "agent/optimized_sql_module.json"
    try:
        generator = SimpleSQLModule()
        generator.load(optimizer_path)
        console.print("  [green]✓ Loaded optimized DSPy module[/green]")
    except Exception:
        console.print("  [yellow]⚠ Using default (non-optimized) module[/yellow]")
        generator = SimpleSQLModule() # Fallback
    
    # Logic: Handle Repair Count
    current_retries = state.get("retry_count", 0)
    context = state.get("extracted_constraints", "")
    
    if state.get("error"):
        current_retries += 1
        console.print(f"  [yellow]🔧 Repair attempt {current_retries}/2[/yellow]")
        console.print(f"  [dim]Previous error: {state['error'][:100]}...[/dim]")
        context += f"\n\nPREVIOUS ERROR: {state['error']}. Fix the SQL."

    # Use a context manager to temporarily boost tokens for this complex step
    with dspy.settings.context(lm=dspy.settings.lm.copy(max_tokens=1024)):
        result = generator(
            question=state["question"],
            schema_context=schema,
            context=context
        )
    
    # Enhanced debug logging
    tracker.inspect_last_call("SQL Generation")
    
    # Robustness check: did the model fail to output the field?
    if not hasattr(result, 'sql_query'):
        console.print("  [bold red]✗ Model failed to generate 'sql_query' field[/bold red]")
        return {
            "error": "Model failed to generate SQL format", 
            "retry_count": current_retries + 1
        }

    clean_sql = result.sql_query.replace("```sql", "").replace("```", "").strip()
    
    # Log generated SQL
    tracker.print_step_summary("SQL Generated", {
        "sql_query": clean_sql,
        "retry_count": current_retries,
        "has_constraints": bool(state.get("extracted_constraints"))
    })
    
    console.print(f"[green]✓ SQL generated[/green]")
    console.print(f"[dim]{clean_sql[:100]}{'...' if len(clean_sql) > 100 else ''}[/dim]")
    
    return {
        "schema_context": schema,
        "sql_query": clean_sql,
        "retry_count": current_retries
    }

def sql_execution_node(state: AgentState):
    """Runs the SQL."""
    console.print(f"\n[bold cyan]▶️  SQL Execution Node[/bold cyan]")
    
    db = NorthwindDB()
    
    # Check if we have a query to run
    if not state.get("sql_query"):
        console.print("  [red]✗ No SQL query to execute[/red]")
        return {"sql_result": "No SQL generated", "error": "No SQL generated"}
    
    console.print(f"[dim]Executing: {state['sql_query'][:80]}...[/dim]")
    result = db.execute_query(state["sql_query"])
    
    # Check for errors
    if isinstance(result, str) and result.startswith("SQL Error"):
        console.print(f"  [red]✗ SQL Error: {result[:100]}...[/red]")
        tracker.print_step_summary("SQL Execution Failed", {
            "error": result[:200]
        })
        return {"sql_result": result, "error": result}
    
    # Success
    result_count = len(result) if isinstance(result, list) else 0
    console.print(f"[green]✓ SQL executed successfully ({result_count} rows returned)[/green]")
    
    tracker.print_step_summary("SQL Execution Success", {
        "rows_returned": result_count,
        "first_row": result[0] if result and isinstance(result, list) else "N/A"
    })
    
    return {"sql_result": result, "error": None}

def synthesis_node(state: AgentState):
    """Final Answer Generation."""
    console.print(f"\n[bold cyan]🎯 Synthesis Node[/bold cyan]")
    console.print("[dim]Generating final answer...[/dim]")
    
    synthesizer = dspy.Predict(GenerateAnswer)
    
    sql_res = str(state.get("sql_result", "No SQL run"))
    if len(sql_res) > 2000: sql_res = sql_res[:2000] + "...(truncated)"
    
    try:
        result = synthesizer(
            question=state["question"],
            sql_query=state.get("sql_query", ""),
            sql_result=sql_res,
            doc_context=state.get("doc_context_str", ""),
            format_hint=state["format_hint"]
        )
        
        # Enhanced debug logging
        tracker.inspect_last_call("Synthesis")
        
        current_cites = state.get("citations", [])
        new_cites = result.citations
        
        # Handle case where model returns string instead of list
        if isinstance(new_cites, str):
            new_cites = [c.strip() for c in new_cites.split(",")]
            
        final_cites = list(set(current_cites + (new_cites if isinstance(new_cites, list) else [])))
        
        # Log synthesis results
        tracker.print_step_summary("Answer Synthesized", {
            "final_answer": str(result.final_answer)[:100],
            "format_hint": state["format_hint"],
            "num_citations": len(final_cites),
            "explanation_length": len(result.explanation)
        })
        
        console.print(f"[green]✓ Answer synthesized with {len(final_cites)} citations[/green]")
        
        return {
            "final_answer": result.final_answer,
            "explanation": result.explanation,
            "citations": final_cites
        }
    except Exception as e:
        console.print(f"[bold red]✗ Synthesis failed: {e}[/bold red]")
        return {
            "final_answer": None, 
            "explanation": f"Synthesis Error: {e}", 
            "citations": state.get("citations", [])
        }

# --- 3. Edge Logic ---

def decide_route(state: AgentState):
    return state["classification"]

def check_sql_health(state: AgentState):
    error = state.get("error")
    retries = state.get("retry_count", 0)
    
    if error and retries < 2:
        console.print(f"[yellow]🔄 Routing to repair (attempt {retries + 1}/2)[/yellow]")
        return "repair"
    
    if error and retries >= 2:
        console.print(f"[red]⚠ Max retries reached, proceeding with error[/red]")
    
    return "synthesize"

# --- 4. Build Graph ---

def build_graph():
    """Build and compile the LangGraph workflow."""
    console.print("[dim]Building graph...[/dim]")
    
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("router", router_node)
    workflow.add_node("retriever", retrieval_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("sql_gen", sql_generation_node)
    workflow.add_node("executor", sql_execution_node)
    workflow.add_node("synthesizer", synthesis_node)
    
    # Set Entry
    workflow.set_entry_point("router")
    
    # Edges
    workflow.add_conditional_edges(
        "router",
        decide_route,
        {
            "rag_only": "retriever",
            "sql_only": "sql_gen",
            "hybrid": "retriever"
        }
    )
    
    def post_retrieval_route(state: AgentState):
        if state["classification"] == "hybrid":
            return "planner"
        return "synthesizer"

    workflow.add_conditional_edges(
        "retriever",
        post_retrieval_route,
        {"planner": "planner", "synthesizer": "synthesizer"}
    )
    
    workflow.add_edge("planner", "sql_gen")
    workflow.add_edge("sql_gen", "executor")
    
    workflow.add_conditional_edges(
        "executor",
        check_sql_health,
        {
            "repair": "sql_gen",
            "synthesize": "synthesizer"
        }
    )
    
    workflow.add_edge("synthesizer", END)
    
    console.print("[green]✓ Graph compiled[/green]")
    return workflow.compile()