from helpers.models import Run, EvalResult, eval_function, Task
from pathlib import Path
import json
import os
from evals.longmemeval.evaluate_qa import *
import time
import openai


openai_api_key = os.getenv('OPENAI_API_KEY')
metric_model = "gpt-4o"
metric_client = OpenAI(
    api_key=openai_api_key,
)

def evaluate_qa_helper(task_type, question, answer, response, abstention=False) -> int:
    """
    Wrapper function around long_memeval's evaluate_qa.py original evaluation function.
    """
    qtype = task_type
    q = question
    ans = answer
    hyp = response
    abstention = abstention
    
    prompt = get_anscheck_prompt(qtype, q, ans, hyp, abstention)
    kwargs = {
        'model': metric_model,
        'messages':[
            {"role": "user", "content": prompt}
        ],
        'n': 1,
        'temperature': 0,
        'max_tokens': 10
    }
    completion = chat_completions_with_backoff(metric_client, **kwargs)
    eval_response = completion.choices[0].message.content.strip()
    label = 'yes' in eval_response.lower()
    return label
    
@eval_function
def eval_qa(r: Run) -> EvalResult:
    """Evaluate a QA task by checking if the model's response matches the expected answer."""
    
    # Load task data from task file
    with open(r.task_file) as f:
        task_data = json.load(f)
        print(f"Task data: {task_data[0].keys()}")
    
        if isinstance(task_data, list):
            task_data = task_data[0]  # Take first task if it's a list
    
    # Load agent's response from out.log
    with open(Path(r.run_dir) / "hypothesis.json") as f:
        response = f.read().strip()
    
    qtype = task_data['question_type']
    q = task_data['task']
    ans = task_data['answer']
    hyp = response
    abstention = '_abs' in task_data['task_id']
    
    score = evaluate_qa_helper(qtype, q, ans, hyp)
    return EvalResult(passed=score, result='')

def json_to_task(json_file: str) -> Task:
    with open(json_file) as f:
        tasks_data = json.load(f)
        if isinstance(tasks_data, list):
            task_data = tasks_data[0]  # Take first task if it's a list
        else:
            task_data = tasks_data  # Use as is if it's a single task
    
    return Task(
        task_id=task_data['task_id'],
        task=task_data['task'],
        dir_name=task_data['env_dir']
    )
  
# if __name__ == "__main__":
#     import sys
#     import os
#     print(sys.path)
    
#     # Path relative to gym directory
#     task_file = "tasks/longmemeval/longmemeval_1.json"
#     task = json_to_task(task_file)
    
#     run = Run(
#         task=task, # not sure why task and task_file are both needed
#         agent_name="test_agent",
#         task_file=task_file,
#         run_dir="envs/longmemeval_1",
#         dir_name=task.dir_name # this part is redundant
#     )
#     result = eval_qa(run)
#     print(result)
#     return 
    
    