# experiment_utils.py
"""
Utilities for tracking and comparing DSPy optimization experiments.
"""
import json
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

class ExperimentLogger:
    """
    Logs before/after metrics for DSPy optimization experiments.
    """
    def __init__(self, log_dir="experiments"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.current_experiment = None
    
    def start_experiment(self, name: str, module: str, optimizer: str):
        """Start tracking a new experiment."""
        self.current_experiment = {
            "name": name,
            "module": module,
            "optimizer": optimizer,
            "timestamp": datetime.now().isoformat(),
            "baseline": {},
            "optimized": {}
        }
        console.print(f"\n[bold yellow]🧪 Starting Experiment: {name}[/bold yellow]")
        console.print(f"[dim]Module: {module} | Optimizer: {optimizer}[/dim]\n")
    
    def log_baseline(self, metrics: dict):
        """Log baseline (zero-shot) metrics."""
        if not self.current_experiment:
            raise ValueError("No active experiment. Call start_experiment() first.")
        
        self.current_experiment["baseline"] = metrics
        
        console.print("[bold cyan]📊 Baseline (Zero-Shot) Results:[/bold cyan]")
        self._print_metrics(metrics)
    
    def log_optimized(self, metrics: dict):
        """Log optimized metrics."""
        if not self.current_experiment:
            raise ValueError("No active experiment. Call start_experiment() first.")
        
        self.current_experiment["optimized"] = metrics
        
        console.print("\n[bold green]📊 Optimized Results:[/bold green]")
        self._print_metrics(metrics)
    
    def _print_metrics(self, metrics: dict):
        """Pretty print metrics."""
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="cyan", width=20)
        table.add_column(style="white")
        
        for key, value in metrics.items():
            if isinstance(value, float):
                table.add_row(key, f"{value:.2f}")
            else:
                table.add_row(key, str(value))
        
        console.print(table)
    
    def compare_and_save(self):
        """Compare baseline vs optimized and save results."""
        if not self.current_experiment:
            raise ValueError("No active experiment.")
        
        baseline = self.current_experiment["baseline"]
        optimized = self.current_experiment["optimized"]
        
        # Calculate improvements
        comparison = {}
        for key in baseline.keys():
            if key in optimized and isinstance(baseline[key], (int, float)):
                base_val = baseline[key]
                opt_val = optimized[key]
                
                if base_val != 0:
                    improvement = ((opt_val - base_val) / base_val) * 100
                else:
                    improvement = 0.0
                
                comparison[key] = {
                    "baseline": base_val,
                    "optimized": opt_val,
                    "improvement_pct": improvement
                }
        
        self.current_experiment["comparison"] = comparison
        
        # Print comparison
        console.print("\n[bold magenta]📈 Improvement Analysis:[/bold magenta]")
        
        comp_table = Table(show_header=True, header_style="bold cyan")
        comp_table.add_column("Metric", style="cyan")
        comp_table.add_column("Baseline", justify="right")
        comp_table.add_column("Optimized", justify="right")
        comp_table.add_column("Change", justify="right")
        
        for key, vals in comparison.items():
            base = vals["baseline"]
            opt = vals["optimized"]
            imp = vals["improvement_pct"]
            
            # Format improvement with color
            if imp > 0:
                imp_str = f"[green]+{imp:.1f}%[/green]"
            elif imp < 0:
                imp_str = f"[red]{imp:.1f}%[/red]"
            else:
                imp_str = "[dim]0.0%[/dim]"
            
            comp_table.add_row(
                key,
                f"{base:.2f}" if isinstance(base, float) else str(base),
                f"{opt:.2f}" if isinstance(opt, float) else str(opt),
                imp_str
            )
        
        console.print(comp_table)
        
        # Save to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.log_dir / f"{self.current_experiment['name']}_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.current_experiment, f, indent=2)
        
        console.print(f"\n[green]✅ Experiment saved to: {filename}[/green]")
        
        return comparison
    
    def load_and_display(self, filename: str):
        """Load and display a saved experiment."""
        with open(filename, 'r') as f:
            exp = json.load(f)
        
        console.print(Panel.fit(
            f"[bold cyan]Experiment: {exp['name']}[/bold cyan]\n"
            f"[dim]Module: {exp['module']} | Optimizer: {exp['optimizer']}[/dim]\n"
            f"[dim]Date: {exp['timestamp']}[/dim]",
            border_style="cyan"
        ))
        
        if "comparison" in exp:
            comp_table = Table(show_header=True, header_style="bold cyan")
            comp_table.add_column("Metric", style="cyan")
            comp_table.add_column("Baseline", justify="right")
            comp_table.add_column("Optimized", justify="right")
            comp_table.add_column("Change", justify="right")
            
            for key, vals in exp["comparison"].items():
                base = vals["baseline"]
                opt = vals["optimized"]
                imp = vals["improvement_pct"]
                
                if imp > 0:
                    imp_str = f"[green]+{imp:.1f}%[/green]"
                elif imp < 0:
                    imp_str = f"[red]{imp:.1f}%[/red]"
                else:
                    imp_str = "[dim]0.0%[/dim]"
                
                comp_table.add_row(
                    key,
                    f"{base:.2f}" if isinstance(base, float) else str(base),
                    f"{opt:.2f}" if isinstance(opt, float) else str(opt),
                    imp_str
                )
            
            console.print("\n")
            console.print(comp_table)


def evaluate_sql_module(predictor, test_questions, db):
    """
    Evaluate SQL generation module on test questions.
    
    Returns:
        dict with metrics: success_rate, avg_result_count, valid_syntax_rate
    """
    total = len(test_questions)
    successful = 0
    valid_syntax = 0
    result_counts = []
    
    for item in test_questions:
        question = item['question']
        
        try:
            result = predictor(
                question=question,
                schema_context=db.get_schema(),
                context=""
            )
            
            if hasattr(result, 'sql_query') and result.sql_query:
                sql = result.sql_query.replace("```sql", "").replace("```", "").strip()
                valid_syntax += 1
                
                # Try execution
                exec_result = db.execute_query(sql)
                
                if not isinstance(exec_result, str) or not exec_result.startswith("SQL Error"):
                    successful += 1
                    if isinstance(exec_result, list):
                        result_counts.append(len(exec_result))
        except:
            pass
    
    return {
        "success_rate": (successful / total) * 100 if total > 0 else 0,
        "valid_syntax_rate": (valid_syntax / total) * 100 if total > 0 else 0,
        "avg_result_count": sum(result_counts) / len(result_counts) if result_counts else 0,
        "total_questions": total,
        "successful_executions": successful
    }