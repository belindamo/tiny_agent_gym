from helpers.models import Run, AgentResult, agent_main
from .cc_agent import run_actor_critic_system
import asyncio


@agent_main
def main(r: Run) -> AgentResult:
    try:
        print(f"Processing task: {r.task.task}")
        task = r.task.task
        env = r.dir_name
        
        # Run the actor-critic system
        result = asyncio.run(run_actor_critic_system(
            env=env,
            proposal=task,
            num_rounds=3,  # Default to 3 rounds, can be made configurable
            max_turns_per_agent=10
        ))
        
        # Extract metrics from the result
        total_cost = result.get('total_cost', 0)
        conversation_history = result.get('conversation_history', [])
        
        # Calculate token usage (approximation based on cost)
        # Rough estimate: $0.003 per 1K input tokens, $0.015 per 1K output tokens
        # We'll approximate total tokens from cost
        estimated_total_tokens = int(total_cost * 1000 / 0.009)  # Average cost estimate
        input_tokens = int(estimated_total_tokens * 0.6)  # Approximate input/output split
        output_tokens = int(estimated_total_tokens * 0.4)
        
        # Create summary of the conversation
        summary = f"Actor-Critic system completed {result['num_rounds']} rounds with {len(conversation_history)} total interactions."
        
        return AgentResult(
            completed=True,
            result=summary,
            reasoning=f"Successfully executed actor-critic system for task: {task}",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=total_cost
        )
        
    except Exception as e:
        print(f"Error in actor-critic agent: {str(e)}")
        return AgentResult(
            completed=False,
            result=f"Error: {str(e)}",
            reasoning="Error in actor-critic agent execution",
            input_tokens=0,
            output_tokens=0,
            cost=0.0
        )


