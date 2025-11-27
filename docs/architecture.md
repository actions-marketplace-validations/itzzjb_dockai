# 🏗️ Architecture

DockAI is built on a modular, agentic architecture powered by **LangGraph**. This design allows it to be flexible, robust, and easily extensible.

## Core Components

### 1. The Graph (State Machine)
The heart of DockAI is a state machine defined in `src/dockai/workflow/graph.py`. It orchestrates the flow of data between different agents and nodes.

**Workflow:**
`Scan` → `Analyze` → `Plan` → `Generate` → `Validate` ⇄ `Reflect`

### 2. The Agents
DockAI uses specialized AI agents for different tasks:
-   **Analyzer**: Scans the file tree to understand the tech stack.
-   **Planner**: Formulates a build strategy (e.g., multi-stage builds).
-   **Generator**: Writes the actual Dockerfile code.
-   **Reviewer**: Checks for security vulnerabilities.
-   **Reflector**: Analyzes failures and suggests fixes.

### 3. Interfaces
DockAI exposes its core logic through three main interfaces:
-   **CLI (`dockai.cli`)**: For local usage.
-   **GitHub Action**: For CI/CD automation.
-   **MCP Server (`dockai.core.mcp_server`)**: For integration with AI agents (Claude, Cursor).

## Directory Structure

```
src/dockai/
├── agents/         # AI Agent logic (Analyzer, Generator, etc.)
├── cli/            # Command-line interface (Typer)
├── core/           # Core logic (State, Config, MCP Server)
├── utils/          # Helpers (File I/O, Docker wrapper, Registry Integration)
└── workflow/       # LangGraph nodes and graph definition
```

## Data Flow

1.  **Input**: User provides a path (CLI/MCP) or repo (Action).
2.  **State**: A `DockAIState` object is created to hold all context.
3.  **AgentContext**: Each agent receives a unified `AgentContext` object containing all relevant information (file tree, analysis results, error history, etc.).
4.  **Execution**: The Graph executes nodes, updating the State.
5.  **Loop**: If validation fails, the Reflector updates the State with "lessons learned", and the loop repeats.
6.  **Output**: A validated `Dockerfile` is written to disk (or returned as text).

### AgentContext

All 10 AI agents share context through the `AgentContext` dataclass (`src/dockai/core/agent_context.py`):

```python
@dataclass
class AgentContext:
    file_tree: List[str]           # Project file list
    file_contents: str             # Critical file contents
    analysis_result: Dict          # Stack detection results
    current_plan: Dict             # Build strategy
    retry_history: List[Dict]      # Previous attempts & lessons
    dockerfile_content: str        # Current Dockerfile
    reflection: Dict               # Failure analysis
    error_message: str             # Last error
    custom_instructions: str       # User guidance
    verified_tags: str             # Valid Docker image tags
```

This unified context ensures all agents have access to the full picture, enabling better decision-making and learning from failures.

---

## Next Steps

- **[API Reference](./api-reference.md)**: Detailed code documentation
- **[Customization](./customization.md)**: How to tune the agents
- **[MCP Server](./mcp-server.md)**: Using this architecture with AI agents

