import json
from pathlib import Path

from ai import dspy
from models import Task, EvalResult

class TaskEvaluator(dspy.Signature):
    """Evaluate if a task was completed successfully based on its success criteria."""
    
    task: str = dspy.InputField(desc="The task description")
    success_criteria: str = dspy.InputField(desc="The success criteria for the task")
    execution_logs: str = dspy.InputField(desc="The execution logs (stdout/stderr) from the task attempt")
    summary_info: str = dspy.InputField(desc="Summary information including timing, tokens, and results")
    
    passed: bool = dspy.OutputField(desc="Whether the task succeeded (True/False)")
    reasoning: str = dspy.OutputField(desc="Step-by-step reasoning for the evaluation")
    details: str = dspy.OutputField(desc="Detailed explanation of the evaluation result")

predictor = dspy.ChainOfThought(TaskEvaluator)

def evaluate_task(task: Task, run_dir: str) -> EvalResult:
    """
    Evaluate whether a task was completed successfully by examining logs, outputs, and summary.
    
    Args:
        task: The Task object containing the task description and success criteria
        run_dir: Directory containing task execution logs and outputs
    
    Returns:
        EvalResult indicating success/failure with detailed explanation
    """
    run_path = Path(run_dir)
    
    # Gather execution logs
    execution_logs = ""
    
    # Read stdout logs
    stdout_path = run_path / "out.log"
    if stdout_path.exists():
        with open(stdout_path) as f:
            content = f.read().strip()
            if content:
                execution_logs += f"<STDOUT>\n{content}\n</STDOUT>\n\n"
    
    # Read stderr logs  
    stderr_path = run_path / "err.log"
    if stderr_path.exists():
        with open(stderr_path) as f:
            content = f.read().strip()
            if content:
                execution_logs += f"<STDERR>\n{content}\n</STDERR>\n\n"
    
    # Read info logs
    info_path = run_path / "info.log"
    if info_path.exists():
        with open(info_path) as f:
            content = f.read().strip()
            if content:
                execution_logs += f"<INFO_LOG>\n{content}\n</INFO_LOG>\n\n"
    
    # Read error logs
    error_path = run_path / "error.log"
    if error_path.exists():
        with open(error_path) as f:
            content = f.read().strip()
            if content:
                execution_logs += f"<ERROR_LOG>\n{content}\n</ERROR_LOG>\n\n"
    
    if not execution_logs:
        execution_logs = "No execution logs found."
    
    # Gather summary information
    summary_info = ""
    summary_path = run_path / "summary.json"
    if summary_path.exists():
        try:
            with open(summary_path) as f:
                summary_data = json.load(f)
                summary_info = f"<SUMMARY>\n{json.dumps(summary_data, indent=2)}\n</SUMMARY>"
        except (json.JSONDecodeError, FileNotFoundError):
            summary_info = "Summary file exists but could not be parsed."
    else:
        summary_info = "No summary file found."
    
    # Run the evaluation
    result = predictor(
        task=task.task,
        success_criteria=task.success_criteria if task.success_criteria else "Task is fulfilled",
        execution_logs=execution_logs,
        summary_info=summary_info
    )
    
    return EvalResult(
        passed=result.passed,
        result=f"Reasoning:\n{result.reasoning}\n\nDetails:\n{result.details}"
    )

if __name__ == "__main__":
    # Simple test case
    test_task = Task(
        task_id="test_task",
        task="Create a README.md file",
        success_criteria="README.md exists and contains Installation and Usage sections",
        dir_name="test_env"
    )
    
    print("Running test evaluation...")
    # This would need a real run directory to work
    # result = evaluate_task(test_task, "test_run_dir")
    # print(f"Result: {result}")
    print("LLM Evaluator loaded successfully!")
