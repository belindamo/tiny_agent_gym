from pydantic import BaseModel, Field
from typing import Optional, Callable
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