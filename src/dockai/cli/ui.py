"""
DockAI UI Module.

This module handles all user interface interactions using the 'Rich' library.
It separates the display logic from the main application logic, ensuring that
console output is consistent, beautiful, and informative. It handles:
- Logging configuration
- Status spinners
- Success/Error/Warning messages
- Detailed summary and failure reports
"""

import logging
from rich.console import Console
from rich.panel import Panel
from rich.logging import RichHandler

# Initialize the global Rich console instance
console = Console()

def setup_logging(verbose: bool = False):
    """
    Configures the logging system to use RichHandler.
    
    This ensures that log messages are beautifully formatted and integrated
    seamlessly with other console output.
    
    Args:
        verbose (bool): If True, sets the log level to DEBUG. Otherwise, INFO.
        
    Returns:
        logging.Logger: The configured logger instance for the 'dockai' namespace.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=False, show_path=False)]
    )
    return logging.getLogger("dockai")

def print_welcome():
    """Prints the application welcome banner."""
    console.print(Panel.fit("[bold blue]DockAI[/bold blue]\n[italic]The Customizable AI Dockerfile Generation Framework[/italic]"))

def print_error(title: str, message: str, details: str = None):
    """
    Prints a formatted error message.
    
    Args:
        title (str): The title of the error.
        message (str): The main error message.
        details (str, optional): Additional details or context.
    """
    console.print(f"[bold red]Error:[/bold red] {title}")
    console.print(message)
    if details:
        console.print(f"[dim]{details}[/dim]")

def print_success(message: str):
    """
    Prints a formatted success message.
    
    Args:
        message (str): The success message to display.
    """
    console.print(f"\n[bold green]Success![/bold green] {message}")

def print_warning(message: str):
    """
    Prints a formatted warning message.
    
    Args:
        message (str): The warning message to display.
    """
    console.print(f"[yellow]Warning:[/yellow] {message}")

def display_summary(final_state: dict, output_path: str):
    """
    Displays the final summary of a successful execution.
    
    This includes:
    - Success confirmation
    - Output file location
    - Adaptive learning history (retries and lessons learned)
    - Token usage statistics breakdown
    - Strategy details
    
    Args:
        final_state (dict): The final state of the workflow.
        output_path (str): The path where the Dockerfile was saved.
    """
    print_success(f"Dockerfile validated successfully.")
    console.print(f"[bold green]Final Dockerfile saved to {output_path}[/bold green]")
    
    # Show retry history summary if there were retries (Adaptive Learning)
    retry_history = final_state.get("retry_history", [])
    if retry_history:
        console.print(f"\n[cyan]Adaptive Learning: {len(retry_history)} iterations to reach solution[/cyan]")
        for i, attempt in enumerate(retry_history, 1):
            console.print(f"  [dim]Attempt {i}: {attempt.get('lesson_learned', 'N/A')}[/dim]")
    
    # Calculate Costs and Usage
    total_tokens = 0
    usage_by_stage = {}
    
    for stat in final_state.get("usage_stats", []):
        total_tokens += stat["total_tokens"]
        stage = stat['stage']
        if stage not in usage_by_stage:
            usage_by_stage[stage] = 0
        usage_by_stage[stage] += stat["total_tokens"]
    
    usage_details = [f"{stage}: {tokens} tokens" for stage, tokens in usage_by_stage.items()]
    
    # Build summary content
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
        title="Usage Summary",
        border_style="blue"
    ))

def display_failure(final_state: dict):
    """
    Displays detailed information about a failed execution.
    
    This includes:
    - Failure message
    - Classified error details (Problem, Solution)
    - Specific advice based on error type (Project vs Environment vs Dockerfile)
    - Retry history and lessons learned
    - Final reflection/root cause analysis
    - Token usage
    
    Args:
        final_state (dict): The final state of the workflow.
    """
    console.print(f"\n[bold red]Failed to generate a valid Dockerfile[/bold red]\n")
    
    # Display classified error information if available
    error_details = final_state.get("error_details")
    
    if error_details:
        error_type = error_details.get("error_type", "unknown_error")
        
        # Create error type display with icons
        error_type_icons = {
            "project_error": "Project Error",
            "dockerfile_error": "Dockerfile Error", 
            "environment_error": "Environment Error",
            "unknown_error": "Unknown Error",
            "security_review": "Security Error"
        }
        
        error_type_display = error_type_icons.get(error_type, "Error")
        
        # Build error panel
        error_content = f"[bold]{error_type_display}[/bold]\n\n"
        error_content += f"[red]Problem:[/red] {error_details.get('message', 'Unknown error')}\n\n"
        error_content += f"[green]Solution:[/green] {error_details.get('suggestion', 'Check the logs for details')}"
        
        # Add retry info based on error type
        if error_type == "project_error":
            error_content += "\n\n[yellow]This is a project configuration issue that cannot be fixed by retrying.[/yellow]"
            error_content += "\n[yellow]Please fix the issue in your project and try again.[/yellow]"
        elif error_type == "environment_error":
            error_content += "\n\n[yellow]This is a local environment issue.[/yellow]"
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
        console.print(f"\n[cyan]Attempted {retry_count} of {max_retries} retries:[/cyan]")
        for i, attempt in enumerate(retry_history, 1):
            console.print(f"  [dim]Attempt {i}:[/dim]")
            console.print(f"    [dim]• Tried: {attempt.get('what_was_tried', 'N/A')[:60]}...[/dim]")
            console.print(f"    [dim]• Failed: {attempt.get('why_it_failed', 'N/A')[:60]}...[/dim]")
    elif retry_count > 0:
        console.print(f"\n[dim]Attempted {retry_count} of {max_retries} retries before stopping.[/dim]")
    
    # Show reflection insight if available
    reflection = final_state.get("reflection")
    if reflection:
        console.print(f"\n[cyan]Final Analysis:[/cyan]")
        console.print(f"  [dim]Root Cause: {reflection.get('root_cause_analysis', 'N/A')[:100]}...[/dim]")
    
    # Show token usage even on failure
    total_tokens = 0
    for stat in final_state.get("usage_stats", []):
        total_tokens += stat["total_tokens"]
    if total_tokens > 0:
        console.print(f"\n[dim]Tokens used: {total_tokens}[/dim]")

def get_status_spinner(message: str):
    """
    Returns a status spinner context manager.
    
    Args:
        message (str): The message to display next to the spinner.
        
    Returns:
        rich.status.Status: A context manager for the spinner.
    """
    return console.status(message, spinner="dots")
