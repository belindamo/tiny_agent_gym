from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from helpers.models import Run, AgentResult, agent_main
from helpers.ai import dspy, lm
from .react import ReAct
from .actions import Actions
from pathlib import Path

class ReactAgent:
  
    def __init__(self, dir_name):
        self.dir_name = dir_name
        
    async def run(self, task: str) -> str:
        """
        Executes the given task using the configured tools and ReAct framework.

        Args:
            task: The description of the task to be solved.
        """

        SERVER_PARAMS_FS =  StdioServerParameters(
            command="npx",
            args=[
              "-y",
              "@modelcontextprotocol/server-filesystem",
              str(self.dir_name)
            ]
          )

        # MCP BUILT-IN MEMORY
        SERVER_PARAMS_MEM = StdioServerParameters(
          command="npx",
          args=[
            "-y",
            "@modelcontextprotocol/server-memory"
          ]
        )

                
        class ExecuteExperiment(dspy.Signature):
          """Execute this experiment based on the conditions provided."""

          task: str = dspy.InputField(
              description="The problem we are trying to solve with this experiment"
          )
          completed: bool = dspy.OutputField(
              description="Whether the experiment was completed"
          )
          result: str = dspy.OutputField(description="The result of the experiment")
          
        actions = Actions(self.dir_name)
        dspy_tools = [actions.run_terminal_command]

        # Initialize filesystem server and tools
        print("Initializing filesystem tools...")
        async with stdio_client(SERVER_PARAMS_FS) as (read_0, write_0):
            async with ClientSession(read_0, write_0) as session_0:
                await session_0.initialize()
                tools_0 = await session_0.list_tools()
                for tool in tools_0.tools:
                    dspy_tools.append(dspy.Tool.from_mcp_tool(session_0, tool))
                print(f"  Loaded {len(tools_0.tools)} filesystem tools.")

                # Initialize memory server and tools
                print("Initializing memory tools...")
                async with stdio_client(SERVER_PARAMS_MEM) as (read_1, write_1):
                    async with ClientSession(read_1, write_1) as session_1:
                        await session_1.initialize()
                        tools_1 = await session_1.list_tools()
                        for tool in tools_1.tools:
                            dspy_tools.append(dspy.Tool.from_mcp_tool(session_1, tool))
                        print(f"  Loaded {len(tools_1.tools)} memory tools.")

                        print(f"\nTotal tools available: {len(dspy_tools)}")

                        # Configure and run the ReAct agent
                        print("\nConfiguring ReAct agent...")
                        react = ReAct(ExecuteExperiment, tools=dspy_tools)

                        print("Running ReAct agent...")
                        result = await react.acall(task=task)

                        print("\n--- Agent Result ---")
                        print(result)
                        print("--- End Agent Result ---")
                        return result

@agent_main
async def main(r: Run):
  try:
    print(f"React MCP agent processing task: {r.task.task}")
    task = r.task.task
    dir_name = Path(r.dir_name).resolve()
    
    agent = ReactAgent(dir_name=dir_name)
    result = await agent.run(task=task)
    
    input_tokens = sum([x.get('usage', {}).get('prompt_tokens', 0) for x in lm.history])
    output_tokens = sum([x.get('usage', {}).get('completion_tokens', 0) for x in lm.history])
    cost = sum([x.get('cost', 0) for x in lm.history])
    
    return AgentResult(
      completed=result['completed'], 
      result=result['result'], 
      reasoning=result['reasoning'], 
      input_tokens=input_tokens if input_tokens else None,
      output_tokens=output_tokens if output_tokens else None, 
      cost=cost if cost else None
    )
  
  except Exception as e:
    print(f"Error in agent: {str(e)}")
    return AgentResult(completed=False, result=f"Error: {str(e)}", reasoning="Error in agent", input_tokens=0, output_tokens=0)
    