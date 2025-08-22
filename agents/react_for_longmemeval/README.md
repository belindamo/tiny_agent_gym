# ReAct with MCP Agent

An enhanced ReAct agent that leverages the Model Context Protocol (MCP) to provide advanced filesystem and memory capabilities through external MCP servers.

## Key Differences from Basic ReAct

| Feature | Basic ReAct | ReAct with MCP |
|---------|-------------|----------------|
| **File Operations** | Custom implementations | MCP filesystem server |
| **Memory** | No persistent memory | MCP memory server |
| **Execution** | Synchronous | Asynchronous |
| **Tool Integration** | Manual tool wrapping | Automatic MCP tool discovery |
| **Extensibility** | Limited to hardcoded tools | Easy MCP server addition |

## Features

- **MCP Filesystem Server**: Professional-grade file operations
- **MCP Memory Server**: Persistent memory across tasks  
- **Async Execution**: Non-blocking performance
- **Automatic Tool Discovery**: Dynamically loads tools from MCP servers
- **Terminal Commands**: Execute shell commands within the environment

## Usage

```python
from agents.react_with_mcp.main import main
from helpers.models import Run, Task

# Create a task
task = Task(task="Analyze the codebase and remember key insights")
run = Run(task=task, dir_name="/path/to/environment")

# Execute the agent (async)
result = await main(run)
print(result.result)
```

## Configuration

**Environment Variables:**
- `GOOGLE_API_KEY`: Required for Gemini API access

**Dependencies:**
- Node.js/NPX: For running MCP servers
- `mcp`: Model Context Protocol client library

**MCP Servers Used:**
- `@modelcontextprotocol/server-filesystem`: File operations
- `@modelcontextprotocol/server-memory`: Persistent memory

## When to Use

**Use ReAct with MCP for:**
- Complex file operations requiring reliability
- Multi-session tasks needing persistent memory
- Extensible systems that will add more capabilities

**Use Basic ReAct for:**
- Simple file tasks with basic operations
- Single-session work without memory needs
