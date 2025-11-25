import os
import sys
import logging
import typer
from dotenv import load_dotenv

from .graph import create_graph
from . import ui

# Load environment variables from .env file
load_dotenv()

app = typer.Typer()

# Configure logging
logger = ui.setup_logging()

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
    DockAI: A LangGraph Agentic Pipeline for generating optimized Dockerfiles.
    """
    if verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose mode enabled")
    
    # Validate input path
    if not os.path.exists(path):
        ui.print_error("Path Error", f"Path '{path}' does not exist.")
        logger.error(f"Problem: Path '{path}' does not exist.")
        raise typer.Exit(code=1)
        
    # Validate API key
    if not os.getenv("OPENAI_API_KEY"):
        ui.print_error("Configuration Error", "OPENAI_API_KEY not found in environment variables.", "Please create a .env file with your API key.")
        logger.error("Problem: OPENAI_API_KEY missing")
        raise typer.Exit(code=1)

    # Validate model configuration
    if not os.getenv("MODEL_ANALYZER") or not os.getenv("MODEL_GENERATOR"):
        ui.print_error("Configuration Error", "Model configuration missing.", "Please set MODEL_ANALYZER and MODEL_GENERATOR in your .env file.")
        logger.error("Problem: Model configuration missing")
        raise typer.Exit(code=1)

    ui.print_welcome()
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
        "failure_patterns": [],  # AI-detected failure log patterns
        "needs_reanalysis": False  # Flag to trigger re-analysis
    }

    # Create and Run Graph
    workflow = create_graph()
    
    try:
        with ui.get_status_spinner("[bold green]Running DockAI Agent...[/bold green]"):
            final_state = workflow.invoke(initial_state)
    except Exception as e:
        # Handle any unexpected errors gracefully
        error_msg = str(e)
        
        # Check for common LangGraph errors
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

    # Process Results
    validation_result = final_state["validation_result"]
    output_path = os.path.join(path, "Dockerfile")
    
    if validation_result["success"]:
        ui.display_summary(final_state, output_path)
    else:
        ui.display_failure(final_state)
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
