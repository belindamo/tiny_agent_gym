# tiny-agent-gym

A lightweight, local-first agent execution framework that runs AI agents in isolated folder environments without Docker containers.

## Features

- **Local execution** - No cloud required, runs directly in folders
- **Simple task configuration** - Define tasks with success criteria via CLI
- **Automatic organization** - Tasks, environments, and runs in separate folders
- **Fast iteration** - No Docker container overhead means rapid testing
- **Built-in LLM judge** - Automatically evaluates task success using task description, success criteria, and trajectory logs

## Installation

Make sure you have a `.env` file in the root directory with whichever model api key you'd like to use:
```
GOOGLE_API_KEY=your_google_api_key
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
```

```bash
git clone https://github.com/belindamo/tiny-agent-gym
cd tiny-agent-gym
uv pip install -e .
```

## Quick Start

```bash
# Run a simple task
tag "Write a hello world Python script"

# Run with success criteria
tag "Create a web scraper" --success "Script successfully fetches data from example.com"

# Run an existing task from a JSON file in `tasks/`
tag --task example 

# Run in existing environment in `envs/`. (It will copy the environment to a new folder and run the agent in it.)
tag "Pass the tests" --env example

# Use a different agent
tag "Initialize a github repository for a uv package" --agent react_with_mcp
```

## How It Works

### Task Creation
When you run `tag "Your task description"`, the system:
1. Generates a task ID from your description (e.g., "write_a_hello")
2. Creates a task file: `tasks/task_XXX_write_a_hello.json`
3. Creates an empty environment directory: `envs/YY_task_XXX_write_a_hello_timestamp/`
4. Executes the agent in this clean environment

### Folder Structure
```
tiny-agent-gym/
├── tasks/              # Task definitions (JSON files)
├── envs/               # Working environments
├── runs/               # Execution logs and results
├── agents/             # Available agents
│   ├── react/          # Default ReAct agent
│   └── react_with_mcp/ # ReAct with MCP tools
└── evals/              # Custom evaluation scripts
└── main.py             # Main execution script
```

## Examples in detail

### Example 1: Make a Basic Task
```bash
tag "Create a README file with project description"
```
This creates:
- `tasks/task_001_create_a_readme.json` - Task configuration
- `envs/17_task_001_create_a_readme_[timestamp]/` - Empty working directory
- `runs/17_task_001_create_a_readme_[timestamp]/` - Execution logs and results

The built-in LLM judge will evaluate success based on whether a README was created with meaningful content.

### Example 2: Make a Task with Success Criteria
```bash
tag "Build a calculator" --success "Function correctly calculates fibonacci(10) = 55"
```
The agent will work until the success criteria is met. The LLM judge evaluates the trajectory against your specific criteria.

### Example 3: Make a Task with Custom Evaluation
```bash
tag "Implement sorting algorithm" \
  --success "Correctly sorts [3,1,4,1,5,9]" \
  --eval ./test_sorting.py
```
Your eval script is copied to `evals/[task_id]/eval.py` and run after task completion.

### Example 4: Use an Existing Environment for a Task
```bash
tag "Fix the tests" --env example
```
The agent starts with a copy of the `envs/example/` directory instead of an empty folder.

## Direct Execution (Advanced)

For batch processing or programmatic use:
```bash
# Run with existing task file
uv run main.py --agent react --tasks example

# The task file path can be specified without .json extension
uv run main.py --agent react --tasks task_001_write_a_hello
```

## Task File Structure

Tasks are stored as JSON arrays with this structure:
```json
[
  {
    "task_id": "write_a_hello",
    "task": "Write a hello world Python script",
    "success_criteria": "Task completed successfully",
    "dir_name": null  // null = empty env, or specify existing env name
  }
]
```

## Automatic Evaluation

The built-in LLM-as-a-judge system:
- Reads the task description and success criteria
- Analyzes the complete trajectory logs
- Evaluates whether the task was completed successfully
- Provides detailed feedback on what was/wasn't achieved
- Works independently of custom eval scripts (but can be used alongside)

## License

The MIT License.
