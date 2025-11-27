# run_agent_hybrid.py
import json
import click
import dspy
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from agent.graph_hybrid import build_graph
from agent.rag.utils.debug_utils import tracker

console = Console()

def run_zero_shot_experiment(questions, module_name="sql_gen"):
    """
    Run a zero-shot experiment on a DSPy module.
    
    Args:
        questions: List of question dicts
        module_name: Which module to test ("sql_gen", "router", "synthesizer")
    
    Returns:
        dict with metrics
    """
    console.print(f"\n[bold yellow]🧪 Running Zero-Shot Experiment: {module_name}[/bold yellow]\n")
    
    from agent.dspy_signatures import TextToSQL, RouterSignature, GenerateAnswer
    from agent.tools.sqlite_tool import NorthwindDB
    
    results = {
        "total": len(questions),
        "success": 0,
        "failures": [],
        "avg_confidence": 0.0
    }
    
    if module_name == "sql_gen":
        predictor = dspy.Predict(TextToSQL)
        db = NorthwindDB()
        schema = db.get_schema()
        
        console.print("[cyan]Testing SQL Generation (zero-shot)...[/cyan]")
        
        for item in questions:
            question = item['question']
            console.print(f"\n[dim]Q: {question[:80]}...[/dim]")
            
            try:
                result = predictor(
                    question=question,
                    schema_context=schema,
                    context=""
                )
                
                if hasattr(result, 'sql_query') and result.sql_query:
                    sql = result.sql_query.replace("```sql", "").replace("```", "").strip()
                    
                    # Test execution
                    exec_result = db.execute_query(sql)
                    
                    if not isinstance(exec_result, str) or not exec_result.startswith("SQL Error"):
                        results["success"] += 1
                        console.print(f"[green]✓ Valid SQL generated[/green]")
                    else:
                        results["failures"].append({
                            "question": question,
                            "error": exec_result
                        })
                        console.print(f"[red]✗ SQL Error: {exec_result[:100]}[/red]")
                else:
                    results["failures"].append({
                        "question": question,
                        "error": "No SQL generated"
                    })
                    console.print("[red]✗ No SQL output[/red]")
                    
            except Exception as e:
                results["failures"].append({
                    "question": question,
                    "error": str(e)
                })
                console.print(f"[red]✗ Exception: {e}[/red]")
    
    elif module_name == "router":
        predictor = dspy.Predict(RouterSignature)
        
        console.print("[cyan]Testing Router Classification (zero-shot)...[/cyan]")
        
        for item in questions:
            question = item['question']
            console.print(f"\n[dim]Q: {question[:80]}...[/dim]")
            
            try:
                result = predictor(question=question)
                
                if hasattr(result, 'classification'):
                    cls = result.classification.lower()
                    results["success"] += 1
                    console.print(f"[green]✓ Classified as: {cls}[/green]")
                else:
                    results["failures"].append({
                        "question": question,
                        "error": "No classification"
                    })
                    console.print("[red]✗ No classification output[/red]")
                    
            except Exception as e:
                results["failures"].append({
                    "question": question,
                    "error": str(e)
                })
                console.print(f"[red]✗ Exception: {e}[/red]")
    
    # Print summary
    success_rate = (results["success"] / results["total"]) * 100
    
    summary_table = Table(title="Zero-Shot Results", show_header=True)
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="white")
    
    summary_table.add_row("Total Questions", str(results["total"]))
    summary_table.add_row("Successful", str(results["success"]))
    summary_table.add_row("Failed", str(len(results["failures"])))
    summary_table.add_row("Success Rate", f"{success_rate:.1f}%")
    
    console.print("\n")
    console.print(summary_table)
    
    return results

@click.command()
@click.option('--batch', required=True, help='Input JSONL file')
@click.option('--out', required=True, help='Output JSONL file')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed DSPy interactions')
@click.option('--experiment', type=click.Choice(['sql_gen', 'router', 'none']), 
              default='none', help='Run zero-shot experiment before main run')
def main(batch, out, verbose, experiment):
    """
    Retail Analytics Copilot - Main Entry Point
    
    Run with:
        python run_agent_hybrid.py --batch sample_questions_hybrid_eval.jsonl --out outputs_hybrid.jsonl
        
    Optional flags:
        --verbose / -v : Show detailed DSPy prompts and responses
        --experiment sql_gen : Run zero-shot SQL generation experiment first
        --experiment router : Run zero-shot router experiment first
    """
    
    # Print banner
    console.print(Panel.fit(
        "[bold cyan]🛍️  Northwind Retail Analytics Copilot[/bold cyan]\n"
        "[dim]Powered by DSPy + LangGraph + Local LLMs[/dim]",
        border_style="cyan"
    ))
    
    # 1. Setup DSPy (Ollama)
    console.print("\n[yellow]⚙️  Configuring DSPy with Ollama...[/yellow]")
    lm = dspy.LM(
        model="ollama_chat/phi3.5:3.8b-mini-instruct-q3_K_M",
        api_base="http://localhost:11434",
        num_ctx=8192,      
        max_tokens=4096,     
        temperature=0.0     
    )
    dspy.configure(lm=lm)
    console.print("[green]✓ DSPy configured[/green]")
    
    # 2. Load questions
    console.print(f"\n[yellow]📂 Loading questions from {batch}...[/yellow]")
    with open(batch, 'r') as f:
        questions = [json.loads(line) for line in f]
    console.print(f"[green]✓ Loaded {len(questions)} questions[/green]")
    
    # 3. Optional: Run experiment
    if experiment != 'none':
        run_zero_shot_experiment(questions, module_name=experiment)
        console.print("\n[bold yellow]Press Enter to continue with main processing...[/bold yellow]")
        input()
    
    # 4. Build Graph
    console.print("\n[yellow]🔧 Building LangGraph workflow...[/yellow]")
    app = build_graph()
    console.print("[green]✓ Graph compiled[/green]")
    
    results = []
    
    # 5. Process Batch with Progress Bar
    console.print(f"\n[bold green]🚀 Starting batch processing...[/bold green]\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("[cyan]Processing questions...", total=len(questions))
        
        for i, item in enumerate(questions):
            q_id = item['id']
            question = item['question']
            fmt = item['format_hint']
            
            # Reset tracker for each question
            tracker.reset()
            
            console.print(f"\n[bold blue]{'='*70}[/bold blue]")
            console.print(f"[bold white]Question {i+1}/{len(questions)}[/bold white]")
            console.print(f"[bold blue]{'='*70}[/bold blue]")
            console.print(f"[cyan]ID:[/cyan] {q_id}")
            console.print(f"[cyan]Q:[/cyan] {question}")
            console.print(f"[dim]Expected format: {fmt}[/dim]\n")
            
            # Initial State
            initial_state = {
                "question": question,
                "format_hint": fmt,
                "retry_count": 0,
                "citations": []
            }
            
            # Run Graph
            try:
                final_state = app.invoke(initial_state)
                
                output = {
                    "id": q_id,
                    "final_answer": final_state.get("final_answer"),
                    "sql": final_state.get("sql_query", ""),
                    "confidence": 1.0 if not final_state.get("error") else 0.5,
                    "explanation": final_state.get("explanation", ""),
                    "citations": final_state.get("citations", [])
                }
                
                # Display results
                result_table = Table(show_header=False, box=None, padding=(0, 2))
                result_table.add_column(style="bold cyan", width=15)
                result_table.add_column(style="white")
                
                if final_state.get("classification"):
                    result_table.add_row("Route:", final_state["classification"])
                
                if final_state.get("sql_query"):
                    sql_preview = final_state['sql_query'][:100] + "..." if len(final_state['sql_query']) > 100 else final_state['sql_query']
                    result_table.add_row("SQL:", sql_preview)
                
                result_table.add_row("Answer:", str(output['final_answer']))
                result_table.add_row("Citations:", ", ".join(output['citations'][:5]))
                result_table.add_row("Confidence:", f"{output['confidence']:.2f}")
                
                console.print(Panel(result_table, title="[bold green]✅ Result[/bold green]", border_style="green"))
                
                # Show full summary if verbose
                if verbose:
                    tracker.print_final_summary()
                
                results.append(output)
                
            except Exception as e:
                console.print(Panel(
                    f"[bold red]Error: {str(e)}[/bold red]",
                    title="❌ Processing Failed",
                    border_style="red"
                ))
                results.append({
                    "id": q_id,
                    "final_answer": None,
                    "sql": "",
                    "confidence": 0.0,
                    "explanation": f"System Error: {str(e)}",
                    "citations": []
                })
            
            progress.update(task, advance=1)

    # 6. Save Outputs
    console.print(f"\n[yellow]💾 Saving results to {out}...[/yellow]")
    with open(out, 'w') as f:
        for res in results:
            f.write(json.dumps(res) + "\n")
    
    # 7. Final Summary
    console.print(Panel.fit(
        f"[bold green]✅ Processing Complete![/bold green]\n\n"
        f"Questions Processed: {len(results)}\n"
        f"Output File: {out}\n",
        border_style="green"
    ))

if __name__ == "__main__":
    main()