import sys
from rich.console import Console
from rich.panel import Panel
from app.config.config import settings
from app.core.logging_setup import setup_logging
from app.core.brain import Brain

# Initialize logger
setup_logging()

import uuid

console = Console()
brain = Brain()
session_id = str(uuid.uuid4())

def main():
    console.print(Panel.fit(
        f"[bold green]KLAUSE {settings.klause.version}[/bold green] — Personal AI Engineering Assistant\n"
        f"Session ID: [bold yellow]{session_id}[/bold yellow]\n"
        "Type [bold red]exit[/bold red] or [bold red]quit[/bold red] to end the session.",
        title="[bold cyan]System Booted[/bold cyan]",
        border_style="cyan"
    ))
    
    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit"):
                console.print("[bold yellow]Shutting down KLAUSE. Goodbye![/bold yellow]")
                break
                
            response = brain.think(user_input, session_id=session_id)
            console.print(f"[bold cyan]KLAUSE:[/bold cyan] {response}\n")
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Session interrupted. Goodbye![/bold yellow]")
            sys.exit(0)
        except Exception as e:
            console.print(f"[bold red]System Error:[/bold red] {e}")

if __name__ == "__main__":
    main()
