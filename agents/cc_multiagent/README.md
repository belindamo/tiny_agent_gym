# Claude Code Multi-Agent System

This is a multi-agent system using Claude Code with one actor and multiple critic agents. The actor must pass all critics before the task is considered complete.

## Architecture Overview

The system implements a rigorous development workflow where:
1. **Actor Agent** implements the research proposal
2. **Multiple Critic Agents** evaluate different aspects of the implementation
3. The actor iterates based on critic feedback until all critics pass

## Agent Roles

### Actor Agent (Graduate Student)
- **Role**: Implements experiments and research tasks
- **Capabilities**: Read/write files, use git, run experiments, web search
- **Prompt**: Uses `prompt_for_actor()` from `run_prompts.py`
- **Focus**: Systematic implementation, testing, and documentation
- **Working Directory**: Works in `code/` subdirectory when in experiment structure

### Critic Agents

#### 1. Code Compilation Critic (Non-AI)
- **Role**: Checks if all Python code compiles without syntax errors
- **Method**: Uses Python's built-in `compile()` function
- **Scope**: All `.py` files in the code directory
- **Pass Criteria**: Zero compilation errors

#### 2. Test Runner Critic (Non-AI)
- **Role**: Runs all test files and verifies they pass
- **Method**: Executes pytest on all `test_*.py` files
- **Scope**: All test files in the code directory
- **Pass Criteria**: All tests pass with no failures

#### 3. Implementation Completeness Critic (AI-powered)
- **Role**: Verifies implementation covers all aspects of the proposal
- **Prompt**: Uses `prompt_for_implementation_critic()`
- **Checks**: Missing features, incomplete functionality, proper structure
- **Pass Criteria**: All proposal requirements are implemented

#### 4. Experiment Parameters Critic (AI-powered)
- **Role**: Validates experiment configuration and parameters
- **Prompt**: Uses `prompt_for_experiment_params_critic()`
- **Checks**: Parameter definitions, environment variables, config files
- **Pass Criteria**: Proper configuration aligned with proposal

#### 5. Metrics & Logging Critic (AI-powered)
- **Role**: Ensures proper metric tracking and logging
- **Prompt**: Uses `prompt_for_metrics_critic()`
- **Checks**: Metric collection, logging, result serialization, reproducibility
- **Pass Criteria**: Comprehensive logging and metrics implementation

## Execution Flow

```python
# Main function for multi-agent system
async def run_multi_agent_system(
    env: str,                    # Working directory
    proposal: str,               # Research proposal (or empty to read from plan.md)
    max_actor_runs: int = 8      # Maximum total actor sessions
)
```

### Queue with Final Verification
```
1. Pre-actor baseline check (establish what's missing)
2. Initial actor implementation
3. Create a queue of all critics
4. While (queue not empty OR final_check not done AND actor runs remaining):
   - Pop first critic from queue
   - If critic passes: Mark as passed, continue
   - If critic fails:
     - Run targeted fix (unless in final check mode)
     - Add critic back to FRONT of queue (priority re-check)
     - Reset final_check flag if we were in final check
   - When queue is empty and final_check=False:
     - Add ALL critics back to queue for comprehensive verification
     - Set final_check=True (no more fixes, just verification)
5. Final evaluation shows complete results
6. Done when all critics pass in final check or max runs reached
```

This queue-based approach provides:
- Immediate re-evaluation after fixes
- Priority handling of recently fixed critics
- No wasted evaluations on already-passed critics
- **Guaranteed final verification** of ALL critics after fixes
- Complete conversation history tracking
- Simple, efficient processing order

## Integration with Experiment Structure

When used in a research environment (e.g., `derp/`):
- Automatically detects experiment directories
- Reads proposal from `experiments/<exp_name>/plan.md`
- Works in `experiments/<exp_name>/code/` directory
- Ensures clean separation of planning and implementation

## Usage

### Direct Usage
```python
import asyncio
from cc_agent import run_multi_agent_system

result = await run_multi_agent_system(
    env="/path/to/project",
    proposal="Research proposal text...",
    max_attempts=3
)
```

### With Experiment Structure
```python
# Proposal will be read from plan.md automatically
result = await run_multi_agent_system(
    env="/path/to/research/env",
    proposal="",  # Empty string triggers plan.md reading
    max_attempts=3
)
```

### Integration with Tiny Agent Gym
The system integrates through `main.py` which returns a comprehensive JSON summary:
```json
{
    "final_status": "complete",
    "actor_runs_used": 3,
    "total_cost": 0.45,
    "all_critics_passed": true,
    "initial_critic_results": [
        {"critic_name": "Code Compilation", "passed": false, "feedback": "No files yet"},
        // ... baseline state
    ],
    "final_critic_results": [
        {"critic_name": "Code Compilation", "passed": true, "feedback": "All files compile"},
        {"critic_name": "Test Runner", "passed": true, "feedback": "All tests pass"},
        // ... other critics
    ],
    "conversation_history": [
        {"phase": "initial_baseline", "failing_critics": ["Code Compilation", "Test Runner", ...]},
        {"phase": "initial_actor", "cost": 0.25, "response_length": 5000},
        {"phase": "critic_failed", "critic": "Test Runner", "actor_runs_used": 1, "feedback": "..."},
        {"phase": "targeted_fix", "critic": "Test Runner", "actor_runs_used": 2, "cost": 0.05},
        {"phase": "critic_passed", "critic": "Test Runner", "actor_runs_used": 2},
        {"phase": "critic_failed", "critic": "Metrics & Logging", "actor_runs_used": 2, "feedback": "..."},
        {"phase": "targeted_fix", "critic": "Metrics & Logging", "actor_runs_used": 3, "cost": 0.08},
        {"phase": "critic_passed", "critic": "Metrics & Logging", "actor_runs_used": 3},
        // ... complete flow showing queue processing
    ],
    "targeted_fixes": [
        {"critic_name": "Test Runner", "fix_cost": 0.05, "actor_runs_used": 2},
        {"critic_name": "Metrics & Logging", "fix_cost": 0.08, "actor_runs_used": 3},
        // ... all fix attempts
    ]
}
```

## Features

- **Quality Gates**: Multiple critics ensure high-quality implementation
- **Automated Testing**: Non-AI critics for objective validation
- **AI Review**: Smart critics for subjective quality checks
- **Cost Tracking**: Monitors API costs across all interactions
- **Detailed Feedback**: Each critic provides specific feedback
- **Experiment Integration**: Works seamlessly with research environments

## Configuration

- **Tools**: Actor has full file operations, git, and web search capabilities
- **Critics Tools**: Read-only access for safety (Read, LS, Glob, Grep)
- **MCP Integration**: Uses Exa search for web research
- **Token Limits**: Configurable max turns per agent
- **Working Directory**: Automatically uses `code/` in experiment structures

## Output

The system provides:
- Real-time streaming of agent interactions
- Visual indicators for different critics (🔧, 🧪, 📋, ⚙️, 📊)
- Cost tracking per attempt and cumulative
- Pass/fail status for each critic
- JSON summary of results
- **Automatic Results Saving**: When used in experiment structure:
  - Saves detailed JSON summary to `experiments/<exp_name>/results/multiagent_summary_<timestamp>.json`
  - Updates `experiments/<exp_name>/results.md` with formatted summary