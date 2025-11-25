import os
import logging
import typer
from rich.console import Console
from rich.panel import Panel
from rich.logging import RichHandler
from dotenv import load_dotenv

from .graph import create_graph

# Load environment variables from .env file
load_dotenv()

app = typer.Typer()
console = Console()

# Configure logging with RichHandler for beautiful output
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)]
)
logger = logging.getLogger("dockai")

def load_instructions(path: str):
    analyzer_instructions = ""
    generator_instructions = ""
    
    # Check environment variables
    if os.getenv("DOCKAI_ANALYZER_INSTRUCTIONS"):
        analyzer_instructions += f"\nFrom Environment Variable:\n{os.getenv('DOCKAI_ANALYZER_INSTRUCTIONS')}\n"
        
    if os.getenv("DOCKAI_GENERATOR_INSTRUCTIONS"):
        generator_instructions += f"\nFrom Environment Variable:\n{os.getenv('DOCKAI_GENERATOR_INSTRUCTIONS')}\n"
        
    # Check .dockai file in the target directory
    dockai_file_path = os.path.join(path, ".dockai")
    if os.path.exists(dockai_file_path):
        try:
            with open(dockai_file_path, "r") as f:
                content = f.read()
                
                # Parse sections: [analyzer] and [generator]
                if "[analyzer]" in content.lower() or "[generator]" in content.lower():
                    # Split by sections
                    lines = content.split('\n')
                    current_section = None
                    section_content = {"analyzer": [], "generator": []}
                    
                    for line in lines:
                        line_lower = line.strip().lower()
                        if line_lower == "[analyzer]":
                            current_section = "analyzer"
                        elif line_lower == "[generator]":
                            current_section = "generator"
                        elif current_section and line.strip() and not line.strip().startswith('#'):
                            section_content[current_section].append(line)
                    
                    if section_content["analyzer"]:
                        analyzer_instructions += f"\nFrom .dockai file:\n" + "\n".join(section_content["analyzer"]) + "\n"
                    if section_content["generator"]:
                        generator_instructions += f"\nFrom .dockai file:\n" + "\n".join(section_content["generator"]) + "\n"
                else:
                    # No sections, use for both
                    shared_instructions = content.strip()
                    if shared_instructions:
                        analyzer_instructions += f"\nFrom .dockai file:\n{shared_instructions}\n"
                        generator_instructions += f"\nFrom .dockai file:\n{shared_instructions}\n"
                        
            console.print(f"[green]✓[/green] Loaded custom instructions from {dockai_file_path}")
            logger.info(f"Loaded custom instructions from {dockai_file_path}")
        except Exception as e:
            console.print(f"[yellow]Warning:[/yellow] Could not read .dockai file: {e}")
            logger.warning(f"Could not read .dockai file: {e}")

    return analyzer_instructions, generator_instructions

@app.command()
def run(
    path: str = typer.Argument(..., help="Path to the repository to analyze"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose debug logging")
):
    """
    DockAI: A LangGraph Agentic Pipeline for generating optimized Dockerfiles.
    """
    if verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")
    
    # Validate input path
    if not os.path.exists(path):
        console.print(f"[bold red]Error:[/bold red] Path '{path}' does not exist.")
        logger.error(f"Path '{path}' does not exist.")
        raise typer.Exit(code=1)
        
    # Validate API key
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[bold red]Error:[/bold red] OPENAI_API_KEY not found in environment variables.")
        console.print("Please create a .env file with your API key.")
        logger.error("OPENAI_API_KEY missing")
        raise typer.Exit(code=1)

    # Validate model configuration
    if not os.getenv("MODEL_ANALYZER") or not os.getenv("MODEL_GENERATOR"):
        console.print("[bold red]Error:[/bold red] Model configuration missing.")
        console.print("Please set MODEL_ANALYZER and MODEL_GENERATOR in your .env file.")
        logger.error("Model configuration missing")
        raise typer.Exit(code=1)

    console.print(Panel.fit("[bold blue]DockAI[/bold blue]\n[italic]Agentic Workflow powered by LangGraph[/italic]"))
    logger.info(f"Starting analysis for: {path}")

    # Load instructions
    analyzer_instructions, generator_instructions = load_instructions(path)
    
    # Initialize State
    initial_state = {
        "path": os.path.abspath(path),
        "file_tree": [],
        "analysis_result": {},
        "file_contents": "",
        "dockerfile_content": "",
        "validation_result": {"success": False, "message": ""},
        "retry_count": 0,
        "max_retries": int(os.getenv("MAX_RETRIES", "3")),
        "error": None,
        "logs": [],
        "usage_stats": [],
        "config": {
            "analyzer_instructions": analyzer_instructions,
            "generator_instructions": generator_instructions
        }
    }

    # Create and Run Graph
    workflow = create_graph()
    
    with console.status("[bold green]Running DockAI Agent...[/bold green]", spinner="dots"):
        final_state = workflow.invoke(initial_state)

    # Process Results
    validation_result = final_state["validation_result"]
    output_path = os.path.join(path, "Dockerfile")
    
    if validation_result["success"]:
        console.print(f"[bold green]Success![/bold green] Dockerfile validated successfully.")
        console.print(f"[bold green]Final Dockerfile saved to {output_path}[/bold green]")

        
        # Calculate Costs
        total_tokens = 0
        usage_details = []
        
        for stat in final_state.get("usage_stats", []):
            total_tokens += stat["total_tokens"]
            usage_details.append(f"{stat['stage']}: {stat['total_tokens']} tokens")
            
        console.print(Panel(
            f"Total Tokens: {total_tokens}\n\nDetails:\n" + "\n".join(usage_details),
            title="Usage Summary",
            border_style="blue"
        ))
    else:
        console.print(f"[bold red]Failed to generate a valid Dockerfile.[/bold red]")
        console.print(f"[red]Last Error: {final_state.get('error')}[/red]")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
