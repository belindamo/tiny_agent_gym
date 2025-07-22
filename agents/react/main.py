from .actions import ActionsReAct
from .react import ReAct
from models import Run, AgentResult, agent_main
from .utils.ai import dspy, lm

class ExecuteExperiment(dspy.Signature):
    """Execute this experiment based on the conditions provided."""

    problem: str = dspy.InputField(
        description="The problem we are trying to solve with this experiment"
    )
    completed: bool = dspy.OutputField(
        description="Whether the experiment was completed"
    )
    result: str = dspy.OutputField(description="The result of the experiment")

@agent_main
def main(r: Run) -> AgentResult:
  try:
    print(f"ReAct agent processing task:")
    problem = r.task.task
    env = r.dir_name

    actions = ActionsReAct(env)
    react = ReAct(ExecuteExperiment, tools=[
      actions.create_file,
      actions.delete_file,
      actions.edit_file,
      actions.read_file,
      actions.execute_terminal_command
    ])

    result = react(
      problem=problem
    )
    print(result)
    
    # Debug: Check lm.history
    print(f"DEBUG: lm.history length: {len(lm.history)}")
    print(f"DEBUG: lm.history sample: {lm.history[-1] if lm.history else 'Empty'}")
    
    # Use token counts from the result, not from local lm.history
    input_tokens = result.get('input_tokens', 0)
    output_tokens = result.get('output_tokens', 0)
    cost = result.get('cost', 0)
    
    print(f"DEBUG: Tokens from result - input: {input_tokens}, output: {output_tokens}, cost: {cost}")
    
    return AgentResult(
      completed=result['completed'], 
      result=result['result'], 
      reasoning=result['reasoning'], 
      input_tokens=input_tokens if input_tokens else None,
      output_tokens=output_tokens if output_tokens else None, 
      cost=cost if cost else None
    )
  except Exception as e:
    print(f"Error in ReAct agent: {str(e)}")
    return AgentResult(completed=False, result=f"Error: {str(e)}", reasoning="Error in agent", input_tokens=0, output_tokens=0)

