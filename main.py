import os
import typer
from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from rich.tree import Tree
from dotenv import load_dotenv

# Import our modules
from scanner import get_file_tree
from analyzer import analyze_repo_needs
from generator import generate_dockerfile

# Load environment variables
load_dotenv()

app = typer.Typer()
console = Console()

@app.command()
def run(path: str = typer.Argument(..., help="Path to the repository to analyze")):
    """
    Autodock-Research: A Two-Stage LLM Pipeline for generating optimized Dockerfiles.
    """
    
    if not os.path.exists(path):
        console.print(f"[bold red]Error:[/bold red] Path '{path}' does not exist.")
        raise typer.Exit(code=1)
        
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[bold red]Error:[/bold red] OPENAI_API_KEY not found in environment variables.")
        console.print("Please create a .env file with your API key.")
        raise typer.Exit(code=1)

    console.print(Panel.fit("[bold blue]Autodock-Research[/bold blue]\n[italic]University Thesis - Two-Stage LLM Pipeline[/italic]"))

    # --- Stage 1: Scanning ---
    with console.status("[bold green]Stage 1: Scanning directory structure...[/bold green]", spinner="dots") as status:
        file_tree = get_file_tree(path)
        # Simulate a small delay or just show completion
        console.print(f"[green]✓[/green] Found {len(file_tree)} files.")
        
        # Optional: Show tree
        # tree = Tree("Repository")
        # for f in file_tree[:10]: tree.add(f)
        # if len(file_tree) > 10: tree.add(f"... and {len(file_tree)-10} more")
        # console.print(tree)

        # --- Stage 1.5: Analysis ---
        status.update("[bold green]Stage 1: Analyzing repository needs (The Brain)...[/bold green]")
        analysis_result = analyze_repo_needs(file_tree)
        
    stack = analysis_result.get("stack", "Unknown")
    files_to_read = analysis_result.get("files_to_read", [])
    
    console.print(f"[bold cyan]Identified Stack:[/bold cyan] {stack}")
    console.print(f"[bold cyan]Critical Files:[/bold cyan] {', '.join(files_to_read)}")

    # --- Stage 2: Reading Content ---
    file_contents_str = ""
    with console.status(f"[bold yellow]Stage 2: Reading {len(files_to_read)} critical files...[/bold yellow]", spinner="dots"):
        for rel_path in files_to_read:
            abs_file_path = os.path.join(path, rel_path)
            try:
                with open(abs_file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    file_contents_str += f"--- FILE: {rel_path} ---\n{content}\n\n"
            except Exception as e:
                console.print(f"[red]Warning:[/red] Could not read {rel_path}: {e}")

    # --- Stage 3: Generation ---
    with console.status("[bold magenta]Stage 3: Generating Dockerfile (The Architect)...[/bold magenta]", spinner="earth"):
        dockerfile_content = generate_dockerfile(stack, file_contents_str)

    # Save the result
    output_path = os.path.join(path, "Dockerfile")
    with open(output_path, "w") as f:
        f.write(dockerfile_content)

    console.print(Panel(dockerfile_content, title="Generated Dockerfile", border_style="green"))
    console.print(f"[bold green]Success![/bold green] Dockerfile saved to {output_path}")

if __name__ == "__main__":
    app()
