# debug_utils.py
import dspy
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.tree import Tree
from datetime import datetime
import json

console = Console()

class DebugTracker:
    """
    Enhanced tracker with human-readable logging for DSPy interactions.
    """
    def __init__(self):
        self.step_count = 0
        self.call_history = []
        
    def inspect_last_call(self, step_name: str, show_full: bool = False):
        """
        Pretty-print the last DSPy interaction with rich formatting.
        
        Args:
            step_name: Name of the current step
            show_full: If True, shows complete output; if False, truncates
        """
        try:
            history = dspy.settings.lm.history
            if not history:
                console.print(f"[yellow]⚠ No history available for {step_name}[/yellow]")
                return

            last_interaction = history[-1]
            self.step_count += 1
            
            # Store for summary
            self.call_history.append({
                "step": step_name,
                "timestamp": datetime.now().isoformat(),
                "interaction": last_interaction
            })
            
            # Create a panel for the step
            console.print(f"\n[bold magenta]{'='*60}[/bold magenta]")
            console.print(f"[bold cyan]🔍 Step {self.step_count}: {step_name}[/bold cyan]")
            console.print(f"[bold magenta]{'='*60}[/bold magenta]")
            
            # Extract prompt
            messages = last_interaction.get('messages', [])
            if messages:
                last_msg = messages[-1]
                prompt_content = last_msg.get('content', '')
                
                # Truncate if needed
                max_len = 500 if not show_full else 5000
                if len(prompt_content) > max_len:
                    display_prompt = prompt_content[:max_len] + "\n... [truncated]"
                else:
                    display_prompt = prompt_content
                
                console.print(Panel(
                    display_prompt,
                    title="[bold]📝 Prompt Sent to LM[/bold]",
                    border_style="blue",
                    expand=False
                ))
            
            # Extract response
            response = last_interaction.get('response', {})
            if isinstance(response, dict):
                choices = response.get('choices', [])
                if choices:
                    raw_output = choices[0].get('message', {}).get('content', '')
                else:
                    raw_output = str(response)
            else:
                raw_output = str(response)
            
            # Truncate response
            max_resp_len = 800 if not show_full else 8000
            if len(raw_output) > max_resp_len:
                display_response = raw_output[:max_resp_len] + "\n... [truncated]"
            else:
                display_response = raw_output
            
            console.print(Panel(
                Syntax(display_response, "text", theme="monokai", word_wrap=True),
                title="[bold]🤖 Model Response[/bold]",
                border_style="green",
                expand=False
            ))
            
            # Show token usage if available
            usage = response.get('usage') if isinstance(response, dict) else None
            if usage:
                usage_table = Table(show_header=False, box=None)
                usage_table.add_column(style="cyan")
                usage_table.add_column(style="white")
                
                usage_table.add_row("Prompt Tokens:", str(usage.get('prompt_tokens', 'N/A')))
                usage_table.add_row("Completion Tokens:", str(usage.get('completion_tokens', 'N/A')))
                usage_table.add_row("Total Tokens:", str(usage.get('total_tokens', 'N/A')))
                
                console.print(Panel(usage_table, title="📊 Token Usage", border_style="yellow"))
            
            console.print(f"[bold magenta]{'='*60}[/bold magenta]\n")
            
        except Exception as e:
            console.print(f"[bold red]❌ Debug print failed: {e}[/bold red]")
    
    def print_step_summary(self, step_name: str, data: dict):
        """
        Print a structured summary of a processing step.
        
        Args:
            step_name: Name of the step
            data: Dictionary with relevant data to display
        """
        tree = Tree(f"[bold blue]📍 {step_name}[/bold blue]")
        
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                tree.add(f"[cyan]{key}:[/cyan] {json.dumps(value, indent=2)[:200]}...")
            else:
                tree.add(f"[cyan]{key}:[/cyan] {value}")
        
        console.print(tree)
    
    def print_final_summary(self):
        """Print a summary of all steps taken."""
        if not self.call_history:
            return
        
        console.print("\n[bold magenta]{'='*60}[/bold magenta]")
        console.print("[bold yellow]📋 Execution Summary[/bold yellow]")
        console.print(f"[bold magenta]{'='*60}[/bold magenta]")
        
        summary_table = Table(show_header=True, header_style="bold cyan")
        summary_table.add_column("#", style="dim", width=4)
        summary_table.add_column("Step", style="cyan")
        summary_table.add_column("Timestamp", style="dim")
        
        for idx, entry in enumerate(self.call_history, 1):
            timestamp = entry['timestamp'].split('T')[1].split('.')[0]  # HH:MM:SS
            summary_table.add_row(str(idx), entry['step'], timestamp)
        
        console.print(summary_table)
        console.print(f"[bold green]✅ Total LM Calls: {len(self.call_history)}[/bold green]\n")
    
    def reset(self):
        """Reset tracking for new question."""
        self.step_count = 0
        self.call_history = []

# Global instance
tracker = DebugTracker()