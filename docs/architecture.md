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
3.  **Execution**: The Graph executes nodes, updating the State.
4.  **Loop**: If validation fails, the Reflector updates the State with "lessons learned", and the loop repeats.
5.  **Output**: A validated `Dockerfile` is written to disk (or returned as text).

---

## Next Steps

- **[API Reference](./api-reference.md)**: Detailed code documentation
- **[Customization](./customization.md)**: How to tune the agents
- **[MCP Server](./mcp-server.md)**: Using this architecture with AI agents

