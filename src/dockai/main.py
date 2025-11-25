import os
import logging
import typer
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from rich.tree import Tree
from rich.logging import RichHandler
from dotenv import load_dotenv

from .scanner import get_file_tree
from .analyzer import analyze_repo_needs
from .generator import generate_dockerfile
from .validator import validate_docker_build_and_run

# Load environment variables from .env file
load_dotenv()

PRICING_URL = "https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json"

cached_pricing = None

def get_pricing_data():
    global cached_pricing
    if cached_pricing:
        return cached_pricing
    
    try:
        # Short timeout to not block execution too long
        response = httpx.get(PRICING_URL, timeout=2.0)
        response.raise_for_status()
        cached_pricing = response.json()
        return cached_pricing
    except Exception:
        return None

def calculate_cost(model, prompt_tokens, completion_tokens):
    pricing_data = get_pricing_data()
    
    if pricing_data and model in pricing_data:
        try:
            info = pricing_data[model]
            input_rate = info.get("input_cost_per_token", 0)
            output_rate = info.get("output_cost_per_token", 0)
            
            input_cost = prompt_tokens * input_rate
            output_cost = completion_tokens * output_rate
            return input_cost + output_cost
        except Exception:
            pass 
            
    return 0.0

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

@app.command()
def run(
    path: str = typer.Argument(..., help="Path to the repository to analyze"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose debug logging")
):
    """
    DockAI: A Three-Stage Agentic Pipeline for generating optimized Dockerfiles.
    
    This command orchestrates the entire process:
    1. Scans the repository structure.
    2. Analyzes the project to identify the tech stack and critical files.
    3. Generates a Dockerfile using an LLM.
    4. Validates the Dockerfile by building and running it in a sandboxed environment.
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

    console.print(Panel.fit("[bold blue]DockAI[/bold blue]\n[italic]Three-Stage LLM Pipeline[/italic]"))
    logger.info(f"Starting analysis for: {path}")

    total_cost = 0.0
    total_tokens = 0

    # =========================================================================
    # STAGE 0: LOAD CUSTOM INSTRUCTIONS
    # Read from .dockai file or environment variables (separate for analyzer and generator)
    # =========================================================================
    
    # Pre-fetch pricing in background (or just let it happen on first call)
    # We'll log if we are using live pricing
    pricing_data = get_pricing_data()
    if pricing_data:
        logger.info("Successfully loaded live pricing data")
    else:
        logger.warning("Could not load live pricing data. Cost estimates will be unavailable.")

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

    if analyzer_instructions:
        logger.info(f"Analyzer Instructions: {analyzer_instructions}")
    if generator_instructions:
        logger.info(f"Generator Instructions: {generator_instructions}")

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
            analysis_result, usage = analyze_repo_needs(file_tree, analyzer_instructions)
            
            model = os.getenv("MODEL_ANALYZER")
            cost = calculate_cost(model, usage.prompt_tokens, usage.completion_tokens)
            total_cost += cost
            total_tokens += usage.total_tokens
            console.print(f"[dim]Analyzer Usage: {usage.total_tokens} tokens (${cost:.4f})[/dim]")
            
            logger.debug(f"Analysis result: {analysis_result}")
        except Exception as e:
            console.print(f"[bold red]Error during analysis:[/bold red] {e}")
            logger.exception("Error during analysis")
            raise typer.Exit(code=1)
        
    
    stack = analysis_result.get("stack", "Unknown")
    files_to_read = analysis_result.get("files_to_read", [])
    project_type = analysis_result.get("project_type", "service")
    health_endpoint_data = analysis_result.get("health_endpoint")
    recommended_wait_time = analysis_result.get("recommended_wait_time", 5)
    
    # Convert health endpoint data to tuple format if present
    health_endpoint = None
    if health_endpoint_data and isinstance(health_endpoint_data, dict):
        health_endpoint = (health_endpoint_data.get("path"), health_endpoint_data.get("port"))
        console.print(f"[green]✓[/green] AI detected health endpoint: {health_endpoint[0]} on port {health_endpoint[1]}")
        logger.info(f"Health endpoint detected: {health_endpoint[0]}:{health_endpoint[1]}")
    else:
        console.print(f"[yellow]![/yellow] No health endpoint detected by AI, will use basic validation")
        logger.info("No health endpoint detected")
    
    console.print(f"[bold cyan]Identified Stack:[/bold cyan] {stack}")
    console.print(f"[bold cyan]Project Type:[/bold cyan] {project_type}")
    console.print(f"[bold cyan]Recommended Wait Time:[/bold cyan] {recommended_wait_time}s")
    console.print(f"[bold cyan]Critical Files:[/bold cyan] {', '.join(files_to_read)}")
    logger.info(f"Stack: {stack}, Type: {project_type}, Wait Time: {recommended_wait_time}s, Critical Files: {files_to_read}")

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
    max_retries = int(os.getenv("MAX_RETRIES", "3"))
    current_try = 0
    feedback_error = None

    while current_try < max_retries:
        with console.status(f"[bold magenta]Stage 3: Generating Dockerfile (Attempt {current_try + 1}/{max_retries})...[/bold magenta]", spinner="earth"):
            try:
                # Generator now returns project_type as well
                dockerfile_content, project_type, usage = generate_dockerfile(stack, file_contents_str, generator_instructions, feedback_error)
                
                model = os.getenv("MODEL_GENERATOR")
                cost = calculate_cost(model, usage.prompt_tokens, usage.completion_tokens)
                total_cost += cost
                total_tokens += usage.total_tokens
                console.print(f"[dim]Generator Usage (Attempt {current_try + 1}): {usage.total_tokens} tokens (${cost:.4f})[/dim]")
                
                logger.debug(f"Dockerfile generated successfully. Type: {project_type}")
            except Exception as e:
                console.print(f"[bold red]Error during generation:[/bold red] {e}")
                logger.exception("Error during generation")
                raise typer.Exit(code=1)

        # Save the result
        output_path = os.path.join(path, "Dockerfile")
        with open(output_path, "w") as f:
            f.write(dockerfile_content)

        console.print(Panel(dockerfile_content, title=f"Generated Dockerfile (Attempt {current_try + 1})", border_style="green"))
        
        # Validate
        with console.status(f"[bold blue]Validating Dockerfile (Type: {project_type})...[/bold blue]", spinner="bouncingBall"):
            success, message = validate_docker_build_and_run(path, project_type, stack, health_endpoint, recommended_wait_time)
            
        if success:
            console.print(f"[bold green]Success![/bold green] Dockerfile validated successfully.")
            console.print(f"[bold green]Final Dockerfile saved to {output_path}[/bold green]")
            logger.info(f"Dockerfile validated and saved to {output_path}")
            
            console.print(Panel(
                f"Total Tokens: {total_tokens}\nTotal Cost: ${total_cost:.4f}\nModels Used: {os.getenv('MODEL_ANALYZER')}, {os.getenv('MODEL_GENERATOR')}",
                title="Usage Summary",
                border_style="blue"
            ))
            break
        else:
            # Display raw error - the AI generator will parse and fix it
            console.print(f"[bold red]Validation Failed:[/bold red]")
            console.print(f"[red]{message}[/red]")
            logger.warning(f"Validation failed: {message}")
            feedback_error = message  # Raw error sent to AI for intelligent parsing
            current_try += 1
            
            if current_try >= max_retries:
                console.print(f"[bold red]Failed to generate a valid Dockerfile after {max_retries} attempts.[/bold red]")
                raise typer.Exit(code=1)
            else:
                console.print(f"[yellow]Retrying with AI error analysis...[/yellow]")

if __name__ == "__main__":
    app()
