import os
import argparse
import json
import importlib
import importlib.util
import logging
import time
import shutil
import sys
import asyncio
import inspect
from pathlib import Path

from helpers.models import Task, Run, RunSummary, TaskLog
from helpers.utils import get_next_experiment_number, get_formatted_datetime
from helpers.llm_as_a_judge import evaluate_task
from helpers.logger import setup_logging, silence_loggers, redirect_stdout_stderr

def cli_main():
    """CLI entry point for the tag command"""
    parser = argparse.ArgumentParser(
        description="tiny-agent-gym: A lightweight, local-first agent execution framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  tag "Write a hello world Python script"
  tag "Create a web scraper" --success "Script successfully fetches data from example.com"
  tag --task example
  tag "Improve the code" --env example
  tag "Complex task" --agent react_with_mcp
        """
    )
    
    # Task description (positional argument)
    parser.add_argument(
        "task_description", 
        nargs="?", 
        help="Description of the task to execute"
    )
    
    # Optional arguments
    parser.add_argument(
        "--success", 
        help="Success criteria for the task"
    )
    
    parser.add_argument(
        "--task", 
        help="Path to existing task configuration file"
    )
    
    parser.add_argument(
        "--env", 
        help="Path to existing environment directory"
    )
    
    parser.add_argument(
        "--eval", 
        help="Path to custom evaluation script"
    )
    
    parser.add_argument(
        "--agent", 
        default="react",
        help="Agent name (default: react)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.task_description and not args.task:
        parser.error("Either task description or --task must be provided")
    
    if args.task_description and args.task:
        parser.error("Only one of task description or --task can be provided")

    # Run the task
    run_task(args)

def run_task(cli_args):
    """Run a task using the CLI interface"""
    print("🚀 Starting tiny-agent-gym...")
    
    # Create a task configuration
    if cli_args.task:
        # Load existing task
        task_file = Path(cli_args.task)
        if not task_file.exists():
            # Check if it's just the name without .json extension
            task_file = Path("tasks") / f"{cli_args.task}.json"
            if not task_file.exists():
                print(f"❌ Task file not found: {cli_args.task}")
                return
        
        # Pass the task file name without .json extension to main_execution
        task_name = task_file.stem
        
        # Set up arguments for the main execution
        class Args:
            def __init__(self):
                self.agent = cli_args.agent
                self.tasks = task_name
    else:
        # Create new task from description
        # Generate a task ID from the description using dspy/simple heuristics
        task_description = cli_args.task_description
        
        # Create a short task_id from the description (first few words, cleaned)
        task_id_words = task_description.lower().split()[:3]
        task_id = "_".join(word.strip(".,!?") for word in task_id_words)
        task_id = task_id.replace(" ", "_").replace("-", "_")
        
        # Create the task with proper structure
        task_config = {
            "task_id": task_id,
            "task": task_description,
            "success_criteria": cli_args.success or "Task completed successfully",
            "dir_name": None  # Will create empty env
        }
        
        # If user specified a custom evaluation script
        if cli_args.eval:
            # Create a unique dir_name for this task
            exp_num = get_next_experiment_number()
            dir_name = f"{task_id}_{exp_num}"
            task_config["dir_name"] = dir_name
            
            # Create the evaluation directory and copy the eval script
            eval_dir = Path("evals") / dir_name
            eval_dir.mkdir(parents=True, exist_ok=True)
            
            eval_source = Path(cli_args.eval)
            if eval_source.exists():
                shutil.copy2(eval_source, eval_dir / "eval.py")
                print(f"📝 Copied evaluation script to {eval_dir / 'eval.py'}")
            else:
                print(f"⚠️  Warning: Evaluation script not found: {cli_args.eval}")
        
        # If user specified an existing environment
        if cli_args.env:
            task_config["dir_name"] = cli_args.env
        
        # Create tasks directory if it doesn't exist
        tasks_dir = Path("tasks")
        tasks_dir.mkdir(exist_ok=True)
        
        # Create a task file with a descriptive name
        task_num = get_next_experiment_number()
        task_file_name = f"task_{task_num:03d}_{task_id}"
        task_file = tasks_dir / f"{task_file_name}.json"
        
        with open(task_file, 'w') as f:
            json.dump([task_config], f, indent=2)
        
        print(f"📋 Created task file: {task_file}")
        
        # Set up arguments for the main execution
        class Args:
            def __init__(self):
                self.agent = cli_args.agent
                self.tasks = task_file_name
    
    # Run the main execution
    main_execution(Args())

def main_execution(args):
    print("🚀 Starting AI Scientist Gym...")
    
    # Silence specific loggers
    silence_loggers(["LiteLLM"])
    
    # Generate unique run directory automatically
    exp_num = get_next_experiment_number()
    task_name = Path(args.tasks).name  # Get just the filename, not the full path
    instance_id = f"{exp_num}_{task_name}_{get_formatted_datetime()}"
    run_dir = Path("runs") / instance_id
    run_dir.mkdir(parents=True, exist_ok=True) 
    print(f"📁 Created run directory: {run_dir}")

    # Configure logging
    setup_logging(run_dir)
    redirect_stdout_stderr()

    logger = logging.getLogger(__name__)
    logger.info(f"Starting run with agent: {args.agent}, tasks: {args.tasks}, run_dir: {run_dir}")

    # Stats tracking
    start_time = time.time()
    input_tokens = 0
    output_tokens = 0
    total_cost = 0
    task_logs = []

    # Import the agent's main function
    try:
        agent_module = importlib.import_module(f"agents.{args.agent}.main")
        agent_main = agent_module.main
        logger.info(f"Successfully imported agent: {args.agent}")
    except ImportError as e:
        print(f"❌ Failed to import agent {args.agent}: {e}")
        logger.error(f"Could not import agent {args.agent}: {e}")
        raise
    except AttributeError:
        print(f"❌ Agent {args.agent} missing main() function")
        logger.error(f"Agent {args.agent} does not have a main() function")
        raise
    
    # Load and process tasks
    task_file = Path("tasks") / f"{args.tasks}.json"
    if not task_file.exists():
        print(f"❌ Task file not found: {task_file}")
        raise FileNotFoundError(f"Task file {task_file} does not exist")
    
    with open(task_file) as f:
        tasks = json.load(f)
        if not isinstance(tasks, list):
            print(f"❌ Task file must contain JSON array, got: {type(tasks)}")
            raise ValueError(f"Task file {task_file} must contain a JSON array")
        
        print(f"📋 Loaded {len(tasks)} tasks")
        
        for i, task_dict in enumerate(tasks, 1):
            print(f"\n🔄 Processing task {i}/{len(tasks)}")
            logger.info(f"Processing task {i}")
            
            try:
                task = Task(**task_dict)
                logger.info(f"Running task: {task}")
                
                # Setup environment directory (clone if specified, create if not)
                if task.dir_name:
                    source_env_dir = Path("envs") / task.dir_name
                    if not source_env_dir.exists():
                        print(f"❌ Source environment directory not found: {source_env_dir}")
                        raise FileNotFoundError(f"Source environment directory {source_env_dir} does not exist")
                    
                    cloned_env_dir = Path("envs") / f"{task.dir_name}_{instance_id}"
                    if cloned_env_dir.exists():
                        shutil.rmtree(cloned_env_dir)
                    shutil.copytree(source_env_dir, cloned_env_dir)
                    logger.info(f"Cloned environment from {source_env_dir} to {cloned_env_dir}")
                else:
                    cloned_env_dir = Path("envs") / instance_id
                    cloned_env_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created new environment directory: {cloned_env_dir}")
                
                # Run the task
                task_start = time.time()
                run_data = Run(
                    task=task,
                    agent_name=args.agent,
                    task_file=str(task_file),
                    run_dir=str(run_dir),
                    dir_name=str(cloned_env_dir)
                )
                
                if inspect.iscoroutinefunction(agent_main):
                    result = asyncio.run(agent_main(run_data))
                else:
                    result = agent_main(run_data)
                
                task_time = time.time() - task_start
                logger.info(f"Completed task {i} in {task_time:.2f}s")
                
                # Update token counts if agent returns them (only count actual values, not null/missing)
                task_input_tokens = None
                task_output_tokens = None
                task_cost = None
                
                if isinstance(result, dict):
                    task_input_tokens = result.get('input_tokens')
                    task_output_tokens = result.get('output_tokens')
                    task_cost = result.get('cost')
                elif result and hasattr(result, 'input_tokens'):
                    task_input_tokens = getattr(result, 'input_tokens', None)
                    task_output_tokens = getattr(result, 'output_tokens', None)
                    task_cost = getattr(result, 'cost', None)
                
                # Only add to totals if we have actual values (not None/null)
                if task_input_tokens is not None and task_input_tokens > 0:
                    input_tokens += task_input_tokens
                if task_output_tokens is not None and task_output_tokens > 0:
                    output_tokens += task_output_tokens
                if task_cost is not None and task_cost > 0:
                    total_cost += task_cost
                
                # Log with proper null handling
                input_str = str(task_input_tokens) if task_input_tokens is not None else "null"
                output_str = str(task_output_tokens) if task_output_tokens is not None else "null"
                cost_str = str(task_cost) if task_cost is not None else "null"
                logger.info(f"Token usage - Input: {input_str}, Output: {output_str}, Cost: {cost_str}")

                # Run LLM-based evaluation
                llm_eval_result = None
                try:
                    logger.info(f"Running LLM evaluation for task {i}")
                    llm_eval_result = evaluate_task(task, str(run_dir))
                    logger.info(f"LLM evaluation completed for task {i}: passed={llm_eval_result.passed}")
                except Exception as e:
                    print(f"❌ LLM evaluation failed: {e}")
                    logger.error(f"Error running LLM evaluation for task {i}: {e}", exc_info=True)

                # Run task-specific evaluation if eval file exists
                eval_result = None
                if task.dir_name:
                    eval_file_path = Path("evals") / task.dir_name / "eval.py"
                    if eval_file_path.exists():
                        try:
                            logger.info(f"Running task-specific evaluation for task {i}")
                            # Import the evaluation module directly from file path
                            eval_file_path_str = str(eval_file_path)
                            eval_module_name = f"eval_{task.dir_name.replace('/', '_')}"
                            
                            # Add current directory to sys.path to ensure imports work in eval.py
                            current_dir = str(Path.cwd())
                            if current_dir not in sys.path:
                                sys.path.insert(0, current_dir)
                            
                            spec = importlib.util.spec_from_file_location(eval_module_name, eval_file_path_str)
                            eval_module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(eval_module)
                            
                            # Find the evaluation function (look for functions decorated with @eval_function)
                            eval_function = None
                            for attr_name in dir(eval_module):
                                attr = getattr(eval_module, attr_name)
                                if callable(attr) and hasattr(attr, '__wrapped__'):
                                    eval_function = attr
                                    break
                            
                            if eval_function:
                                eval_result = eval_function(run_data)
                                logger.info(f"Task-specific evaluation completed for task {i}: passed={eval_result.passed}")
                            else:
                                logger.warning(f"No eval function found in {eval_file_path}")
                                
                        except Exception as e:
                            print(f"❌ Task-specific evaluation failed: {e}")
                            logger.error(f"Error running task-specific evaluation for task {i}: {e}", exc_info=True)
                    else:
                        logger.info(f"No task-specific evaluation file found at {eval_file_path}")

                # Log task details using TaskLog model
                task_log = TaskLog(
                    task_id=i,
                    task=task,  # Use the Task object directly
                    ms=task_time * 1000,
                    result=result,  # Pass the AgentResult object directly
                    llm_evaluation=llm_eval_result,  # Pass the EvalResult object directly
                    evaluation=eval_result  # Pass the EvalResult object directly
                )
                task_logs.append(task_log)
                
            except Exception as e:
                print(f"❌ Error processing task {i}: {e}")
                logger.error(f"Error processing task {i}: {e}", exc_info=True)

    # Write summary stats
    total_time = time.time() - start_time
    
    # Calculate total score (completed tasks / all tasks)
    completed_tasks = sum(1 for log in task_logs if log.result and log.result.completed)
    total_tasks = len(task_logs)
    total_score = f"{completed_tasks}/{total_tasks}"
    
    # Build summary using RunSummary model
    summary_dict = {
        'agent_name': args.agent,
        'run_dir': str(run_dir),
        'total_time': f"{total_time:.2f}s",
        'total_score': total_score,
        'task_logs': task_logs
    }
    
    # Only include token/cost information if we have actual data
    if input_tokens > 0 or output_tokens > 0:
        summary_dict['input_tokens'] = input_tokens
        summary_dict['output_tokens'] = output_tokens
        summary_dict['total_tokens'] = input_tokens + output_tokens
    
    if total_cost > 0:
        summary_dict['total_cost'] = total_cost
    
    # Create RunSummary instance
    summary = RunSummary(**summary_dict)
    
    print(f"\n🏁 All tasks completed!")
    print(f"⏱️ Total time: {total_time:.2f}s")
    
    # Only show token information if we have it
    if input_tokens > 0 or output_tokens > 0:
        print(f"🔢 Total tokens: {input_tokens + output_tokens} (in: {input_tokens}, out: {output_tokens})")
    else:
        print(f"🔢 Total tokens: N/A (no token tracking data)")
    
    # Only show cost if we have it
    if total_cost > 0:
        print(f"💰 Total cost: ${total_cost:.4f}")
    else:
        print(f"💰 Total cost: N/A (no cost tracking data)")
    
    print(f"✅ Total score: {total_score}")
    
    summary_path = run_dir / "summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary.model_dump(exclude_none=True), f, indent=2)
    
    logger.info("Run completed successfully")
    print("🎉 Run completed!")
    print(f"📄 Summary saved to: {summary_path}")

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", required=True, help="Agent name (e.g., react, react_with_mcp)")
    parser.add_argument("--tasks", required=True, help="Path to tasks file")
    args = parser.parse_args()
    
    # Run the main execution
    main_execution(args)