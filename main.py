import sys
import time
import queue
import threading
import uuid
from rich.console import Console
from rich.panel import Panel
from app.config.config import settings
from app.core.logging_setup import setup_logging
from loguru import logger
from app.core.brain import Brain
from app.core.context import context
from app.core.state_machine import state_machine
from app.voice.voice_manager import VoiceManager, voice_input_queue
from app.voice.voice_typer import LiveVoiceTyper

# Initialize logger early based on command line arguments
cli_mode = "--server" not in sys.argv
setup_logging(cli_mode=cli_mode)

console = Console()
brain = Brain()
session_id = str(uuid.uuid4())

# Initialize Voice Manager
voice_manager = VoiceManager()
voice_manager.start()
context.voice_active = voice_manager.enabled

logger.info("State machine initialized") if state_machine else None

# Initialize and start Live Voice Typer
voice_typer = LiveVoiceTyper()
voice_typer.start()

from app.automation.event_engine import event_engine
from app.automation.scheduler import scheduler

# Start Event Engine & Scheduler
event_engine.start()
scheduler.start()

text_input_queue = queue.Queue()

def console_reader():
    """
    Background worker thread reading user keyboard inputs to avoid blocking the main thread.
    """
    while True:
        try:
            # We use a simple prompt. Since print() outputs are asynchronous,
            # we don't block the screen printouts.
            inp = input("You: ").strip()
            if inp:
                text_input_queue.put(inp)
        except Exception:
            break

def main():
    import argparse
    parser = argparse.ArgumentParser(description="KLAUSE desktop runtime")
    parser.add_argument("--server", action="store_true", help="Launch backend FastAPI service layer")
    args = parser.parse_args()

    if args.server:
        console.print(Panel.fit(
            f"[bold green]KLAUSE Server Mode[/bold green]\n"
            f"Local server token initialized in data/.server_token.\n"
            f"FastAPI endpoints running at: [bold cyan]http://localhost:8000[/bold cyan]\n"
            f"Press [bold red]Ctrl+C[/bold red] to stop.",
            title="[bold cyan]System Booted[/bold cyan]",
            border_style="cyan"
        ))
        from app.api.server import start_server
        try:
            start_server()
        except KeyboardInterrupt:
            pass
        finally:
            console.print("\n[bold yellow]Shutting down KLAUSE Server. Goodbye![/bold yellow]")
            event_engine.stop()
            scheduler.stop()
        return

    console.print(Panel.fit(
        f"[bold green]KLAUSE {settings.klause.version}[/bold green] — Personal AI Engineering Assistant\n"
        f"Session ID: [bold yellow]{session_id}[/bold yellow]\n"
        f"Voice Trigger: [bold {'green' if voice_manager.enabled else 'red'}]{'Push-To-Talk (ctrl+space)' if voice_manager.enabled else 'Disabled'}[/bold {'green' if voice_manager.enabled else 'red'}]\n"
        "Type [bold red]exit[/bold red] or [bold red]quit[/bold red] to end the session.",
        title="[bold cyan]System Booted[/bold cyan]",
        border_style="cyan"
    ))
    
    # Start console input reader thread
    reader_thread = threading.Thread(target=console_reader, daemon=True)
    reader_thread.start()
    
    while True:
        try:
            user_input = None
            is_voice = False
            
            # Check vocal inputs queue
            if not voice_input_queue.empty():
                user_input = voice_input_queue.get()
                # Echo captured voice command to CLI
                console.print(f"[bold yellow]You (Voice):[/bold yellow] {user_input}")
                is_voice = True
            # Check keyboard inputs queue
            elif not text_input_queue.empty():
                user_input = text_input_queue.get()
                
            if user_input:
                # Instantly interrupt any active speaking outputs
                voice_manager.stop_speaking()
                
                if user_input.lower() in ("exit", "quit"):
                    console.print("[bold yellow]Shutting down KLAUSE. Goodbye![/bold yellow]")
                    voice_typer.stop()
                    event_engine.stop()
                    scheduler.stop()
                    break
                    
                # Beautiful console step-by-step progress tracking callback
                def terminal_step_callback(step_data):
                    if step_data["type"] == "thought":
                        step_num = step_data["step"]
                        thought = step_data["thought"]
                        action = step_data["action"]
                        # Truncate thought description to fit clean terminal display
                        disp_thought = thought if len(thought) < 70 else thought[:67] + "..."
                        console.print(f"  [bold yellow]└─ Step {step_num}[/bold yellow] thought: {disp_thought}")
                        if action != "FINAL":
                            # Extract simplified parameters for logging display
                            disp_params = {k: (v if len(str(v)) < 40 else str(v)[:37] + "...") for k, v in step_data["params"].items()}
                            console.print(f"     [bold blue]⚙ Calling tool:[/bold blue] [bold cyan]{action}[/bold cyan] with params: {disp_params}")
                    elif step_data["type"] == "observation":
                        obs = step_data["observation"]
                        step_num = step_data["step"]
                        if obs["success"]:
                            res_str = str(obs["result"]).strip()
                            disp_res = res_str if len(res_str) < 80 else res_str[:77] + "..."
                            console.print(f"     [bold green]✔ Observation success:[/bold green] {disp_res}")
                        else:
                            console.print(f"     [bold red]✖ Observation failure:[/bold red] {obs['error']}")

                console.print(f"\n[bold yellow]Thinking...[/bold yellow]")
                response = brain.think(user_input, session_id=session_id, step_callback=terminal_step_callback)
                console.print(f"\n[bold cyan]KLAUSE:[/bold cyan] {response}\n")
                
                # Speak response back to user
                if voice_manager.enabled:
                    voice_manager.speak(response)
                    
            # Prevent high CPU usage by yielding time slice
            time.sleep(0.05)
            
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Session interrupted. Goodbye![/bold yellow]")
            voice_typer.stop()
            voice_manager.stop_speaking()
            event_engine.stop()
            scheduler.stop()
            sys.exit(0)
        except Exception as e:
            console.print(f"[bold red]System Error:[/bold red] {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
