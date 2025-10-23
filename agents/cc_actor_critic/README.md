# Claude Code Actor-Critic Agent System

This is an actor-critic system using 2 instances of Claude Code that work together in alternating rounds to complete research tasks.

## How it Works

The system implements a graduate student (actor) and professor (critic) collaboration pattern:

### Actor Agent (Graduate Student)
- **Role**: Implements experiments and research tasks
- **Capabilities**: Read/write files, use git, run experiments, web search
- **Prompt**: Uses `prompt_for_actor()` from `run_prompts.py`
- **Focus**: Systematic implementation, testing, and documentation

### Critic Agent (Professor)  
- **Role**: Reviews student's work and provides feedback
- **Capabilities**: Same tools as actor for thorough review
- **Prompt**: Uses `prompt_for_critic()` from `run_prompts.py`
- **Focus**: Quality assurance, scientific rigor, identifying issues

## Architecture

```python
# Main function for X rounds of actor-critic interaction
async def run_actor_critic_system(
    env: str,                    # Working directory
    proposal: str,               # Research proposal/task
    num_rounds: int = 3,         # Number of rounds
    max_turns_per_agent: int = 10 # Max turns per agent per round
)
```

### Round Structure
1. **Actor Phase**: Student works on implementation based on proposal and any previous critic feedback
2. **Critic Phase**: Professor reviews the student's work and provides detailed feedback
3. **Repeat**: For specified number of rounds with feedback carried forward

## Usage

### Direct Usage
```python
import asyncio
from cc_agent import run_actor_critic_system

result = await run_actor_critic_system(
    env="/path/to/project",
    proposal="Research proposal text...",
    num_rounds=3,
    max_turns_per_agent=10
)
```

### Integration with Tiny Agent Gym
The system integrates with the gym framework through `main.py` which wraps the actor-critic system and returns standardized `AgentResult` objects.

## Features

- **Persistent Context**: Each round builds on previous rounds
- **Cost Tracking**: Monitors API costs across all interactions  
- **Rich Output**: Streams responses with visual indicators for different phases
- **Error Handling**: Graceful handling of failures with detailed reporting
- **Conversation History**: Complete log of all actor-critic interactions

## Configuration

- **Tools**: Both agents have access to file operations, git commands, and web search
- **MCP Integration**: Uses Exa search for web research capabilities
- **Token Limits**: Configurable max turns per agent to prevent runaway costs
- **Working Directory**: Agents operate in specified project directory

## Output

The system provides:
- Real-time streaming of agent interactions
- Cost tracking per round and cumulative
- Conversation history with metadata
- Summary statistics and completion status 
