# tiny-agent-gym

A lightweight, local-first agent execution framework that runs AI agents in isolated folder environments without Docker containers.

## Features

- **Fast, local execution** - No Docker required, runs directly in folders
- **Simple task configuration** - Define tasks with success criteria via CLI
- **Automatic organization** - Tasks, environments, and runs in separate folders
- **Fast iteration** - No container overhead means rapid testing
- **Built-in LLM judge** - Automatically evaluates task success using task description, success criteria, and trajectory logs

## Installation

```bash
git clone https://github.com/belindamo/tiny-agent-gym
cd tiny-agent-gym
pip install -e .
```

## Quick Start

```bash
# Run a simple task
tiny-agent "Write a hello world Python script"

# Run with success criteria
tiny-agent "Create a web scraper" --success "Script successfully fetches data from example.com"

# Run with custom evaluation
tiny-agent "Build a calculator" --success "All tests pass" --eval ./eval_calculator.py

# Run in existing environment
tiny-agent "Improve the code" --env ./my-project
```

## Examples

### Example 1: Basic Task
```bash
tiny-agent "Create a README file with project description"
```
This creates:
- `tasks/task_001/task.json` - Task configuration
- `environments/env_001/` - Empty working directory
- `runs/run_001/` - Execution logs and results

The built-in LLM judge will evaluate success based on whether a README was created with meaningful content.

### Example 2: Task with Success Criteria
```bash
tiny-agent "Build a todo list CLI" --success "Can add, remove, and list todos"
```
The agent will work until the success criteria is met. The LLM judge evaluates the trajectory against your specific criteria.

### Example 3: Task with Custom Evaluation
```bash
tiny-agent "Implement sorting algorithm" \
  --success "Correctly sorts all test cases" \
  --eval ./test_sorting.py
```
Your eval script receives the environment path and returns success/failure. The LLM judge can also provide additional assessment.

### Example 4: Using Existing Environment
```bash
tiny-agent "Refactor and add tests" \
  --success "All tests pass with >80% coverage" \
  --env ./my-app
```
The agent operates within your existing project folder.

## Automatic Evaluation

The built-in LLM-as-a-judge system:
- Reads the task description and success criteria
- Analyzes the complete trajectory logs
- Evaluates whether the task was completed successfully
- Provides detailed feedback on what was/wasn't achieved
- Works independently of custom eval scripts (but can be used alongside)

## License

The MIT License.
