from pydantic import BaseModel, Field
from typing import Optional, Callable, List, Dict, Any
from functools import wraps
import inspect

class Task(BaseModel):
  task_id: str = Field(..., example="update_readme")
  task: str = Field(..., example="Update the README.md to describe the repository. Create the README.md if it doesn't exist")
  success_criteria: Optional[str] = Field(None, example="README.md exists and contains at least 100 words describing the repository's purpose, structure, and usage")
  ms: Optional[int] = Field(None, example=3600000)
  dir_name: Optional[str] = Field(None, description="Directory name of the env folder to clone and the eval folder to evaluate with", example="dummy_env")

class AgentResult(BaseModel):
    completed: bool = Field(..., description="Whether the experiment was completed")
    result: str = Field(..., description="The result of the experiment")
    input_tokens: Optional[int] = Field(None, description="The number of input tokens used by the agent")
    output_tokens: Optional[int] = Field(None, description="The number of output tokens used by the agent")
    cost: Optional[float] = Field(None, description="The cost of the agent")
    reasoning: str = Field(..., description="The reasoning of the agent")

class EvalResult(BaseModel):
  passed: bool = Field(..., description="Whether the task succeeded")
  result: str = Field(..., description="Detailed explanation of the evaluation result")

class TaskLog(BaseModel):
  task_id: int = Field(..., description="The sequential task number")
  task: Task = Field(..., description="The original task")
  ms: float = Field(..., description="Task execution time in milliseconds")
  result: Optional[AgentResult] = Field(None, description="Agent result if available")
  llm_evaluation: Optional[EvalResult] = Field(None, description="LLM evaluation result if available")
  evaluation: Optional[EvalResult] = Field(None, description="Task-specific evaluation result if available")

class RunSummary(BaseModel):
  agent_name: str = Field(..., description="Name/path of the agent used for this run")
  run_dir: str = Field(..., description="Directory where run outputs are stored")
  total_time: str = Field(..., description="Total execution time in seconds", example="56.03s")
  total_score: str = Field(..., description="Score as completed/total tasks", example="1/1")
  task_logs: List[TaskLog] = Field(..., description="Detailed logs for each task")
  # Optional fields - only included when data is available
  input_tokens: Optional[int] = Field(None, description="Total input tokens across all tasks")
  output_tokens: Optional[int] = Field(None, description="Total output tokens across all tasks")
  total_tokens: Optional[int] = Field(None, description="Total tokens (input + output)")
  total_cost: Optional[float] = Field(None, description="Total cost across all tasks")

class Run(BaseModel):
  task: Task
  agent_name: str
  task_file: str
  run_dir: str
  dir_name: str = Field(description="Directory name of the env folder that the agent runs in")

# Type alias for evaluation functions
EvalFunction = Callable[[Run], EvalResult]

def eval_function(func: EvalFunction) -> EvalFunction:
  """Decorator to mark a function as an evaluation function."""
  @wraps(func)
  def wrapper(r: Run) -> EvalResult:
    return func(r)
  return wrapper

# Type alias for agent main functions
AgentMainFunction = Callable[[Run], AgentResult]

def agent_main(func):
  """Decorator to mark a function as an agent main function. Handles both sync and async functions."""
  if inspect.iscoroutinefunction(func):
    @wraps(func)
    async def async_wrapper(r: Run) -> AgentResult:
      return await func(r)
    return async_wrapper
  else:
    @wraps(func)
    def sync_wrapper(r: Run) -> AgentResult:
      return func(r)
    return sync_wrapper