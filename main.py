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

from models import Task, Run
from utils import get_next_experiment_number, get_formatted_datetime
from llm_as_a_judge import evaluate_task

if __name__ == "__main__":
  print("🚀 Starting AI Scientist Gym...")
  
  # Silence specific loggers
  silence_logs = ["LiteLLM"]
  for logger_name in silence_logs:
    logging.getLogger(logger_name).setLevel(logging.WARNING)
  print("✅ Configured logging levels")

  # Parse command line arguments
  parser = argparse.ArgumentParser()
  parser.add_argument("--agent", required=True, help="Path to agent folder")
  parser.add_argument("--tasks", required=True, help="Path to tasks file")
  args = parser.parse_args()
  print(f"📋 Parsed arguments - Agent: {args.agent}, Tasks: {args.tasks}")
  
  # Generate unique run directory automatically
  exp_num = get_next_experiment_number()
  task_name = Path(args.tasks).name  # Get just the filename, not the full path
  instance_id = f"{exp_num}_{task_name}_{get_formatted_datetime()}"
  run_dir = Path("runs") / instance_id
  run_dir.mkdir(parents=True, exist_ok=True) 
  print(f"📁 Created run directory: {run_dir}")

  # Configure logging
  log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
      logging.FileHandler(run_dir / "all.log"),
      logging.StreamHandler()
    ],
    force=True
  )
  print("📝 Configured main logging")

  # Add separate log files for info and errors
  root_logger = logging.getLogger()
  info_handler = logging.FileHandler(run_dir / "info.log")
  info_handler.setLevel(logging.INFO)
  info_handler.setFormatter(logging.Formatter(log_format))
  root_logger.addHandler(info_handler)
  
  error_handler = logging.FileHandler(run_dir / "error.log")
  error_handler.setLevel(logging.ERROR)
  error_handler.setFormatter(logging.Formatter(log_format))
  root_logger.addHandler(error_handler)
  
  # Configure stderr logger to use the same error.log file
  stderr_logger = logging.getLogger("stderr")
  stderr_logger.addHandler(error_handler)  # Use the same error handler
  stderr_logger.setLevel(logging.ERROR)
  stderr_logger.propagate = False  # Prevent duplication with root logger
  print("📊 Added additional log handlers")

  # Redirect prints and errors to logging
  class PrintToLogger:
    def __init__(self, is_stderr=False):
      self._stdout = sys.stdout
      self._stderr = sys.stderr
      self._is_stderr = is_stderr
      self._buffer = []
      # Store the original fileno
      self._fileno = self._stderr.fileno() if is_stderr else self._stdout.fileno()
      
    def write(self, text):
      if text.strip():
        if self._is_stderr:
          logging.getLogger("stderr").error(text.rstrip())
        else:
          logging.getLogger("stdout").info(text.rstrip())
      
      # Also write to original stdout/stderr
      if self._is_stderr:
        self._stderr.write(text)
      else:
        self._stdout.write(text)
      
    def flush(self):
      if self._is_stderr:
        self._stderr.flush()
      else:
        self._stdout.flush()
        
    def fileno(self):
      # Return the stored fileno
      return self._fileno

  # Only redirect stdout/stderr if not in a subprocess
  if not os.environ.get('MCP_SUBPROCESS'):
    sys.stdout = PrintToLogger(is_stderr=False)
    sys.stderr = PrintToLogger(is_stderr=True)
    
    def fileno(self):
      # Return the original file descriptor for subprocess compatibility
      if self._is_stderr:
        return self._stderr.fileno()
      else:
        return self._stdout.fileno()
    
    def isatty(self):
      # Check if the original stream is a terminal
      if self._is_stderr:
        return self._stderr.isatty()
      else:
        return self._stdout.isatty()

  logger = logging.getLogger(__name__)
  print("🔄 Redirected stdout/stderr to logging")

  task_file = Path("tasks") / f"{args.tasks}.json"
  print(f"🎯 Looking for task file: {task_file}")
  logger.info(f"Starting run with agent: {args.agent}, tasks: {args.tasks}, run_dir: {run_dir}")

  # Stats tracking
  start_time = time.time()
  input_tokens = 0
  output_tokens = 0
  task_logs = []
  print("⏱️ Started timer and initialized stats tracking")

  # Import the agent's main function
  print(f"🤖 Attempting to import agent: agents.{args.agent}.main")
  try:
    agent_module = importlib.import_module(f"agents.{args.agent}.main")
    agent_main = agent_module.main
    print(f"✅ Successfully imported agent: {args.agent}")
  except ImportError as e:
    print(f"❌ Failed to import agent {args.agent}: {e}")
    logger.error(f"Could not import agent {args.agent}: {e}")
    raise
  except AttributeError:
    print(f"❌ Agent {args.agent} missing main() function")
    logger.error(f"Agent {args.agent} does not have a main() function")
    raise
  
  # Load and process tasks
  print(f"📂 Checking if task file exists: {task_file}")
  if not task_file.exists():
    print(f"❌ Task file not found: {task_file}")
    raise FileNotFoundError(f"Task file {task_file} does not exist")
  
  print(f"📖 Loading tasks from: {task_file}")
  with open(task_file) as f:
    tasks = json.load(f)
    if not isinstance(tasks, list):
      print(f"❌ Task file must contain JSON array, got: {type(tasks)}")
      raise ValueError(f"Task file {task_file} must contain a JSON array")
    
    print(f"✅ Loaded {len(tasks)} tasks from file")
    
    for i, task_dict in enumerate(tasks, 1):
      print(f"\n🔄 Processing task {i}/{len(tasks)}")
      logger.info(f"Processing task {i}")
      
      try:
        task = Task(**task_dict)
        print(f"✅ Created task object: {task.task[:50]}..." if len(task.task) > 50 else task.task)
        logger.info(f"Running task: {task}")
        
        # Setup environment directory (clone if specified, create if not)
        if task.dir_name:
            source_env_dir = Path("envs") / task.dir_name
            print(f"🏗️ Setting up environment from: {source_env_dir}")
            if not source_env_dir.exists():
                print(f"❌ Source environment directory not found: {source_env_dir}")
                raise FileNotFoundError(f"Source environment directory {source_env_dir} does not exist")
            
            cloned_env_dir = Path("envs") / f"{task.dir_name}_{instance_id}"
            if cloned_env_dir.exists():
                print(f"🧹 Removing existing cloned directory: {cloned_env_dir}")
                shutil.rmtree(cloned_env_dir)
            print(f"📋 Cloning environment to: {cloned_env_dir}")
            shutil.copytree(source_env_dir, cloned_env_dir)
            print(f"✅ Environment cloned successfully")
            logger.info(f"Cloned environment from {source_env_dir} to {cloned_env_dir}")
        else:
            cloned_env_dir = Path("envs") / instance_id
            cloned_env_dir.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created new environment directory: {cloned_env_dir}")
            logger.info(f"Created new environment directory: {cloned_env_dir}")
        
        # Run the task
        print(f"🚀 Running task with agent...")
        task_start = time.time()
        run_data = Run(
            task=task,
            agent_name=args.agent,
            task_file=str(task_file),
            run_dir=str(run_dir),
            dir_name=str(cloned_env_dir)
        )
        
        if inspect.iscoroutinefunction(agent_main):
            print("🔄 Running async agent...")
            result = asyncio.run(agent_main(run_data))
        else:
            print("🔄 Running sync agent...")
            result = agent_main(run_data)
        
        task_time = time.time() - task_start
        print(f"✅ Task completed in {task_time:.2f}s")
        
        # Update token counts if agent returns them
        task_input_tokens = 0
        task_output_tokens = 0
        if isinstance(result, dict):
          task_input_tokens = result.get('input_tokens')
          task_output_tokens = result.get('output_tokens')
          input_tokens += task_input_tokens
          output_tokens += task_output_tokens
          print(f"📊 Token usage - Input: {task_input_tokens}, Output: {task_output_tokens}")
          
        logger.info(f"Completed task {i} in {task_time:.2f}s")

        # Run LLM-based evaluation
        llm_eval_result = None
        print("🧠 Running LLM evaluation...")
        try:
          logger.info(f"Running LLM evaluation for task {i}")
          llm_eval_result = evaluate_task(task, str(run_dir))
          print(f"✅ LLM evaluation completed - Passed: {llm_eval_result.passed}")
          logger.info(f"LLM evaluation completed for task {i}: passed={llm_eval_result.passed}")
        except Exception as e:
          print(f"❌ LLM evaluation failed: {e}")
          logger.error(f"Error running LLM evaluation for task {i}: {e}", exc_info=True)

        # Run task-specific evaluation if eval file exists
        eval_result = None
        if task.dir_name:
          eval_file_path = Path("evals") / task.dir_name / "eval.py"
          print(f"🔍 Checking for task-specific evaluation: {eval_file_path}")
          if eval_file_path.exists():
            print("📝 Found task-specific evaluation file")
            try:
              logger.info(f"Running task-specific evaluation for task {i}")
              # Import the evaluation module directly from file path
              eval_file_path_str = str(eval_file_path)
              eval_module_name = f"eval_{task.dir_name.replace('/', '_')}"
              print(f"📥 Importing evaluation module from: {eval_file_path_str}")
              
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
                print(f"🎯 Found evaluation function: {eval_function.__name__}")
                eval_result = eval_function(run_data)
                print(f"✅ Task-specific evaluation completed - Passed: {eval_result.passed}")
                logger.info(f"Task-specific evaluation completed for task {i}: passed={eval_result.passed}")
              else:
                print(f"⚠️ No eval function found in {eval_file_path}")
                logger.warning(f"No eval function found in {eval_file_path}")
                
            except Exception as e:
              print(f"❌ Task-specific evaluation failed: {e}")
              logger.error(f"Error running task-specific evaluation for task {i}: {e}", exc_info=True)
          else:
            print("ℹ️ No task-specific evaluation file found")
            logger.info(f"No task-specific evaluation file found at {eval_file_path}")

        # Log task details
        task_logs.append({
          'task_id': i,
          'task': task_dict,
          'ms': task_time * 1000,
          'result': result.__dict__ if result else None,
          'llm_evaluation': llm_eval_result.__dict__ if llm_eval_result else None,
          'evaluation': eval_result.__dict__ if eval_result else None
        })
        print(f"📋 Task {i} results logged")
        
      except Exception as e:
        print(f"❌ Error processing task {i}: {e}")
        logger.error(f"Error processing task {i}: {e}", exc_info=True)

  # Write summary stats
  total_time = time.time() - start_time
  
  # Calculate total score (completed tasks / all tasks)
  completed_tasks = sum(1 for log in task_logs if log.get('result', {}).get('completed', False))
  total_tasks = len(task_logs)
  total_score = f"{completed_tasks}/{total_tasks}"
  
  summary = {
    'total_time': f"{total_time:.2f}s",
    'input_tokens': input_tokens,
    'output_tokens': output_tokens,
    'total_tokens': input_tokens + output_tokens,
    'total_score': total_score,
    'task_logs': task_logs
  }
  
  print(f"\n🏁 All tasks completed!")
  print(f"⏱️ Total time: {total_time:.2f}s")
  print(f"🔢 Total tokens: {input_tokens + output_tokens} (in: {input_tokens}, out: {output_tokens})")
  print(f"✅ Total score: {total_score}")
  print(f"📊 Writing summary to: {run_dir / 'summary.json'}")
  
  with open(run_dir / "summary.json", 'w') as f:
    json.dump(summary, f, indent=2)
  
  print("✅ Summary written successfully!")
  print("🎉 Run completed!")