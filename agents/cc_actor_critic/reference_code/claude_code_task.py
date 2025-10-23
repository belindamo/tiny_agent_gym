import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from utils.datetime import get_formatted_datetime
from models import Task, Run 
from utils.llm_evaluator import evaluate_task
import subprocess
import json
import threading
from server.utils import get_next_experiment_number

def task_completion_cb(process, task, run_dir):
    """Callback function to run after subprocess completes"""
    # Wait for process to complete
    process.wait()
    
    # Run evaluation
    eval_result = evaluate_task(task, str(run_dir))
    
    # Read existing run.json file
    run_json_path = run_dir / "run.json"
    with open(run_json_path, "r") as f:
        run_data = json.load(f)
    
    # Add evaluation results to run data
    run_data["result"] = eval_result.model_dump()
    
    # Write updated run data back to run.json
    with open(run_json_path, "w") as f:
        json.dump(run_data, f, indent=2)
    
    print(f"Task {task.task_id} evaluation completed and saved to run.json")

async def start_task(t: Task, agent: str = "claude"):
        
    try:
        # Get next experiment number and create unique task ID with number and datetime
        exp_num = get_next_experiment_number()
        t.task_id = f"{exp_num}_{t.task_id}_{get_formatted_datetime()}"
        
        print('UNIQUE TASK ID', t.task_id)
        
        # Create task JSON file
        task_file = Path("tasks") / f"{t.task_id}.json"
        tasks = [ t ]
        with open(task_file, "w") as f:
            json.dump([item.model_dump() for item in tasks], f, indent=2)
            
        instance_id = f"{t.task_id}_{get_formatted_datetime()}"
        
        # Create task env instance folder
        env_dir = '' 
        if t.dir_name:
            env_dir = Path("envs") / t.dir_name
            if not env_dir.exists():
                raise HTTPException(status_code=400, detail=f"Environment directory {env_dir} does not exist")
        else:
            env_dir = Path("envs") / instance_id
            env_dir.mkdir(parents=True, exist_ok=False)
            
        # Create run instance folder
        run_dir = Path("runs") / instance_id
        run_dir.mkdir(parents=True, exist_ok=False)
        run = Run(
            task=t,
            agent_name=agent,
            task_file=str(task_file),
            run_dir=str(run_dir),
            dir_name=str(env_dir)
        )
        with open(run_dir / "run.json", "w") as f:
            json.dump(run.model_dump(), f, indent=2)
            
        task_prompt = f"Complete the following task in one shot (assume all information you need is in the directory, do not ask questions): {t.task}"
        command = ["claude", "-p", task_prompt, "--allowedTools", "Edit", "Write", "Task", "Bash"]
        
        with open(run_dir / "out.log", "w") as out_log, \
             open(run_dir / "err.log", "w") as err_log:
            
            # Use Popen for non-blocking execution with logs
            process = subprocess.Popen(
                command, 
                cwd=env_dir,
                stdout=out_log, 
                stderr=err_log, 
                text=True            
            )
            
            # Start a thread to handle the callback after process completion
            thread = threading.Thread(
                target=task_completion_cb,
                args=(process, t, run_dir)
            )
            thread.daemon = True
            thread.start()
            
        run_url = f"{os.getenv('ROOT_URL')}/{run_dir}"
        return {
            "status": "processing", 
            "process_id": process.pid, 
            "run_url": run_url, 
            "run": run.model_dump(),
            "message": "Task started. Evaluation will be performed after completion."
        }
    
    except subprocess.CalledProcessError as e:
        return {"status": "error", "message": e.stderr}
    except Exception as e:
        return {"status": "error", "message": str(e)}

