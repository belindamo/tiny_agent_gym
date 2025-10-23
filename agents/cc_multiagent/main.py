from helpers.models import Run, AgentResult, agent_main
from .cc_agent import run_multi_agent_system
import asyncio
import json


@agent_main
def main(r: Run) -> AgentResult:
    try:
        print(f"Processing task: {r.task.task}")
        task = r.task.task
        env = r.dir_name
        
        # Run the multi-agent system
        result = asyncio.run(run_multi_agent_system(
            env=env,
            proposal=task,
            max_actor_runs=8  # Maximum individual actor sessions total
        ))
        
        # Extract metrics from the result
        total_cost = result.get('total_cost', 0)
        final_status = result.get('final_status', 'incomplete')
        actor_runs_used = result.get('actor_runs_used', 0)
        final_critic_results = result.get('final_critic_results', [])
        
        # Calculate token usage (approximation based on cost)
        # Rough estimate: $0.003 per 1K input tokens, $0.015 per 1K output tokens
        # We'll approximate total tokens from cost
        estimated_total_tokens = int(total_cost * 1000 / 0.009)  # Average cost estimate
        input_tokens = int(estimated_total_tokens * 0.6)  # Approximate input/output split
        output_tokens = int(estimated_total_tokens * 0.4)
        
        # Create a JSON summary of the results
        summary_json = {
            "final_status": final_status,
            "actor_runs_used": actor_runs_used,
            "total_cost": total_cost,
            "all_critics_passed": final_status == "complete",
            "critic_results": []
        }
        
        # Include final critic results
        for critic_result in final_critic_results:
            summary_json["critic_results"].append({
                "critic": critic_result["critic_name"],
                "passed": critic_result["passed"],
                "feedback": critic_result["feedback"][:200] + "..." if len(critic_result["feedback"]) > 200 else critic_result["feedback"]
            })
        
        # Convert summary to JSON string for the result
        result_str = json.dumps(summary_json, indent=2)
        
        # Determine if task was completed successfully
        completed = final_status == "complete"
        
        return AgentResult(
            completed=completed,
            result=result_str,
            reasoning=f"Multi-agent system {'successfully completed' if completed else 'did not complete'} task using {actor_runs_used} actor runs",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=total_cost
        )
        
    except Exception as e:
        print(f"Error in multi-agent system: {str(e)}")
        error_json = {
            "error": str(e),
            "final_status": "error",
            "actor_runs_used": 0,
            "total_cost": 0.0
        }
        
        return AgentResult(
            completed=False,
            result=json.dumps(error_json, indent=2),
            reasoning=f"Error in multi-agent system execution: {str(e)}",
            input_tokens=0,
            output_tokens=0,
            cost=0.0
        )

