import os
import sys
import logging
import typer
from rich.console import Console
from rich.panel import Panel
from rich.logging import RichHandler
from rich.table import Table
from dotenv import load_dotenv

from .graph import create_graph
from .errors import ErrorType, format_error_for_display, ClassifiedError

# Load environment variables from .env file
load_dotenv()

app = typer.Typer()
console = Console()

# Configure logging with RichHandler for beautiful output
# Disable rich_tracebacks to prevent verbose traceback output
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=False, show_path=False)]
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
                        
            console.print(f"[green]Loaded custom instructions from {dockai_file_path}[/green]")
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
        logger.error(f"Problem: Path '{path}' does not exist.")
        raise typer.Exit(code=1)
        
    # Validate API key
    if not os.getenv("OPENAI_API_KEY"):
        console.print("[bold red]Error:[/bold red] OPENAI_API_KEY not found in environment variables.")
        console.print("Please create a .env file with your API key.")
        logger.error("Problem: OPENAI_API_KEY missing")
        raise typer.Exit(code=1)

    # Validate model configuration
    if not os.getenv("MODEL_ANALYZER") or not os.getenv("MODEL_GENERATOR"):
        console.print("[bold red]Error:[/bold red] Model configuration missing.")
        console.print("Please set MODEL_ANALYZER and MODEL_GENERATOR in your .env file.")
        logger.error("Problem: Model configuration missing")
        raise typer.Exit(code=1)

    console.print(Panel.fit("[bold blue]DockAI[/bold blue]\n[italic]Adaptive Agentic Workflow powered by LangGraph[/italic]"))
    logger.info(f"Starting analysis for: {path}")

    # Load instructions
    analyzer_instructions, generator_instructions = load_instructions(path)
    
    # Initialize State with all adaptive agent fields
    initial_state = {
        "path": os.path.abspath(path),
        "file_tree": [],
        "analysis_result": {},
        "file_contents": "",
        "dockerfile_content": "",
        "previous_dockerfile": None,  # For iterative improvement
        "validation_result": {"success": False, "message": ""},
        "retry_count": 0,
        "max_retries": int(os.getenv("MAX_RETRIES", "5")),
        "error": None,
        "error_details": None,
        "logs": [],
        "usage_stats": [],
        "config": {
            "analyzer_instructions": analyzer_instructions,
            "generator_instructions": generator_instructions
        },
        # Adaptive agent fields
        "retry_history": [],  # Full history of attempts for learning
        "current_plan": None,  # AI-generated strategic plan
        "reflection": None,  # AI reflection on failures
        "detected_health_endpoint": None,  # AI-detected from file contents
        "readiness_patterns": [],  # AI-detected startup log patterns
        "needs_reanalysis": False  # Flag to trigger re-analysis
    }

    # Create and Run Graph
    workflow = create_graph()
    
    try:
        with console.status("[bold green]Running DockAI Agent...[/bold green]", spinner="dots"):
            final_state = workflow.invoke(initial_state)
    except Exception as e:
        # Handle any unexpected errors gracefully
        error_msg = str(e)
        
        # Check for common LangGraph errors
        if "GraphRecursionError" in error_msg or "recursion" in error_msg.lower():
            console.print("\n[bold red]Max Retries Exceeded[/bold red]")
            console.print("[yellow]The system reached the maximum retry limit while trying to generate a valid Dockerfile.[/yellow]\n")
            console.print("[bold]Check the error details above for specific guidance on how to fix the issue.[/bold]")
            console.print("[dim]You can also increase MAX_RETRIES in .env or run with --verbose for more details.[/dim]\n")
        else:
            console.print(f"\n[bold red]Unexpected Error[/bold red]")
            console.print(f"[yellow]{error_msg[:200]}[/yellow]\n")
            if verbose:
                console.print_exception()
        
        raise typer.Exit(code=1)

    # Process Results
    validation_result = final_state["validation_result"]
    output_path = os.path.join(path, "Dockerfile")
    
    if validation_result["success"]:
        console.print(f"\n[bold green]✅ Success![/bold green] Dockerfile validated successfully.")
        console.print(f"[bold green]📄 Final Dockerfile saved to {output_path}[/bold green]")
        
        # Show retry history summary if there were retries
        retry_history = final_state.get("retry_history", [])
        if retry_history:
            console.print(f"\n[cyan]🔄 Adaptive Learning: {len(retry_history)} iterations to reach solution[/cyan]")
            for i, attempt in enumerate(retry_history, 1):
                console.print(f"  [dim]Attempt {i}: {attempt.get('lesson_learned', 'N/A')}[/dim]")
        
        # Calculate Costs
        total_tokens = 0
        usage_by_stage = {}
        
        for stat in final_state.get("usage_stats", []):
            total_tokens += stat["total_tokens"]
            stage = stat['stage']
            if stage not in usage_by_stage:
                usage_by_stage[stage] = 0
            usage_by_stage[stage] += stat["total_tokens"]
        
        usage_details = [f"{stage}: {tokens} tokens" for stage, tokens in usage_by_stage.items()]
        
        # Build summary with adaptive agent stats
        summary_content = f"[bold]Total Tokens:[/bold] {total_tokens}\n\n"
        summary_content += "[bold]Breakdown by Stage:[/bold]\n" + "\n".join(f"  • {d}" for d in usage_details)
        
        # Add plan info if available
        current_plan = final_state.get("current_plan")
        if current_plan:
            summary_content += f"\n\n[bold]Strategy Used:[/bold]\n"
            summary_content += f"  • Base Image: {current_plan.get('base_image_strategy', 'N/A')[:50]}..."
            summary_content += f"\n  • Multi-stage: {'Yes' if current_plan.get('use_multi_stage') else 'No'}"
            
        console.print(Panel(
            summary_content,
            title="📊 Usage Summary",
            border_style="blue"
        ))
    else:
        console.print(f"\n[bold red]❌ Failed to generate a valid Dockerfile[/bold red]\n")
        
        # Display classified error information if available
        error_details = final_state.get("error_details")
        
        if error_details:
            error_type = error_details.get("error_type", "unknown_error")
            
            # Create error type display with icons
            error_type_icons = {
                "project_error": "🔧 Project Error",
                "dockerfile_error": "🐳 Dockerfile Error", 
                "environment_error": "💻 Environment Error",
                "unknown_error": "❓ Unknown Error",
                "security_review": "🔒 Security Error"
            }
            
            error_type_display = error_type_icons.get(error_type, "Error")
            
            # Build error panel
            error_content = f"[bold]{error_type_display}[/bold]\n\n"
            error_content += f"[red]Problem:[/red] {error_details.get('message', 'Unknown error')}\n\n"
            error_content += f"[green]Solution:[/green] {error_details.get('suggestion', 'Check the logs for details')}"
            
            # Add retry info based on error type
            if error_type == "project_error":
                error_content += "\n\n[yellow]⚠️ This is a project configuration issue that cannot be fixed by retrying.[/yellow]"
                error_content += "\n[yellow]Please fix the issue in your project and try again.[/yellow]"
            elif error_type == "environment_error":
                error_content += "\n\n[yellow]⚠️ This is a local environment issue.[/yellow]"
                error_content += "\n[yellow]Please fix your Docker/system configuration and try again.[/yellow]"
            
            console.print(Panel(
                error_content,
                title="Error Details",
                border_style="red"
            ))
        else:
            # Fallback to simple error message
            error_msg = final_state.get('error', 'Unknown error occurred')
            console.print(f"[red]Error: {error_msg[:300]}[/red]")
        
        # Show retry history with lessons learned
        retry_history = final_state.get("retry_history", [])
        retry_count = final_state.get("retry_count", 0)
        max_retries = final_state.get("max_retries", 5)
        
        if retry_history:
            console.print(f"\n[cyan]🔄 Attempted {retry_count} of {max_retries} retries:[/cyan]")
            for i, attempt in enumerate(retry_history, 1):
                console.print(f"  [dim]Attempt {i}:[/dim]")
                console.print(f"    [dim]• Tried: {attempt.get('what_was_tried', 'N/A')[:60]}...[/dim]")
                console.print(f"    [dim]• Failed: {attempt.get('why_it_failed', 'N/A')[:60]}...[/dim]")
        elif retry_count > 0:
            console.print(f"\n[dim]Attempted {retry_count} of {max_retries} retries before stopping.[/dim]")
        
        # Show reflection insight if available
        reflection = final_state.get("reflection")
        if reflection:
            console.print(f"\n[cyan]💡 Final Analysis:[/cyan]")
            console.print(f"  [dim]Root Cause: {reflection.get('root_cause_analysis', 'N/A')[:100]}...[/dim]")
        
        # Show token usage even on failure
        total_tokens = 0
        for stat in final_state.get("usage_stats", []):
            total_tokens += stat["total_tokens"]
        if total_tokens > 0:
            console.print(f"\n[dim]Tokens used: {total_tokens}[/dim]")
        
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
