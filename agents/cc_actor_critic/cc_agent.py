"""
Claude Code Python SDK: https://docs.anthropic.com/en/docs/claude-code/sdk/sdk-python
Actor-Critic System Implementation
"""

import asyncio
from typing import List, Dict, Any
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from run_prompts import prompt_for_actor, prompt_for_critic

async def collect_response(client: ClaudeSDKClient) -> Dict[str, Any]:
    """Collect the full response from a Claude client."""
    response_text = []
    result_info = {}
    
    async for message in client.receive_response():
        if hasattr(message, 'content'):
            for block in message.content:
                if hasattr(block, 'text'):  # Text Block
                    response_text.append(block.text)
                    print(block.text, end='', flush=True)
                elif hasattr(block, 'thinking'):  # Thinking Block
                    print(f"[THINKING: {block.signature}]", flush=True)
                elif hasattr(block, 'input'):  # Tool Call
                    print(f"[TOOL: {block.name}]", flush=True)
                elif hasattr(block, 'content'):  # Tool Call Result
                    if block.is_error:
                        print(f"[ERROR: {block.content}]", flush=True)
        elif hasattr(message, 'total_cost_usd'):
            # Capture result message details
            result_info = {
                'duration_ms': message.duration_ms,
                'duration_api_ms': message.duration_api_ms,
                'is_error': message.is_error,
                'num_turns': message.num_turns,
                'session_id': message.session_id,
                'total_cost_usd': message.total_cost_usd,
                'usage': message.usage,
                'result': message.result
            }
    
    return {
        'text': ''.join(response_text),
        'result_info': result_info
    }

async def run_actor_critic_system(env: str, proposal: str, num_rounds: int = 3, max_turns_per_agent: int = 10):
    """
    Run an actor-critic system where agents alternate for multiple rounds.
    
    Args:
        env: Working directory for the agents
        proposal: Research proposal to work on
        num_rounds: Number of actor-critic rounds to run
        max_turns_per_agent: Maximum turns per agent per round
    """
    
    # Common tool configuration
    common_tools = [
        "Edit",
        "MultiEdit", 
        "Glob",
        "Grep",
        "LS",
        "Read",
        "Write",
        "Task",
        "Bash(git add:*)",
        "Bash(git commit:*)",
        "Bash(git push:*)",
        "Bash(git status:*)",
        "Bash(git diff:*)",
        "Bash(git log:*)",
        "Bash(git rm:*)",
        "mcp__search__web_search_exa"
    ]
    
    # MCP server configuration
    mcp_config = {
        "search": {
            "command": "npx",
            "args": ["-y", "mcp-remote", "https://mcp.exa.ai/mcp?exaApiKey=8b0e6b45-e064-4428-a0bf-1fa31d0e8ac6"]
        }
    }
    
    # Track conversation history
    conversation_history = []
    total_cost = 0.0
    
    print("=" * 80)
    print(f"🎭 STARTING ACTOR-CRITIC SYSTEM ({num_rounds} rounds)")
    print("=" * 80)
    
    for round_num in range(1, num_rounds + 1):
        print(f"\n{'='*20} ROUND {round_num}/{num_rounds} {'='*20}")
        
        # ACTOR PHASE
        print(f"\n🎯 ACTOR PHASE (Round {round_num})")
        print("-" * 50)
        
        async with ClaudeSDKClient(
            options=ClaudeCodeOptions(
                system_prompt=prompt_for_actor(proposal),
                allowed_tools=common_tools,
                cwd=env,
                max_turns=max_turns_per_agent,
                mcp_servers=mcp_config,
                permission_mode="acceptEdits",
                permission_prompt_tool_name="mcp__approval_tool"
            )
        ) as actor_client:
            
            # Prepare actor's task based on round
            if round_num == 1:
                actor_task = f"Begin implementing the research proposal. Work systematically and document your progress."
            else:
                # Include previous critic feedback
                last_critic_feedback = conversation_history[-1]['text'] if conversation_history else ""
                actor_task = f"""Continue working on the research proposal, addressing the professor's feedback from the previous round:

PROFESSOR'S FEEDBACK:
{last_critic_feedback}

Please address their concerns and continue with the implementation."""
            
            await actor_client.query(actor_task)
            actor_response = await collect_response(actor_client)
            
            conversation_history.append({
                'round': round_num,
                'agent': 'actor',
                'text': actor_response['text'],
                'result_info': actor_response['result_info']
            })
            
            total_cost += actor_response['result_info'].get('total_cost_usd', 0)
            
            print(f"\n💰 Actor cost this round: ${actor_response['result_info'].get('total_cost_usd', 0):.4f}")
        
        # CRITIC PHASE  
        print(f"\n🎓 CRITIC PHASE (Round {round_num})")
        print("-" * 50)
        
        async with ClaudeSDKClient(
            options=ClaudeCodeOptions(
                system_prompt=prompt_for_critic(proposal),
                allowed_tools=common_tools,
                cwd=env,
                max_turns=max_turns_per_agent,
                mcp_servers=mcp_config
            )
        ) as critic_client:
            
            # Prepare critic's task with actor's work
            actor_work = actor_response['text']
            critic_task = f"""Review the graduate student's work from this round and provide detailed feedback:

STUDENT'S WORK THIS ROUND:
{actor_work}

Please evaluate their progress, identify any issues, and provide constructive feedback for the next round."""
            
            await critic_client.query(critic_task)
            critic_response = await collect_response(critic_client)
            
            conversation_history.append({
                'round': round_num,
                'agent': 'critic', 
                'text': critic_response['text'],
                'result_info': critic_response['result_info']
            })
            
            total_cost += critic_response['result_info'].get('total_cost_usd', 0)
            
            print(f"\n💰 Critic cost this round: ${critic_response['result_info'].get('total_cost_usd', 0):.4f}")
        
        print(f"\n📊 Round {round_num} Summary:")
        print(f"   Total cost this round: ${(actor_response['result_info'].get('total_cost_usd', 0) + critic_response['result_info'].get('total_cost_usd', 0)):.4f}")
        print(f"   Cumulative cost: ${total_cost:.4f}")
    
    print("\n" + "=" * 80)
    print("🏁 ACTOR-CRITIC SYSTEM COMPLETE")
    print("=" * 80)
    print(f"💰 Total cost: ${total_cost:.4f}")
    print(f"🔄 Completed {num_rounds} rounds")
    print(f"💬 Total interactions: {len(conversation_history)}")
    
    return {
        'conversation_history': conversation_history,
        'total_cost': total_cost,
        'num_rounds': num_rounds
    }

# Legacy function for backwards compatibility
async def run_cc_agent(env: str, task: str, system_prompt="You are a scientific research assistant"):
    """Legacy single-agent function - redirects to actor-critic system."""
    print("⚠️  Using legacy function - consider using run_actor_critic_system() directly")
    return await run_actor_critic_system(env, task, num_rounds=1)

if __name__ == "__main__":
    # Example usage of the actor-critic system
    research_proposal = """
<research concept>
**Question 1:** Which memory tools perform best across agentic tasks?

**Subquestion 1:** Can knowledge graph-based memory systems perform better for “agentic-tasks”?

* How it is answered: Integrate a KG tool into an agent.

**Subquestion 2:** Do methods that perform well in long-term memory evaluation perform well for “agentic-tasks”?

* How it is answered: Compare vanilla agent vs agent w/ LME retrieval tool on LME+ & LME

**Subquestion 3:** How do different memory tool approaches affect long vs. shorter-horizon tasks

* How it is answered: measure difference in agent + memory tool performance across similar tasks with differing horizons, e.g. BrowserComp.

### Experiment:

We have selected several recently released memory systems. For needle-in-the-haystack evaluation, we use LongMemEval \[Wu et al, 2025], a standard benchmark for memory system assessment. We define "agentic tasks" as multi-step planning scenarios where agents must use tools to interact with their environment. For this evaluation, we use BrowserComp \[Wei et al, 2025], categorizing tasks by planning horizon length to assess memory system effectiveness across different complexity levels.
</research concept>

<implementation>
Prior work on building an agent memory system has focused on tasks of document retrieval or chat dialogue. These tasks can be characterized by "needle-in-the-haystack", where the system must retrieve a small amount of important text in a sea of information. However, it is unclear if memory systems designed for information retrieval can effectively support more complex tasks that require strategic planning and multi-step decision-making. In this work, we aim to understand if SOTA memory systems perform as well in agentic tasks as they do in needle-in-the-haystack tasks, particularly whether these methods can improve performance in tasks requiring long-horizon planning.

**Question 1:** Which memory tools perform best across agentic tasks? 

**Subquestion:** Can knowledge graph-based memory systems perform better for “agentic-tasks”?

- How it is answered: Integrate a KG tool into an agent.

**Subquestion 2:** Do methods that perform well in long-term memory evaluation perform well for “agentic-tasks”?

- How it is answered: Compare vanilla agent vs agent w/ LME retrieval tool on LME+ & LME

**Subquestion 3:** How do different memory tool approaches affect long vs. shorter-horizon tasks

- How it is answered: measure difference in agent + memory tool performance across similar tasks with differing horizons, e.g. BrowserComp.

### Experiment:

We have selected several recently released memory systems. For needle-in-the-haystack evaluation, we use LongMemEval [Wu et al, 2025], a standard benchmark for memory system assessment. We define "agentic tasks" as multi-step planning scenarios where agents must use tools to interact with their environment. For this evaluation, we use BrowserComp [Wei et al, 2025], categorizing tasks by planning horizon length to assess memory system effectiveness across different complexity levels.

**Benchmarks:**

- Chat task:
    - Why: QA is the current main style of benchmark for long-term memory of LLMs. We run this to establish
    - LongMemEval (LME)
    - LongMemEval+ (LME+) - Modified LongMemEval, where the chatlogs are dumped into the filesystem. This forces the agent to retrieve the relevant chat logs from the file system. @Ruhana Azam
- ~~“Agentic” task with short, med, long horizon:~~
    - ~~BrowserComp~~

**Agent(s):**

- Tool:
    - Memory Editing: @Belinda Mo
        - Control: no memory tool
        - System 1 : LME retrieval
        - System 2: GraphRAG mcp
        - System 3: [KGMem mcp](https://github.com/belindamo/kg_mem)
        - System 4: [built-in memory mcp](https://github.com/modelcontextprotocol/servers/tree/main/src/memory)
    - If BrowserComp:
        - web search
        - web browser
    - If LongMemEval
        - filesystem CRED

**Metric(s):**

- success rate
- token count
- cost
- tool calls
    - per tool
- api calls
- time

**Base LLMs:**

- Private
    - gpt-5?
    - claude 4?
    - gpt-4o-mini
    - Gemini 2.5 pro
- Open-source
    - gpt-oss:120b
    - qwen

### Estimated Costs & Resources

- [TODO]

### Timeline & Goals:

- September 19, 2025: ICLR Abstract (https://iclr.cc/Conferences/2026/CallForPapers)
- September 24, 2025:
    - ICLR Main Conference Submission
    - Archive submitted manuscript

## Next Steps:

- Move LongMemEval benchmark & evaluation (from ai-scientist-sym) to new repo (Ruhana)
    - https://github.com/belindamo/memory-systems-in-action
- Get the baseline LongMemEval agent working on LMRE (Ruhana)
- Get memory tools set up (do LME last)  (Belinda)
- Work on proposal writeup (For Sanmi)
    - Write more in detail the motivation to each subquestion.
    - Background information on each of the chosen memory systems.
- Later:
    - Pair on writing an agent for LME+

---

# Appendix

### Our Agent Pipeline

- Following ReAct, at each step, the agent is given an observation, then reasons, and proposed an action.
- Action Space:
    - CRUD (For interacting with the file system)
    - Memory Related:
        - Indexing
        - Updating
        - Retrieving
- Observation Space:
    - Chat history

## Benchmark Description

### LongMemEval

This benchmark was released in order to test long-term memory of a chat-assistants. To test vary levels of difficulty, three benchmarks, each with 500 tasks, were release:

- `LongMemEval_S`: For each tasks, ~40 sessions are given to the agent.  Total token count is  ~115k tokens per task.
- `LongMemEval_M`: For each tasks, ~500 chat session are given to the agent. Accessing up to  ~1.5 million tokens per task.
- `LongMemEval_Oracle`: Unlike the above benchmarks, these tasks are given only relevant chat-sessions are provided to the agent. [Unclear what the average number of tokens and chat-session are per task]

Below are examples of the seven different task types proposed in the LongMemEval:

![image.png](attachment:b54d5ed9-0fb8-40af-bf5d-f5d2ad2fd83c:image.png)

[Image from Wu et al 2025]

Summarize baseline method and results: 

- TODO

### LongMemEval+

[TODO]

# References

- Wu et al 2025, LongMemEval, https://arxiv.org/pdf/2410.10813, https://github.com/xiaowu0162/LongMemEval
</implementation<

    """
    
    asyncio.run(run_actor_critic_system(
        env="/Users/bmo/deliverables/tiny_agent_gym/envs/memory-systems-in-action",
        proposal=research_proposal,
        num_rounds=3,  # Run 3 rounds of actor-critic interaction
        max_turns_per_agent=10  # Max 10 turns per agent per round
    ))