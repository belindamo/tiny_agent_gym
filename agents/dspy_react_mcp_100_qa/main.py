from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .utils.load_chat_sessions import load_chat_sessions_into_graphiti, load_chat_sessions_into_server_memory
from helpers.models import Run, AgentResult, agent_main, Task
from helpers.ai import dspy, lm
from .react import ReAct
from .actions import Actions
from evals.longmemeval.eval import eval_qa, json_to_task
from .utils.utils import get_cost_from_history
from pathlib import Path
from typing import Dict, List, Any
import json
import os
import asyncio
import sys

class QAAgent:
    def __init__(self, dir_name):
        self.dir_name = dir_name
        self.prompt_tokens = 0

    # async def _load_chat_sessions_into_server_memory(self, session: ClientSession, chat_sessions: List[Dict[str, str]]):
    #     """Load chat logs into the server memory."""
    #     print(f"Loading {len(chat_sessions)} chat messages into server memory...")

    #     for idx, chat_session in enumerate(chat_sessions):
    #         formatted_chat = ""
    #         messages = chat_session.get('messages', [])
    #         for message in messages:
    #             role = message.get('role', 'unknown')
    #             content = message.get('content', '')
    #             formatted_message = f"{role}: {content}"
    #             formatted_chat += formatted_message + "\n"
                
    #         result = await session.call_tool("create_entities", {
    #             "name": f"Chat Session {idx}",
    #             "episode_body": formatted_chat,
    #             "source": "message",
    #             "source_description": f"Chat session {idx} log.",
    #             "group_id": "agent_session"
    #         })
            
    #         print(f"Added chat session {idx} to server memory.")
            
    #         # Wait so that the episode are processed
    #         await asyncio.sleep(10)
    #     return
    
    
    async def run(self, task: str) -> str:
        """
        Executes the given question answering task using chat logs and ReAct framework.

        Args:
            task: The question to be answered
            context: Dictionary containing:
                - chat_logs: List of conversation messages
                - metadata: Optional metadata about the chat (e.g., timestamps, participants)
        """
        print(f"--- Starting Chat Agent ---")
        print(f"Question: {task}")

        # # Only need memory server for chat analysis
        # SERVER_PARAMS_MEM = StdioServerParameters(
        #     command=os.path.expanduser("~/.local/bin/uv"),
        #     args=[
        #         "run",
        #         "--directory", str(Path(__file__).parent.parent.parent / "graphiti" / "mcp_server"),
        #         "graphiti_mcp_server.py",
        #         "--transport", "stdio",
        #         "--group-id", "agent_session"
        #     ],
        #     env={
        #         "NEO4J_URI": os.environ.get("NEO4J_URI", "neo4j://127.0.0.1:7687"),
        #         "NEO4J_USER": os.environ.get("NEO4J_USER", "neo4j"), 
        #         "NEO4J_PASSWORD": os.environ.get("NEO4J_PASSWORD", "demodemo"),
        #         "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
        #     }
        # )
        SERVER_PARAMS_MEM = StdioServerParameters(
          command="npx",
          args=[
            "-y",
            "@modelcontextprotocol/server-memory"
          ]
        )
                
        actions = Actions(self.dir_name)
        tool_list = []

        # Initialize memory server and tools
        print("Initializing memory tools...")
        async with stdio_client(SERVER_PARAMS_MEM) as (read_1, write_1):
            async with ClientSession(read_1, write_1) as session_1:
                await session_1.initialize()
                
                # # Clear the graphiti database
                # print("Clearing graphiti database...")
                # result = await session_1.call_tool("clear_graph")
                # print(f"MPC Message: {result}")
                
                # Load each session one by one from the env file
                print("Loading chat logs into memory...")
                chat_sessions = []
                for session_file in self.dir_name.glob("chat_logs/session_*.json"): 
                    with open(session_file, "r") as f:
                        chat_sessions.append(json.load(f))
                await load_chat_sessions_into_server_memory(session_1, chat_sessions)

                # Get available tools after loading data
                tools_1 = await session_1.list_tools()
                print(f"Tools: {len(tools_1.tools)}")
                
                for tool in tools_1.tools:
                    dspy_tool = dspy.Tool.from_mcp_tool(session_1, tool)
                    print(f"Creating tool: {tool.name}")
                    print(f"  MCP tool: {tool}")
                    print(f"  DSPy tool: {dspy_tool}")
                    print(f"  DSPy tool name: {dspy_tool.name}")
                    print(f"  DSPy tool desc: {dspy_tool.desc}")
                    print(f"  DSPy tool args: {dspy_tool.args}")
                    tool_list.append(dspy_tool)
                print(f"  Loaded {len(tools_1.tools)} memory tools.")
                print(f"  Tool names: {[tool.name for tool in tool_list]}")
                
                # Print detailed tool information for debugging
                print("\nDetailed tool information:")
                for i, tool in enumerate(tool_list):
                    print(f"  {i+1}. {tool.name}")
                    print(f"     Description: {tool.desc}")
                    print(f"     Args: {tool.args}")
                    print()

                # Configure and run the ReAct agent
                print("\nConfiguring ReAct agent...")
                
                # Create a custom signature with explicit memory search instructions
                class AnswerQuestionWithMemory(dspy.Signature):
                    """Answer the given question using the provided chat logs by first searching memory for relevant information.
                    
                    WORKFLOW:
                    1. FIRST: Use search_memory_nodes to find relevant chat messages and information related to the question
                    2. SECOND: Use search_memory_facts to find any relevant facts or relationships
                    3. THIRD: Analyze the search results to understand the context
                    4. FOURTH: Provide your final answer based on the information found in memory
                    
                    You MUST search memory before providing any answer. Do not skip the search steps."""

                    task: str = dspy.InputField(
                        description="The question we are trying to answer"
                    )
                    answer: str = dspy.OutputField(
                        description="The final answer to the question based on information found in memory"
                    )
                    reasoning: str = dspy.OutputField(
                        description="Step-by-step reasoning including relevant chat messages and memory searches used"
                    )
                
                react = ReAct(AnswerQuestionWithMemory, tools=tool_list, strict_iters=None, max_iters=10)

                print("Running ReAct agent...")
                result = await react.acall(task=task)

                print("\n--- Agent Result ---")
                print(result)
                print("--- End Agent Result ---")
                
                # Print detailed trajectory for debugging
                if hasattr(result, 'trajectory'):
                    print("\n--- Agent Trajectory ---")
                    for key, value in result.trajectory.items():
                        print(f"{key}: {value}")
                    print("--- End Trajectory ---")
                return result

@agent_main
async def main(r: Run):
    # Normal agent run
    print(f"Chat MCP agent processing question:")
    task = r.task.task
    dir_name = Path(r.dir_name).resolve()
    
    # TODO ADD THE CURRENT DATES INTO THE CONTEXT!
    agent = QAAgent(dir_name=dir_name)
    result = await agent.run(task=task)
    
    # Convert usage object to dict to avoid JSON serialization issues
    usage_data = lm.history[-1]["usage"]
    if hasattr(usage_data, 'model_dump'):
        # If it's a Pydantic model, use model_dump
        usage_dict = usage_data.model_dump()
    elif hasattr(usage_data, '__dict__'):
        # If it has __dict__, convert to dict
        usage_dict = dict(usage_data.__dict__)
    else:
        # Fallback: try to convert directly
        usage_dict = dict(usage_data) if usage_data else {}
    
    formatted_answer = {"question_id": r.task.task_id, 
                        "answer": result.answer, 
                        "cost": lm.history[-1]["cost"], 
                        "usage": usage_dict
                    }
    
    # Write answer to hypothesis.json
    hypothesis_path = dir_name / "hypothesis.json"
    with open(hypothesis_path, "w") as f:
        json.dump(formatted_answer, f)
    
    return AgentResult(completed=True, result=result.answer)

async def test_qa_agent(task_file, agent_name):
    # Path relative to gym directory
    task = json_to_task(task_file)
    
    # write chat sessions into directory
    chat_log_dir = Path("envs") / task.dir_name / "chat_logs"
    chat_log_dir.mkdir(parents=True, exist_ok=True)
    
    task_dict = json.load(open(task_file))
    for idx, session in enumerate(task_dict[0]['sessions']):
        chatlog_path = chat_log_dir / f"session_{idx}.json"
        with open(chatlog_path, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2) 

    run = Run(
        task=task,
        agent_name=agent_name,
        task_file=str(Path("envs") / task_file),
        run_dir=str(Path("envs") / task.dir_name),
        dir_name=str(Path("envs") / task.dir_name)
    )
    
    # Run the agent
    result = await main(run)
    print("\nTest Result:")
    print(f"Completed: {result.completed}")
    print(f"Answer: {result.result}")
    task_dict = json.load(open(task_file))
    print(f"Actual answer: {task_dict[0]['answer']}")
    print(f"Cost and usage: {get_cost_from_history(lm.history)}")

async def evaluate_agent(task_file, agent_name):       
    # Load the task file
    task = json_to_task(task_file)
    
    run = Run(
        task=task, # not sure why task and task_file are both needed
        agent_name="test_agent",
        task_file=task_file,
        run_dir=str(Path("envs") / task.dir_name),
        dir_name=str(Path("envs") / task.dir_name) # this part is redundant
    )
    result = eval_qa(run)
    print(f"Result: {result}")
    return result

# Test section
if __name__ == "__main__":
    import asyncio
    import json
    import os
    import sys
    from pathlib import Path
    
    # Add the gym directory to Python path
    gym_dir = Path(__file__).parent.parent.parent
    sys.path.append(str(gym_dir))
    
    from helpers.models import Task, Run
    
    task_file = str(gym_dir / "tasks/longmemeval/longmemeval_10.json")
    agent_name = "test_agent"
    
    task_files = [str(gym_dir / "tasks/longmemeval/longmemeval_10.json")] # add all task files you want to run
    # # Run the test
    for task_file in task_files:
        asyncio.run(test_qa_agent(task_file, agent_name))
    
    # # Run the evaluation
    # for task_file in task_files:
    #     asyncio.run(evaluate_agent(task_file, agent_name))

    # # Summarize the results
    # total_score = 0
    # for task_file in task_files:
    #     task = json_to_task(task_file)
    #     result_path = "envs" / Path(task.dir_name) / "result.json"
    #     result = json.load(result_path.open())
    #     score = result['passed'] == True
    #     total_score += score
    # print(f"Average score: {total_score / len(task_files)}")