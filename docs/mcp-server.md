# Model Context Protocol (MCP) Integration

DockAI implements the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/), allowing it to function as a server for AI agents. This enables you to use DockAI's capabilities directly inside tools like **Claude Desktop**, **Cursor**, **Zed**, and other MCP-compliant clients.

---

## 🚀 Getting Started

### Prerequisites

-   Python 3.10+
-   `dockai-cli` installed (`pip install dockai-cli`)
-   An MCP Client (e.g., Claude Desktop)

### Configuration

Add the following configuration to your MCP client's settings file (e.g., `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "dockai": {
      "command": "python",
      "args": ["-m", "dockai.core.mcp_server"]
    }
  }
}
```

> **Note**: Ensure that `dockai-cli` is installed in the python environment you are using, or provide the full path to the python executable.

---

## 🛠️ Available Tools

When running as an MCP server, DockAI exposes the following tools to the AI agent:

### 1. `run_full_workflow`
Executes the complete DockAI agentic workflow, identical to running `dockai build` in the CLI.

-   **Arguments**:
    -   `path` (string): The absolute path to the project directory.
    -   `instructions` (string, optional): Custom instructions for the agents (e.g., "Use Alpine Linux", "Expose port 3000").
-   **Behavior**:
    -   Scans and analyzes the project.
    -   Generates a Dockerfile.
    -   Builds and validates the image.
    -   Self-corrects if validation fails (up to 3 retries).
    -   Returns the final Dockerfile content and validation status.

### 2. `analyze_project`
Performs a standalone analysis of the project structure and requirements.

-   **Arguments**:
    -   `path` (string): The absolute path to the project directory.
-   **Returns**:
    -   Detected tech stack (e.g., Node.js, Python).
    -   Project type (Service vs. Script).
    -   Suggested base image.
    -   Build and start commands.

### 3. `generate_dockerfile_content`
Generates a Dockerfile without building or validating it.

-   **Arguments**:
    -   `path` (string): The absolute path to the project directory.
    -   `instructions` (string, optional): Custom instructions.
-   **Returns**:
    -   The raw content of the generated Dockerfile.

### 4. `validate_dockerfile`
Validates a specific Dockerfile content against a project.

-   **Arguments**:
    -   `path` (string): The build context path.
    -   `dockerfile_content` (string): The content to validate.
-   **Returns**:
    -   Success/Failure status and build logs.

---

## 💡 Example Usage

Once configured, you can talk to your AI agent naturally:

> **User**: "Analyze the project at `/Users/me/my-app` and generate a Dockerfile for it. Make sure to use a multi-stage build."

> **Claude**: *Calls `dockai.run_full_workflow(path="/Users/me/my-app", instructions="Use multi-stage build")`*

> **DockAI**: *Runs the workflow, builds the image, verifies it works, and returns the result.*

> **Claude**: "I've generated and validated a Dockerfile for your app. It uses a multi-stage build as requested. Here is the content..."

---

## 🏗️ Architecture

The MCP Server is implemented in `src/dockai/core/mcp_server.py`. It wraps the core LangGraph workflow and exposes it via the `FastMCP` library.

For more details on the internal architecture, see [Architecture](./architecture.md).
