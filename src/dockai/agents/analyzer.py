"""
DockAI Analyzer Module.

This module is responsible for the initial analysis of the repository.
It acts as the "Brain" of the operation, understanding the project structure,
identifying the technology stack, and determining the requirements.
"""

import os
import json
from typing import Tuple, Any, Dict, List, TYPE_CHECKING

# Third-party imports for LangChain integration
from langchain_core.prompts import ChatPromptTemplate

# Internal imports for data schemas, callbacks, and LLM providers
from ..core.schemas import AnalysisResult
from ..utils.callbacks import TokenUsageCallback
from ..utils.rate_limiter import with_rate_limit_handling
from ..utils.prompts import get_prompt
from ..core.llm_providers import create_llm

# Type checking imports (avoid circular imports)
if TYPE_CHECKING:
    from ..core.agent_context import AgentContext


@with_rate_limit_handling(max_retries=5, base_delay=2.0, max_delay=60.0)
def safe_invoke_chain(chain, input_data: Dict[str, Any], callbacks: list) -> Any:
    """Safely invoke a LangChain chain with rate limit handling."""
    return chain.invoke(input_data, config={"callbacks": callbacks})


def analyze_repo_needs(context: 'AgentContext') -> Tuple[AnalysisResult, Dict[str, int]]:
    """
    Performs the initial analysis of the repository to determine project requirements.

    This function corresponds to "Stage 1: The Brain" of the DockAI process. It uses
    an LLM to analyze the list of files in the repository and deduce the technology
    stack, project type (service vs. script), and necessary build/start commands.

    Args:
        context (AgentContext): Unified context containing file_tree and custom_instructions.

    Returns:
        Tuple[AnalysisResult, Dict[str, int]]: A tuple containing:
            - The structured analysis result (AnalysisResult object).
            - A dictionary tracking token usage for cost monitoring.
    """
    from ..core.agent_context import AgentContext
    # Create LLM using the provider factory for the analyzer agent
    llm = create_llm(agent_name="analyzer", temperature=0)
    
    # Configure the LLM to return a structured output matching the AnalysisResult schema
    structured_llm = llm.with_structured_output(AnalysisResult)
    
    # Default system prompt for the Build Engineer persona
    default_prompt = """You are the ANALYZER agent in a multi-agent Dockerfile generation pipeline. You are AGENT 1 of 10 - your analysis is the foundation that all downstream agents depend on.

## Your Role in the Pipeline
```
[YOU: Analyzer] → Planner → Generator → Reviewer → Validator → (Reflector if failed)
```
Your output directly feeds the Planner and Generator. Poor analysis = poor Dockerfile. Be thorough.

## Your Mission
Analyze this software project from FIRST PRINCIPLES. You have NO assumptions - discover everything from evidence.

## Chain-of-Thought Analysis Process

### PHASE 1: EVIDENCE GATHERING
Systematically examine the file tree:
```
1. Entry points: main.*, index.*, app.*, server.*, cmd/, src/
2. Manifests: package.json, requirements.txt, go.mod, Cargo.toml, pom.xml, build.gradle, Gemfile, composer.json
3. Configs: Dockerfile (existing), docker-compose.*, .env*, config/
4. Build files: Makefile, build.*, setup.py, CMakeLists.txt, webpack.*, vite.*
5. Lock files: package-lock.json, yarn.lock, poetry.lock, Pipfile.lock, go.sum
```

### PHASE 2: TECHNOLOGY DEDUCTION
From the evidence, deduce:
```
A. Primary Language: What extensions dominate? (.py → Python, .js/.ts → Node, .go → Go, etc.)
B. Framework Signals: 
   - next.config.* → Next.js
   - manage.py → Django
   - main.go + go.mod → Go service
   - Cargo.toml → Rust
   - pom.xml/build.gradle → Java/Kotlin
C. Runtime Type:
   - Compiled (Go, Rust, C++) vs Interpreted (Python, Node, Ruby)
   - Static binary vs dynamic linking
   - JIT compiled (Java, .NET)
```

### PHASE 3: BUILD REQUIREMENTS
Determine what's needed to BUILD:
```
1. Compiler/Interpreter version requirements
2. Build tools (npm, pip, cargo, go, maven, gradle)
3. Native dependencies (gcc, make, libssl-dev, etc.)
4. Build commands: npm run build, pip install, go build, cargo build
5. Build artifacts: dist/, build/, target/, bin/
```

### PHASE 4: RUNTIME REQUIREMENTS
Determine what's needed to RUN:
```
1. Runtime only (node, python) vs compiled binary
2. Runtime dependencies vs build-only dependencies
3. Environment variables expected
4. Ports typically used (3000 Node, 8000 Django, 8080 Go, etc.)
5. File paths the app expects (/app, static files, templates)
```

### PHASE 5: EXECUTION PATTERN
Classify the application:
```
SERVICE: Long-running process (web server, API, worker)
  - Needs health checks, graceful shutdown
  - Runs indefinitely, binds to port
  
SCRIPT: One-time execution (CLI tool, batch job, migration)
  - Runs to completion, exits
  - No health checks needed
  
HYBRID: Service with CLI commands (Django manage.py, etc.)
```

## Critical Outputs for Downstream Agents

Your analysis MUST provide clear answers for:
1. **stack**: Technology identification (e.g., "Node.js 20 with Next.js 14")
2. **project_type**: "service" or "script"
3. **build_command**: Exact command to build (e.g., "npm ci && npm run build")
4. **start_command**: Exact command to run (e.g., "node server.js")
5. **suggested_base_image**: Recommended base (e.g., "node:20-alpine")
6. **critical_files**: Files the Generator MUST copy

## Anti-Patterns to Avoid
- DON'T guess without evidence
- DON'T assume standard ports without checking config
- DON'T overlook lock files (they indicate package manager)
- DON'T ignore existing Dockerfile hints
- DON'T miss monorepo structures (workspaces, packages/)

{custom_instructions}
"""

    # Get custom prompt if configured, otherwise use default
    system_prompt = get_prompt("analyzer", default_prompt)

    # Create the chat prompt template
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", """Here is the file list: {file_list}

Analyze the project and provide a detailed thought process explaining your reasoning.""")
    ])
    
    # Create the execution chain: Prompt -> LLM -> Structured Output
    chain = prompt | structured_llm
    
    # Initialize callback to track token usage
    callback = TokenUsageCallback()
    
    # Convert file list to JSON string for better formatting in the prompt
    file_list_str = json.dumps(context.file_tree)
    
    # Execute the chain (with rate limit handling)
    result = safe_invoke_chain(
        chain,
        {
            "custom_instructions": context.custom_instructions, 
            "file_list": file_list_str
        },
        [callback]
    )
    
    return result, callback.get_usage()

