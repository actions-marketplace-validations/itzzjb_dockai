"""
DockAI Main Entry Point.

This module serves as the command-line interface (CLI) entry point for the DockAI application.
It handles argument parsing, environment validation, logging configuration, and the initialization
of the main agent workflow.
"""

import os
import sys
import logging
import warnings

# Suppress Pydantic V1 compatibility warning with Python 3.14+
warnings.filterwarnings("ignore", message=".*Pydantic V1.*Python 3.14.*")

import typer
from dotenv import load_dotenv

from .graph import create_graph
from . import ui

# Load environment variables from .env file
load_dotenv()

# Initialize Typer application with Rich markup support
app = typer.Typer(rich_markup_mode="rich")

# Configure logging using the centralized setup from the UI module
logger = ui.setup_logging()

def load_instructions(path: str):
    """
    Loads custom instructions for the AI agent from various sources.

    Instructions can be provided via:
    1. Environment variables (DOCKAI_ANALYZER_INSTRUCTIONS, DOCKAI_GENERATOR_INSTRUCTIONS).
    2. A local `.dockai` file in the target directory.

    The `.dockai` file supports sections `[analyzer]` and `[generator]` to target specific
    phases of the pipeline.

    Args:
        path (str): The absolute path to the target directory where `.dockai` might exist.

    Returns:
        Tuple[str, str]: A tuple containing (analyzer_instructions, generator_instructions).
    """
    analyzer_instructions = ""
    generator_instructions = ""
    
    # Check environment variables first
    if os.getenv("DOCKAI_ANALYZER_INSTRUCTIONS"):
        analyzer_instructions += f"\nFrom Environment Variable:\n{os.getenv('DOCKAI_ANALYZER_INSTRUCTIONS')}\n"
        
    if os.getenv("DOCKAI_GENERATOR_INSTRUCTIONS"):
        generator_instructions += f"\nFrom Environment Variable:\n{os.getenv('DOCKAI_GENERATOR_INSTRUCTIONS')}\n"
        
    # Check for a .dockai file in the target directory
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
                    # No sections found, apply instructions to both phases
                    shared_instructions = content.strip()
                    if shared_instructions:
                        analyzer_instructions += f"\nFrom .dockai file:\n{shared_instructions}\n"
                        generator_instructions += f"\nFrom .dockai file:\n{shared_instructions}\n"
                        
            logger.info(f"Loaded custom instructions from {dockai_file_path}")
        except Exception as e:
            ui.print_warning(f"Could not read .dockai file: {e}")
            logger.warning(f"Could not read .dockai file: {e}")

    return analyzer_instructions, generator_instructions

@app.command()
def run(
    path: str = typer.Argument(..., help="Path to the repository to analyze"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose debug logging")
):
    """
    [bold blue]DockAI[/bold blue]
    
    [italic]Adaptive Agentic Workflow powered by LangGraph[/italic]
    """
    if verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")
    
    # Validate input path existence
    if not os.path.exists(path):
        ui.print_error("Path Error", f"Path '{path}' does not exist.")
        logger.error(f"Problem: Path '{path}' does not exist.")
        raise typer.Exit(code=1)
        
    # Validate API key configuration
    if not os.getenv("OPENAI_API_KEY"):
        ui.print_error("Configuration Error", "OPENAI_API_KEY not found in environment variables.", "Please create a .env file with your API key or set the OPENAI_API_KEY environment variable.")
        logger.error("Problem: OPENAI_API_KEY missing")
        raise typer.Exit(code=1)
    
    # Log model configuration (uses defaults if not set)
    model_analyzer = os.getenv("MODEL_ANALYZER", "gpt-4o-mini")
    model_generator = os.getenv("MODEL_GENERATOR", "gpt-4o")
    logger.info(f"Using models - Analyzer: {model_analyzer}, Generator: {model_generator}")

    ui.print_welcome()
    logger.info(f"Starting analysis for: {path}")

    # Load custom instructions
    analyzer_instructions, generator_instructions = load_instructions(path)
    
    # Initialize the workflow state with all necessary fields
    initial_state = {
        "path": os.path.abspath(path),
        "file_tree": [],
        "analysis_result": {},
        "file_contents": "",
        "dockerfile_content": "",
        "previous_dockerfile": None,  # For iterative improvement
        "validation_result": {"success": False, "message": ""},
        "retry_count": 0,
        "max_retries": int(os.getenv("MAX_RETRIES", "3")),
        "error": None,
        "error_details": None,
        "logs": [],
        "usage_stats": [],
        "config": {
            "analyzer_instructions": analyzer_instructions,
            "generator_instructions": generator_instructions
        },
        # Adaptive agent fields for learning and planning
        "retry_history": [],  # Full history of attempts for learning
        "current_plan": None,  # AI-generated strategic plan
        "reflection": None,  # AI reflection on failures
        "detected_health_endpoint": None,  # AI-detected from file contents
        "readiness_patterns": [],  # AI-detected startup log patterns
        "failure_patterns": [],  # AI-detected failure log patterns
        "needs_reanalysis": False  # Flag to trigger re-analysis
    }

    # Create and compile the LangGraph workflow
    workflow = create_graph()
    
    try:
        # Execute the workflow with a visual spinner
        with ui.get_status_spinner("[bold green]Running DockAI Agent...[/bold green]"):
            final_state = workflow.invoke(initial_state)
    except Exception as e:
        # Handle unexpected errors gracefully
        error_msg = str(e)
        
        # Check for common LangGraph errors like recursion limits
        if "GraphRecursionError" in error_msg or "recursion" in error_msg.lower():
            ui.print_error(
                "Max Retries Exceeded", 
                "The system reached the maximum retry limit while trying to generate a valid Dockerfile.",
                "Check the error details above for specific guidance on how to fix the issue.\nYou can also increase MAX_RETRIES in .env or run with --verbose for more details."
            )
        else:
            ui.print_error("Unexpected Error", error_msg[:200])
            if verbose:
                logger.exception("Unexpected error")
        
        raise typer.Exit(code=1)

    # Process and display the final results
    validation_result = final_state["validation_result"]
    output_path = os.path.join(path, "Dockerfile")
    
    if validation_result["success"]:
        ui.display_summary(final_state, output_path)
    else:
        ui.display_failure(final_state)
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
