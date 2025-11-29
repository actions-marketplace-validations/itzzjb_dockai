# MCP Server Integration

DockAI includes a Model Context Protocol (MCP) server that exposes Dockerfile generation as a tool for AI assistants like Claude Desktop, Cursor, and other MCP-compatible clients. This enables conversational Dockerfile generation directly within your development environment.

---

## 📋 Table of Contents

1. [What is MCP?](#what-is-mcp)
2. [Why Use DockAI as an MCP Server?](#why-use-dockai-as-an-mcp-server)
3. [Quick Start](#quick-start)
4. [Installation Methods](#installation-methods)
5. [Configuration](#configuration)
6. [Using with Claude Desktop](#using-with-claude-desktop)
7. [Using with Cursor](#using-with-cursor)
8. [Available Tools](#available-tools)
9. [Example Conversations](#example-conversations)
10. [Advanced Configuration](#advanced-configuration)
11. [Troubleshooting](#troubleshooting)

---

## What is MCP?

The **Model Context Protocol (MCP)** is an open standard developed by Anthropic that allows AI assistants to interact with external tools and data sources. Think of it as a plugin system for AI:

```mermaid
flowchart LR
    subgraph Client["AI Assistant"]
        claude["Claude Desktop\nCursor\nOther MCP Clients"]
    end
    
    subgraph Server["MCP Server"]
        mcp["JSON-RPC\nover STDIO"]
    end
    
    subgraph Engine["DockAI Engine"]
        workflow["LangGraph\nWorkflow"]
    end
    
    claude <-->|"MCP Protocol"| mcp
    mcp <-->|"Python API"| workflow
```

### Key Benefits

| Benefit | Description |
|---------|-------------|
| **Natural Language** | Ask for Dockerfiles in plain English |
| **Context Aware** | AI understands your project context |
| **Iterative** | Refine through conversation |
| **Integrated** | Works in your existing AI workflow |

---

## Why Use DockAI as an MCP Server?

### Comparison of Interfaces

| Interface | Best For | Interaction |
|-----------|----------|-------------|
| CLI | Automation, scripts, CI/CD | Command-line |
| GitHub Action | Automated pipelines | Configuration YAML |
| **MCP Server** | Development, exploration | Natural language |

### MCP Server Advantages

1. **Conversational**: "Generate a Dockerfile for this Python project"
2. **Contextual**: "Now make it use a smaller base image"
3. **Educational**: "Why did you choose Alpine?"
4. **Exploratory**: "What would happen if I used multi-stage builds?"

### When to Use MCP vs CLI

| Use MCP When | Use CLI When |
|--------------|--------------|
| Exploring options | Automating builds |
| Learning Dockerfile best practices | Running in CI/CD |
| Iterating on configuration | Batch processing |
| Integrating with AI workflow | Scripting |

---

## Quick Start

### 1. Install DockAI

```bash
pip install dockai-cli
```

### 2. Set API Key

```bash
export OPENAI_API_KEY=sk-your-key
```

### 3. Test MCP Server

```bash
# Run the MCP server directly
python -m dockai.core.mcp_server
```

### 4. Configure Your AI Client

See specific instructions for:
- [Claude Desktop](#using-with-claude-desktop)
- [Cursor](#using-with-cursor)

---

## Installation Methods

### Using pip (Recommended)

```bash
pip install dockai-cli

# Verify installation
dockai --version
python -c "from dockai.core.mcp_server import mcp; print('MCP Server available')"
```

### Using pipx (Isolated Environment)

```bash
pipx install dockai-cli

# Verify
pipx run dockai --version
```

### Using Docker

```bash
docker pull ghcr.io/itzzjb/dockai:latest

# Run MCP server in Docker (requires volume mount for project access)
docker run -it --rm \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -v /path/to/your/projects:/projects \
  ghcr.io/itzzjb/dockai:latest \
  python -m dockai.core.mcp_server
```

### From Source

```bash
git clone https://github.com/itzzjb/dockai.git
cd dockai
pip install -e .
```

---

## Configuration

### Environment Variables

Set these before starting the MCP server (via the `env` section in your MCP client config):

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | If using OpenAI | OpenAI API key |
| `AZURE_OPENAI_API_KEY` | If using Azure | Azure OpenAI key |
| `AZURE_OPENAI_ENDPOINT` | If using Azure | Azure endpoint |
| `GOOGLE_API_KEY` | If using Gemini | Google AI key |
| `ANTHROPIC_API_KEY` | If using Anthropic | Anthropic key |
| `DOCKAI_LLM_PROVIDER` | No | Default: `openai` |
| `MAX_RETRIES` | No | Default: `3` |
| `DOCKAI_ENABLE_TRACING` | No | Enable OpenTelemetry |

### Running the MCP Server

The MCP server is run as a Python module:

```bash
python -m dockai.core.mcp_server
```

This starts the server using stdio transport, which is what MCP clients like Claude Desktop expect.

---

## Using with Claude Desktop

Claude Desktop supports MCP servers through its configuration file.

### Step 1: Locate Configuration File

| Platform | Path |
|----------|------|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/claude/claude_desktop_config.json` |

### Step 2: Configure DockAI

Edit or create the configuration file:

```json
{
  "mcpServers": {
    "dockai": {
      "command": "python",
      "args": ["-m", "dockai.core.mcp_server"],
      "env": {
        "OPENAI_API_KEY": "sk-your-api-key-here"
      }
    }
  }
}
```

### Step 3: With Full Python Path (If Needed)

If the `python` command doesn't find dockai:

```json
{
  "mcpServers": {
    "dockai": {
      "command": "/usr/local/bin/python3",
      "args": ["-m", "dockai.core.mcp_server"],
      "env": {
        "OPENAI_API_KEY": "sk-your-api-key-here"
      }
    }
  }
}
```

Find your Python path:
```bash
which python3  # macOS/Linux
where python   # Windows
```

### Step 4: With Different Providers

**Google Gemini**:
```json
{
  "mcpServers": {
    "dockai": {
      "command": "python",
      "args": ["-m", "dockai.core.mcp_server"],
      "env": {
        "DOCKAI_LLM_PROVIDER": "gemini",
        "GOOGLE_API_KEY": "your-google-api-key"
      }
    }
  }
}
```

**Azure OpenAI**:
```json
{
  "mcpServers": {
    "dockai": {
      "command": "python",
      "args": ["-m", "dockai.core.mcp_server"],
      "env": {
        "DOCKAI_LLM_PROVIDER": "azure",
        "AZURE_OPENAI_API_KEY": "your-key",
        "AZURE_OPENAI_ENDPOINT": "https://your-resource.openai.azure.com/"
      }
    }
  }
}
```

**Ollama (Local)**:
```json
{
  "mcpServers": {
    "dockai": {
      "command": "python",
      "args": ["-m", "dockai.core.mcp_server"],
      "env": {
        "DOCKAI_LLM_PROVIDER": "ollama"
      }
    }
  }
}
```

### Step 5: Restart Claude Desktop

After saving the configuration, restart Claude Desktop completely:

1. Quit Claude Desktop (not just close window)
2. Start Claude Desktop again
3. Look for the 🔧 tools icon indicating MCP servers are connected

### Step 6: Verify Connection

Ask Claude:
> "What tools do you have available?"

Claude should mention the DockAI tools: `analyze_project`, `generate_dockerfile_content`, `validate_dockerfile`, and `run_full_workflow`.

---

## Using with Cursor

Cursor IDE also supports MCP servers for AI-assisted development.

### Configuration Location

| Platform | Path |
|----------|------|
| macOS | `~/.cursor/config/mcp.json` |
| Windows | `%USERPROFILE%\.cursor\config\mcp.json` |
| Linux | `~/.cursor/config/mcp.json` |

### Configuration Example

```json
{
  "mcpServers": {
    "dockai": {
      "command": "python",
      "args": ["-m", "dockai.core.mcp_server"],
      "env": {
        "OPENAI_API_KEY": "sk-your-api-key"
      }
    }
  }
}
```

### Per-Project Configuration

Create `.cursor/mcp.json` in your project:

```json
{
  "mcpServers": {
    "dockai": {
      "command": "python",
      "args": ["-m", "dockai.core.mcp_server"],
      "env": {
        "DOCKAI_LLM_PROVIDER": "gemini",
        "GOOGLE_API_KEY": "${env:GOOGLE_API_KEY}"
      }
    }
  }
}
```

The `${env:VARIABLE}` syntax references environment variables.

---

## Available Tools

DockAI's MCP server exposes four tools (defined in `src/dockai/core/mcp_server.py`):

### 1. `analyze_project`

Analyzes a project directory to determine Docker requirements without generating a Dockerfile.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | Yes | Absolute path to project directory |

**Returns**: A summary of detected stack, build commands, and critical files.

### 2. `generate_dockerfile_content`

Generates a Dockerfile for the project. Returns content only, does NOT write to disk.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | Yes | Absolute path to project directory |
| `instructions` | string | No | Custom instructions (e.g., "Use Alpine") |

**Returns**: The generated Dockerfile content.

### 3. `validate_dockerfile`

Validates a Dockerfile by building and running it.

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | Yes | Absolute path to project directory (build context) |
| `dockerfile_content` | string | Yes | The Dockerfile content to test |

**Returns**: Validation result (success/failure with message).

### 4. `run_full_workflow`

Executes the complete DockAI agentic workflow (same as `dockai build` CLI command).

**Parameters**:

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | string | Yes | Absolute path to project directory |
| `instructions` | string | No | Custom instructions for agents |

**Returns**: Summary including final Dockerfile content and validation status.

### Tool Schema Example

```json
{
  "name": "run_full_workflow",
  "description": "Executes the full DockAI agentic workflow (Scan -> Analyze -> Plan -> Generate -> Validate -> Fix)",
  "inputSchema": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Absolute path to the project directory"
      },
      "instructions": {
        "type": "string",
        "description": "Optional custom instructions for the agents"
      }
    },
    "required": ["path"]
  }
}
```

---

## Example Conversations

### Basic Project Analysis

**You**: Analyze my project at /Users/me/projects/myapp

**Claude**: I'll analyze your project to understand its Docker requirements...

*[Claude calls analyze_project tool]*

Here's what I found:
- **Stack**: Python 3.11 with FastAPI
- **Project Type**: service
- **Build Command**: pip install -r requirements.txt
- **Start Command**: uvicorn main:app --host 0.0.0.0
- **Suggested Base Image**: python:3.11-slim
- **Critical Files**: requirements.txt, main.py

Would you like me to generate a Dockerfile based on this analysis?

---

### Generate Dockerfile

**You**: Generate a Dockerfile for /Users/me/projects/myapp. Use Alpine as the base image.

**Claude**: I'll generate a Dockerfile with Alpine as the base image...

*[Claude calls generate_dockerfile_content tool with instructions parameter]*

Here's the generated Dockerfile:

```dockerfile
FROM python:3.11-alpine
# ... generated content
```

This Dockerfile uses Alpine for a minimal footprint. Would you like me to validate it?

---

### Full Workflow with Validation

**You**: Run the full DockAI workflow for /Users/me/projects/myapp

**Claude**: I'll run the complete DockAI workflow which includes analysis, generation, and validation...

*[Claude calls run_full_workflow tool]*

Workflow completed in 1 attempt.
Status: SUCCESS
Validation Message: Image built and tested successfully.

Here's the final Dockerfile:
```dockerfile
FROM python:3.11-slim AS builder
# ...
```

---

### Validate Existing Dockerfile

**You**: Can you validate this Dockerfile for my project at /Users/me/projects/myapp?

```dockerfile
FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "main.py"]
```

**Claude**: I'll validate this Dockerfile by building and running it...

*[Claude calls validate_dockerfile tool]*

Validation Result: Success! The image builds and runs correctly.

---

### Iterative Refinement

**You**: That's good, but can you make the image smaller?

**Claude**: I can generate an optimized version with a smaller footprint:

1. Using multi-stage builds
2. Using a slim or Alpine base image
3. Removing build dependencies from the final image

Would you like me to regenerate with these optimizations?

**You**: Yes, please regenerate.

*[Claude calls generate_dockerfile_content with updated instructions]*

---

### Learning/Exploration

**You**: Why did the Dockerfile use multi-stage builds?

**Claude**: Multi-stage builds offer several advantages for your Python application:

1. **Smaller image size**: Build tools and dev dependencies stay in the builder stage
2. **Security**: Final image only contains runtime necessities
3. **Faster deployments**: Smaller images transfer faster

In your case, the builder stage:
- Installs build dependencies (gcc, etc.)
- Compiles Python packages with C extensions

The runtime stage:
- Copies only the compiled packages
- Uses a minimal base image

---

## Advanced Configuration

### Multiple Project Profiles

Configure different DockAI instances for different project types:

```json
{
  "mcpServers": {
    "dockai-nodejs": {
      "command": "python",
      "args": ["-m", "dockai.core.mcp_server"],
      "env": {
        "OPENAI_API_KEY": "sk-your-key",
        "DOCKAI_GENERATOR_INSTRUCTIONS": "Optimize for Node.js projects. Use Alpine base images."
      }
    },
    "dockai-python": {
      "command": "python",
      "args": ["-m", "dockai.core.mcp_server"],
      "env": {
        "OPENAI_API_KEY": "sk-your-key",
        "DOCKAI_GENERATOR_INSTRUCTIONS": "Optimize for Python projects. Use slim base images."
      }
    }
  }
}
```

### With Docker (No Local Installation)

Run DockAI MCP server in Docker:

```json
{
  "mcpServers": {
    "dockai": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "OPENAI_API_KEY",
        "-v", "/Users/me/projects:/projects:ro",
        "ghcr.io/itzzjb/dockai:latest",
        "python", "-m", "dockai.core.mcp_server"
      ],
      "env": {
        "OPENAI_API_KEY": "sk-your-key"
      }
    }
  }
}
```

**Important**: Mount your project directories as volumes for DockAI to access them.

### With Custom Models

```json
{
  "mcpServers": {
    "dockai": {
      "command": "python",
      "args": ["-m", "dockai.core.mcp_server"],
      "env": {
        "OPENAI_API_KEY": "sk-your-key",
        "DOCKAI_MODEL_ANALYZER": "gpt-4o-mini",
        "DOCKAI_MODEL_GENERATOR": "gpt-4o"
      }
    }
  }
}
```

### With Tracing

Enable OpenTelemetry tracing for debugging:

```json
{
  "mcpServers": {
    "dockai": {
      "command": "python",
      "args": ["-m", "dockai.core.mcp_server"],
      "env": {
        "OPENAI_API_KEY": "sk-your-key",
        "DOCKAI_ENABLE_TRACING": "true",
        "DOCKAI_TRACING_EXPORTER": "console"
      }
    }
  }
}
```

---

## Troubleshooting

### "MCP Server Not Appearing"

**Symptoms**: No tools icon or DockAI tools not available

**Solutions**:

1. **Check Python path**:
   ```bash
   which python3
   python3 -c "from dockai.core.mcp_server import mcp; print('OK')"
   ```
   Use full Python path in configuration if needed.

2. **Verify installation**:
   ```bash
   dockai --version
   python3 -m dockai.core.mcp_server  # Should wait for input
   ```

3. **Test manually**:
   ```bash
   echo '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}' | python -m dockai.core.mcp_server
   ```
   Should return JSON-RPC response.

4. **Check logs** (Claude Desktop):
   - macOS: `~/Library/Logs/Claude/`
   - Windows: `%LOCALAPPDATA%\Claude\logs\`

5. **Restart completely**: Quit and restart Claude Desktop.

### "API Key Not Found"

**Solutions**:

1. **Check environment variable** in config:
   ```json
   "env": {
     "OPENAI_API_KEY": "sk-your-actual-key"
   }
   ```

2. **Don't use shell expansion**: MCP config doesn't expand `$VARIABLES`.

3. **Test API key**:
   ```bash
   export OPENAI_API_KEY=sk-your-key
   dockai build /path/to/project
   ```

### "Permission Denied on Project Path"

**Symptoms**: DockAI can't read project files

**Solutions**:

1. **Use absolute paths**: `/Users/me/projects/myapp`, not `~/projects/myapp`

2. **Check permissions**:
   ```bash
   ls -la /path/to/project
   ```

3. **For Docker-based MCP**: Mount volumes correctly:
   ```json
   "-v", "/Users/me/projects:/projects:ro"
   ```

### "Timeout or Slow Responses"

**Causes**: Large projects, slow network, rate limiting

**Solutions**:

1. **Increase timeout** in AI client settings (if available)

2. **Use faster models**:
   ```json
   "env": {
     "DOCKAI_MODEL_ANALYZER": "gpt-4o-mini"
   }
   ```

3. **Skip validation for exploration**:
   Use `generate_dockerfile_content` instead of `run_full_workflow` for faster iteration without validation.

### "JSON Parse Error"

**Symptoms**: Error parsing MCP response

**Solutions**:

1. **Update DockAI**:
   ```bash
   pip install --upgrade dockai-cli
   ```

2. **Check for print statements**: Custom prompts shouldn't print to stdout.

3. **Verify JSON syntax** in configuration file.

### Debugging Checklist

1. ✅ DockAI installed and `dockai --version` works
2. ✅ API key is set and valid
3. ✅ Configuration file syntax is correct JSON
4. ✅ Command path is correct (use `which dockai`)
5. ✅ Claude Desktop/Cursor fully restarted
6. ✅ Project path is absolute and accessible
7. ✅ No firewall blocking DockAI network requests

---

## Security Considerations

### API Key Management

| Practice | Description |
|----------|-------------|
| **Never commit** | Don't put API keys in version control |
| **Use environment variables** | Reference from secure storage |
| **Rotate regularly** | Change keys periodically |
| **Monitor usage** | Watch for unexpected API calls |

### Project Access

The MCP server can only access paths you explicitly request. However:

1. **Review generated Dockerfiles** before using
2. **Use read-only mounts** for Docker-based MCP
3. **Limit project scope** when possible

---

## Next Steps

- **[Getting Started](./getting-started.md)**: CLI usage basics
- **[Configuration](./configuration.md)**: All configuration options
- **[Customization](./customization.md)**: Fine-tune generation
- **[FAQ](./faq.md)**: Common questions
