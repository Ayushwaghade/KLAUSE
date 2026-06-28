import sys
import time
import queue
import threading
import uuid
from rich.console import Console
from rich.panel import Panel
from app.config.config import settings
from app.core.logging_setup import setup_logging
from app.core.brain import Brain
from app.voice.voice_manager import VoiceManager, voice_input_queue

# Initialize logger
setup_logging()

console = Console()
brain = Brain()
session_id = str(uuid.uuid4())

# Initialize Voice Manager
voice_manager = VoiceManager()
voice_manager.start()

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
                    break
                    
                response = brain.think(user_input, session_id=session_id)
                console.print(f"[bold cyan]KLAUSE:[/bold cyan] {response}\n")
                
                # Speak response back to user
                if voice_manager.enabled:
                    voice_manager.speak(response)
                    
            # Prevent high CPU usage by yielding time slice
            time.sleep(0.05)
            
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Session interrupted. Goodbye![/bold yellow]")
            voice_manager.stop_speaking()
            sys.exit(0)
        except Exception as e:
            console.print(f"[bold red]System Error:[/bold red] {e}")
            time.sleep(1)

if __name__ == "__main__":
    main()
