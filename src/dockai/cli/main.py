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

from ..workflow.graph import create_graph
from . import ui
from ..utils.prompts import load_prompts, set_prompt_config

# Load environment variables from .env file
load_dotenv()

# Initialize Typer application with Rich markup support
app = typer.Typer(rich_markup_mode="rich")

# Configure logging using the centralized setup from the UI module
logger = ui.setup_logging()

def load_instructions(path: str):
    """
    Loads custom instructions and prompts for the AI agent from various sources.

    Instructions and prompts can be provided via:
    1. Environment variables (DOCKAI_*_INSTRUCTIONS, DOCKAI_PROMPT_*)
    2. A local `.dockai` file in the target directory.

    The `.dockai` file supports sections:
    - [analyzer], [generator] - Legacy sections for backward compatibility
    - [instructions_*] - Extra instructions appended to default prompts
    - [prompt_*] - Complete prompt replacements

    Args:
        path (str): The absolute path to the target directory where `.dockai` might exist.

    Returns:
        Tuple[str, str]: A tuple containing (analyzer_instructions, generator_instructions) for backward compatibility.
    """
    # Load and set custom prompts and instructions configuration
    # This handles all 10 prompts and their instructions from env vars and .dockai file
    prompt_config = load_prompts(path)
    set_prompt_config(prompt_config)
    logger.debug("Custom prompts and instructions configuration loaded")
    
    # Return analyzer and generator instructions for backward compatibility with the config dict
    return (
        prompt_config.analyzer_instructions or "",
        prompt_config.generator_instructions or ""
    )

@app.command()
def run(
    path: str = typer.Argument(..., help="Path to the repository to analyze"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose debug logging")
):
    """
    [bold blue]DockAI[/bold blue]
    
    [italic]The Customizable AI Dockerfile Generation Framework[/italic]
    """
    if verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")
    
    # Validate input path existence
    if not os.path.exists(path):
        ui.print_error("Path Error", f"Path '{path}' does not exist.")
        logger.error(f"Problem: Path '{path}' does not exist.")
        raise typer.Exit(code=1)
    
    # Import and initialize LLM provider configuration
    from ..core.llm_providers import get_llm_config, load_llm_config_from_env, set_llm_config, log_provider_info, LLMProvider
    
    # Load LLM configuration from environment
    llm_config = load_llm_config_from_env()
    set_llm_config(llm_config)
    
    # Validate API key configuration based on provider
    if llm_config.provider == LLMProvider.OPENAI:
        if not os.getenv("OPENAI_API_KEY"):
            ui.print_error("Configuration Error", "OPENAI_API_KEY not found in environment variables.", 
                          "Please create a .env file with your API key or set the OPENAI_API_KEY environment variable.")
            logger.error("Problem: OPENAI_API_KEY missing")
            raise typer.Exit(code=1)
    elif llm_config.provider == LLMProvider.AZURE:
        if not os.getenv("AZURE_OPENAI_API_KEY"):
            ui.print_error("Configuration Error", "AZURE_OPENAI_API_KEY not found in environment variables.",
                          "Please set AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT environment variables.")
            logger.error("Problem: AZURE_OPENAI_API_KEY missing")
            raise typer.Exit(code=1)
        if not llm_config.azure_endpoint:
            ui.print_error("Configuration Error", "AZURE_OPENAI_ENDPOINT not found in environment variables.",
                          "Please set the AZURE_OPENAI_ENDPOINT environment variable.")
            logger.error("Problem: AZURE_OPENAI_ENDPOINT missing")
            raise typer.Exit(code=1)
    elif llm_config.provider == LLMProvider.GEMINI:
        if not os.getenv("GOOGLE_API_KEY"):
            ui.print_error("Configuration Error", "GOOGLE_API_KEY not found in environment variables.",
                          "Please set the GOOGLE_API_KEY environment variable.")
            logger.error("Problem: GOOGLE_API_KEY missing")
            raise typer.Exit(code=1)
    elif llm_config.provider == LLMProvider.ANTHROPIC:
        if not os.getenv("ANTHROPIC_API_KEY"):
            ui.print_error("Configuration Error", "ANTHROPIC_API_KEY not found in environment variables.",
                          "Please set the ANTHROPIC_API_KEY environment variable.")
            logger.error("Problem: ANTHROPIC_API_KEY missing")
            raise typer.Exit(code=1)
    
    # Log LLM provider and model configuration
    log_provider_info()

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
        with ui.get_status_spinner("[bold green]Running DockAI Framework...[/bold green]"):
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
