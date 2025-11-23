import os
import logging
import typer
from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from rich.tree import Tree
from rich.logging import RichHandler
from dotenv import load_dotenv

from .scanner import get_file_tree
from .analyzer import analyze_repo_needs
from .generator import generate_dockerfile

load_dotenv()

app = typer.Typer()
console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)]
)
logger = logging.getLogger("dockai")

@app.command()
def run(
    path: str = typer.Argument(..., help="Path to the repository to analyze"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose debug logging")
):
    """
    DockAI: A Two-Stage LLM Pipeline for generating optimized Dockerfiles.
    """
    if verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")
    
    if not os.path.exists(path):
        console.print(f"[bold red]Error:[/bold red] Path '{path}' does not exist.")
        logger.error(f"Path '{path}' does not exist.")
        raise typer.Exit(code=1)
        
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[bold red]Error:[/bold red] OPENAI_API_KEY not found in environment variables.")
        console.print("Please create a .env file with your API key.")
        logger.error("OPENAI_API_KEY missing")
        raise typer.Exit(code=1)

    if not os.getenv("MODEL_ANALYZER") or not os.getenv("MODEL_GENERATOR"):
        console.print("[bold red]Error:[/bold red] Model configuration missing.")
        console.print("Please set MODEL_ANALYZER and MODEL_GENERATOR in your .env file.")
        logger.error("Model configuration missing")
        raise typer.Exit(code=1)

    console.print(Panel.fit("[bold blue]DockAI[/bold blue]\n[italic]University Thesis - Two-Stage LLM Pipeline[/italic]"))
    logger.info(f"Starting analysis for: {path}")

    # =========================================================================
    # STAGE 1: SCANNING
    # Map the file structure while ignoring noise (node_modules, etc.)
    # =========================================================================
    with console.status("[bold green]Stage 1: Scanning directory structure...[/bold green]", spinner="dots") as status:
        file_tree = get_file_tree(path)
        console.print(f"[green]✓[/green] Found {len(file_tree)} files.")
        logger.debug(f"File tree: {file_tree}")
        
        # =========================================================================
        # STAGE 1.5: ANALYSIS (THE BRAIN)
        # Send file list to AI to identify stack and critical files.
        # =========================================================================
        status.update("[bold green]Stage 1: Analyzing repository needs (The Brain)...[/bold green]")
        try:
            analysis_result = analyze_repo_needs(file_tree)
            logger.debug(f"Analysis result: {analysis_result}")
        except Exception as e:
            console.print(f"[bold red]Error during analysis:[/bold red] {e}")
            logger.exception("Error during analysis")
            raise typer.Exit(code=1)
        
    stack = analysis_result.get("stack", "Unknown")
    files_to_read = analysis_result.get("files_to_read", [])
    
    console.print(f"[bold cyan]Identified Stack:[/bold cyan] {stack}")
    console.print(f"[bold cyan]Critical Files:[/bold cyan] {', '.join(files_to_read)}")
    logger.info(f"Stack: {stack}, Critical Files: {files_to_read}")

    # =========================================================================
    # STAGE 2: CONTEXT GATHERING
    # Read only the specific files requested by the Brain.
    # =========================================================================
    file_contents_str = ""
    with console.status(f"[bold yellow]Stage 2: Reading {len(files_to_read)} critical files...[/bold yellow]", spinner="dots"):
        for rel_path in files_to_read:
            abs_file_path = os.path.join(path, rel_path)
            try:
                with open(abs_file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    file_contents_str += f"--- FILE: {rel_path} ---\n{content}\n\n"
                logger.debug(f"Read file: {rel_path}")
            except Exception as e:
                console.print(f"[red]Warning:[/red] Could not read {rel_path}: {e}")
                logger.warning(f"Could not read {rel_path}: {e}")

    # =========================================================================
    # STAGE 3: GENERATION (THE ARCHITECT)
    # Synthesize the Dockerfile using the gathered context.
    # =========================================================================
    with console.status("[bold magenta]Stage 3: Generating Dockerfile (The Architect)...[/bold magenta]", spinner="earth"):
        try:
            dockerfile_content = generate_dockerfile(stack, file_contents_str)
            logger.debug("Dockerfile generated successfully")
        except Exception as e:
            console.print(f"[bold red]Error during generation:[/bold red] {e}")
            logger.exception("Error during generation")
            raise typer.Exit(code=1)

    # Save the result
    output_path = os.path.join(path, "Dockerfile")
    with open(output_path, "w") as f:
        f.write(dockerfile_content)

    console.print(Panel(dockerfile_content, title="Generated Dockerfile", border_style="green"))
    console.print(f"[bold green]Success![/bold green] Dockerfile saved to {output_path}")
    logger.info(f"Dockerfile saved to {output_path}")

if __name__ == "__main__":
    app()
