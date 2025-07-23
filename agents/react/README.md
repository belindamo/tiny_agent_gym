# ReAct Agent

A ReAct (Reasoning and Acting) agent built with DSPy that can solve tasks by iteratively reasoning about problems and taking actions to solve them. This agent operates within a folder environment and provides file manipulation and terminal execution capabilities.

## Overview

The ReAct agent uses a think-then-act approach where it iteratively reasons about the current situation and takes actions to make progress toward completing the task.

## Available Actions

| Action | Description | Parameters |
|--------|-------------|------------|
| `create_file` | Create a new file with optional content | `filepath`, `content` |
| `delete_file` | Delete an existing file | `filepath` |
| `edit_file` | AI-powered file editing based on query | `filepath`, `query` |
| `read_file` | Read contents of one or more files | `filepath` (string or list) |
| `execute_terminal_command` | Run terminal commands | `command` |

## Usage

```python
from agents.react.main import main
from helpers.models import Run, Task

# Create a task
task = Task(task="Create a Python script that prints 'Hello World'")
run = Run(task=task, dir_name="/path/to/environment")

# Execute the agent
result = main(run)
print(result.result)
```

## Configuration

**Environment Variables:**
- `GOOGLE_API_KEY`: Required for Gemini API access

**Key Features:**
- Framework: DSPy for structured reasoning and tool integration
- Security: Path restriction and command validation
- Iteration Control: Configurable maximum iterations
