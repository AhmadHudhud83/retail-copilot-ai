import os
import time
import requests
import sqlite3
import dspy
from rich.console import Console
from rich.panel import Panel

console = Console()

def check_db():
    db_path = "data/northwind.sqlite"
    console.print(f"[bold]1. Checking Database ({db_path})...[/bold]")
    
    if not os.path.exists(db_path):
        console.print("[red]❌ Database file missing![/red]")
        return False
    
    try:
        # Check if we can read and if Views exist
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='view'")
        views = [r[0] for r in cursor.fetchall()]
        conn.close()
        
        required = {'orders', 'order_items', 'products'}
        if required.issubset(set(views)):
            console.print(f"[green]✅ DB Connection OK. Views found: {len(views)}[/green]")
            return True
        else:
            console.print(f"[red]❌ DB Connection OK, but missing views. Found: {views}[/red]")
            return False
    except Exception as e:
        console.print(f"[red]❌ DB Error: {e}[/red]")
        return False

def check_ollama():
    url = "http://localhost:11434/api/tags"
    console.print(f"\n[bold]2. Checking Ollama ({url})...[/bold]")
    
    try:
        r = requests.get(url, timeout=2)
        if r.status_code == 200:
            models = [m['name'] for m in r.json()['models']]
            console.print(f"[green]✅ Ollama is up. Models: {models}[/green]")
            
            # Check for Phi-3.5 specific tag
            phi_models = [m for m in models if 'phi3.5' in m]
            if phi_models:
                console.print(f"[green]✅ Found Phi-3.5 variant: {phi_models[0]}[/green]")
                return phi_models[0]
            else:
                console.print("[yellow]⚠️ Phi-3.5 not found. You might need to pull it.[/yellow]")
                return None
        else:
            console.print("[red]❌ Ollama returned non-200 status.[/red]")
            return None
    except Exception as e:
        console.print(f"[red]❌ Ollama connection failed: {e}[/red]")
        return None

def test_inference(model_name):
    console.print(f"\n[bold]3. Testing Inference Speed & Format...[/bold]")
    
    lm = dspy.LM(f"ollama_chat/{model_name}", api_base="http://localhost:11434", max_tokens=200)
    dspy.configure(lm=lm)
    
    t0 = time.time()
    try:
        # Simple generation
        pred = dspy.Predict("question -> answer")(question="What is 2+2? Reply with just the number.")
        t1 = time.time()
        console.print(f"[green]✅ Inference success ({t1-t0:.2f}s). Answer: {pred.answer}[/green]")
    except Exception as e:
        console.print(f"[red]❌ Inference failed: {e}[/red]")

if __name__ == "__main__":
    console.print(Panel("[bold white]Retail Copilot Diagnostics[/bold white]", style="blue"))
    if check_db():
        model = check_ollama()
        if model:
            test_inference(model)