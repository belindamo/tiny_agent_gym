"""
Claude Code Python SDK: https://docs.anthropic.com/en/docs/claude-code/sdk/sdk-python
Multi-Agent System Implementation with Actor and Multiple Critics
"""

import asyncio
import json
import subprocess
import ast
import os
import re
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions
from .run_prompts import (
    prompt_for_actor, 
    prompt_for_implementation_critic,
    prompt_for_experiment_params_critic,
    prompt_for_metrics_critic
)


def parse_critic_xml_response(response_text: str, critic_name: str) -> tuple[bool, str]:
    """
    Parse XML response from AI critic to extract pass/fail status and feedback.
    
    Expected format:
    <feedback>Detailed explanation of what was checked...</feedback>
    <passed>True</passed>
    
    Returns:
        tuple[bool, str]: (passed, feedback)
    """
    try:
        # Find the XML content in the response using regex
        feedback_match = re.search(r'<feedback>(.*?)</feedback>', response_text, re.DOTALL | re.IGNORECASE)
        passed_match = re.search(r'<passed>(.*?)</passed>', response_text, re.DOTALL | re.IGNORECASE)
        
        if not feedback_match or not passed_match:
            print(f"⚠️ {critic_name}: Could not find XML tags in response")
            print(f"   Response preview: {response_text[:300]}...")
            return False, f"XML parsing failed for {critic_name}. Could not find <feedback> and <passed> tags."
        
        feedback = feedback_match.group(1).strip()
        passed_str = passed_match.group(1).strip().lower()
        
        # Parse the boolean
        passed = passed_str in ['true', '1', 'yes', 'pass']
        
        print(f"   🔍 {critic_name}: Parsed passed={passed}")
        return passed, feedback
        
    except Exception as e:
        print(f"⚠️ {critic_name}: XML parsing error: {e}")
        return False, f"XML parsing error for {critic_name}: {str(e)}"


@dataclass
class CriticResult:
    """Result from a critic evaluation"""
    passed: bool
    critic_name: str
    feedback: str
    details: Dict[str, Any] = None


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
                    print(f"[THINKING: {block.signature}] {block.thinking[:100]}...", flush=True)
                elif hasattr(block, 'input'):  # Tool Call
                    print(f"[TOOL: {block.name}] Input: {str(block.input)[:200]}...", flush=True)
                elif hasattr(block, 'content'):  # Tool Call Result
                    if block.is_error:
                        print(f"[ERROR: {block.content}]", flush=True)
                    else:
                        print(f"[TOOL RESULT: {str(block.content)[:200]}...]", flush=True)
                else:
                    print(f"[UNKNOWN BLOCK TYPE: {type(block)}]", flush=True)
        elif hasattr(message, 'total_cost_usd'):
            # Capture result message details
            print(f"[COST: ${message.total_cost_usd:.4f}]", flush=True)
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


def find_experiment_dir(env: str) -> Optional[Tuple[str, str]]:
    """Find the experiment directory and read the proposal from plan.md
    
    Returns:
        Tuple of (experiment_path, proposal_text) or None if not found
    """
    experiments_path = Path(env) / "experiments"
    
    if not experiments_path.exists():
        return None
        
    # Look for experiment directories (excluding README.md files)
    for item in experiments_path.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            plan_file = item / "plan.md"
            if plan_file.exists():
                try:
                    proposal = plan_file.read_text()
                    # Extract the actual proposal content (not the template)
                    # Look for filled content between the template markers
                    if "[" not in proposal or len(proposal) > 1000:  # Heuristic: filled templates are longer
                        return str(item), proposal
                except Exception as e:
                    print(f"Error reading {plan_file}: {e}")
                    
    return None


def get_code_dir(experiment_path: str) -> str:
    """Get the code directory path for an experiment"""
    return os.path.join(experiment_path, "code")


def save_experiment_results(experiment_path: str, summary: Dict[str, Any]) -> None:
    """Save experiment results to results folder and update results.md"""
    from datetime import datetime
    
    # Create results directory if it doesn't exist
    results_dir = os.path.join(experiment_path, "results")
    os.makedirs(results_dir, exist_ok=True)
    
    # Generate timestamp for unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save detailed JSON summary
    json_file = os.path.join(results_dir, f"multiagent_summary_{timestamp}.json")
    with open(json_file, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    print(f"💾 Saved detailed results to: {json_file}")
    
    # Update results.md
    results_md_path = os.path.join(experiment_path, "results.md")
    
    # Generate markdown summary
    md_content = generate_results_markdown(summary, timestamp)
    
    # Read existing results.md if it exists
    existing_content = ""
    if os.path.exists(results_md_path):
        with open(results_md_path, 'r') as f:
            existing_content = f.read()
    
    # Append new results or create new file
    if "# Results" in existing_content:
        # Append to existing file
        with open(results_md_path, 'a') as f:
            f.write("\n\n" + md_content)
    else:
        # Create new file
        with open(results_md_path, 'w') as f:
            f.write("# Results\n\n" + md_content)
    
    print(f"📝 Updated results summary in: {results_md_path}")


def generate_results_markdown(summary: Dict[str, Any], timestamp: str) -> str:
    """Generate markdown content for results summary"""
    status_emoji = "✅" if summary['final_status'] == 'complete' else "❌"
    
    md = f"""## Multi-Agent Run - {timestamp}

**Status:** {status_emoji} {summary['final_status'].title()}  
**Actor Runs Used:** {summary['actor_runs_used']}  
**Total Cost:** ${summary['total_cost']:.4f}  

### Critic Results
"""
    
    # Use final_critic_results instead of attempts
    if summary.get('final_critic_results'):
        for critic_result in summary['final_critic_results']:
            status_icon = "✅" if critic_result['passed'] else "❌"
            md += f"- {status_icon} **{critic_result['critic_name']}**: {critic_result['passed']}\n"
    
    # Add summary of what was accomplished
    if summary['final_status'] == 'complete':
        md += "\n### Summary\nAll critics passed successfully. Implementation is complete and meets all requirements.\n"
    else:
        md += "\n### Summary\nSome critics failed. Implementation needs further work to meet all requirements.\n"
    
    # Add conversation history summary
    if summary.get('conversation_history'):
        md += f"\n### Conversation Flow\n"
        md += f"Total phases: {len(summary['conversation_history'])}\n"
    
    # Add link to detailed JSON
    md += f"\n**Detailed Results:** `results/multiagent_summary_{timestamp}.json`\n"
    
    return md


class CodeCompilationCritic:
    """Critic that checks if Python code compiles (no AI)"""
    
    def __init__(self, env: str, code_dir: Optional[str] = None):
        self.env = env
        self.code_dir = code_dir or env
        
    async def evaluate(self, actor_work: str) -> CriticResult:
        """Check all Python files for syntax errors"""
        print("\n🔧 CODE COMPILATION CRITIC")
        print("-" * 50)
        
        errors = []
        files_checked = 0
        
        # Find all Python files in the code directory
        for root, dirs, files in os.walk(self.code_dir):
            # Skip hidden directories and __pycache__
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if file.endswith('.py'):
                    filepath = os.path.join(root, file)
                    files_checked += 1
                    
                    try:
                        with open(filepath, 'r') as f:
                            content = f.read()
                        
                        # Try to compile the code
                        compile(content, filepath, 'exec')
                        print(f"✓ {filepath} - OK")
                        
                    except SyntaxError as e:
                        error_msg = f"Syntax error in {filepath}: Line {e.lineno} - {e.msg}"
                        errors.append(error_msg)
                        print(f"✗ {filepath} - SYNTAX ERROR: Line {e.lineno}")
                        
                    except Exception as e:
                        error_msg = f"Error checking {filepath}: {str(e)}"
                        errors.append(error_msg)
                        print(f"✗ {filepath} - ERROR: {str(e)}")
        
        if errors:
            feedback = f"Found {len(errors)} compilation errors:\n" + "\n".join(errors)
            passed = False
        else:
            feedback = f"All {files_checked} Python files compile successfully."
            passed = True
            
        return CriticResult(
            passed=passed,
            critic_name="Code Compilation",
            feedback=feedback,
            details={"files_checked": files_checked, "errors": errors}
        )


class TestRunnerCritic:
    """Critic that runs test files and checks if they pass (no AI)"""
    
    def __init__(self, env: str, code_dir: Optional[str] = None):
        self.env = env
        self.code_dir = code_dir or env
        
    async def evaluate(self, actor_work: str) -> CriticResult:
        """Run all test files and check results"""
        print("\n🧪 TEST RUNNER CRITIC")
        print("-" * 50)
        
        test_results = []
        tests_passed = 0
        tests_failed = 0
        
        # Find all test files
        test_files = []
        for root, dirs, files in os.walk(self.code_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    test_files.append(os.path.join(root, file))
        
        if not test_files:
            return CriticResult(
                passed=True,
                critic_name="Test Runner",
                feedback="No test files found. Consider adding tests for your implementation.",
                details={"test_files": [], "total_tests": 0}
            )
        
        # Run each test file
        for test_file in test_files:
            try:
                # Try pytest first
                result = subprocess.run(
                    ['python', '-m', 'pytest', test_file, '-v'],
                    cwd=self.code_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    tests_passed += 1
                    test_results.append(f"✓ {test_file} - PASSED")
                    print(f"✓ {test_file} - PASSED")
                else:
                    # If pytest fails, try simple python import test
                    try:
                        import_result = subprocess.run(
                            ['python', '-c', f'import sys; sys.path.append("{self.code_dir}"); exec(open("{test_file}").read())'],
                            cwd=self.code_dir,
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        if import_result.returncode == 0:
                            tests_passed += 1
                            test_results.append(f"✓ {test_file} - PASSED (fallback)")
                            print(f"✓ {test_file} - PASSED (fallback)")
                        else:
                            tests_failed += 1
                            test_results.append(f"✗ {test_file} - FAILED")
                            test_results.append(f"  Pytest Error: {result.stderr}")
                            test_results.append(f"  Import Error: {import_result.stderr}")
                            print(f"✗ {test_file} - FAILED")
                    except:
                        tests_failed += 1
                        test_results.append(f"✗ {test_file} - FAILED")
                        test_results.append(f"  Error: {result.stderr}")
                        print(f"✗ {test_file} - FAILED")
                    
            except subprocess.TimeoutExpired:
                tests_failed += 1
                test_results.append(f"✗ {test_file} - TIMEOUT")
                print(f"✗ {test_file} - TIMEOUT")
                
            except Exception as e:
                tests_failed += 1
                test_results.append(f"✗ {test_file} - ERROR: {str(e)}")
                print(f"✗ {test_file} - ERROR")
        
        passed = tests_failed == 0
        feedback = f"Tests: {tests_passed} passed, {tests_failed} failed out of {len(test_files)} test files.\n"
        feedback += "\n".join(test_results)
        
        return CriticResult(
            passed=passed,
            critic_name="Test Runner",
            feedback=feedback,
            details={
                "test_files": test_files,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed
            }
        )


class ImplementationCompletenessCritic:
    """AI-powered critic that checks if implementation is complete based on proposal"""
    
    def __init__(self, env: str, proposal: str, mcp_config: Dict, code_dir: Optional[str] = None):
        self.env = env
        self.proposal = proposal
        self.mcp_config = mcp_config
        self.code_dir = code_dir or env
        
    async def evaluate(self, actor_work: str) -> CriticResult:
        """Check if implementation covers all aspects of the proposal"""
        print("\n📋 IMPLEMENTATION COMPLETENESS CRITIC")
        print("-" * 50)
        
        async with ClaudeSDKClient(
            options=ClaudeCodeOptions(
                system_prompt=prompt_for_implementation_critic(self.proposal),
                allowed_tools=["Read", "LS", "Glob", "Grep"],
                cwd=self.code_dir,
                max_turns=100,
                mcp_servers=self.mcp_config
            )
        ) as critic_client:
            
            task = f"""Review implementation completeness based on the proposal.

Proposal: {self.proposal}

After your analysis, end with a final response in this format (so we may parse it):
<feedback>Your assessment here</feedback>
<passed>True</passed>
"""
            
            await critic_client.query(task)
            response = await collect_response(critic_client)
            
            # Use XML parsing instead of text analysis
            passed, feedback = parse_critic_xml_response(response['text'], "Implementation Completeness")
            
            return CriticResult(
                passed=passed,
                critic_name="Implementation Completeness",
                feedback=feedback,
                details={"cost": response['result_info'].get('total_cost_usd', 0)}
            )


class ExperimentParametersCritic:
    """AI-powered critic that checks experiment parameters and environment variables"""
    
    def __init__(self, env: str, proposal: str, mcp_config: Dict, code_dir: Optional[str] = None):
        self.env = env
        self.proposal = proposal
        self.mcp_config = mcp_config
        self.code_dir = code_dir or env
        
    async def evaluate(self, actor_work: str) -> CriticResult:
        """Check experiment parameters and configuration"""
        print("\n⚙️ EXPERIMENT PARAMETERS CRITIC")
        print("-" * 50)
        
        async with ClaudeSDKClient(
            options=ClaudeCodeOptions(
                system_prompt=prompt_for_experiment_params_critic(self.proposal),
                allowed_tools=["Read", "LS", "Glob", "Grep"],
                cwd=self.code_dir,
                max_turns=10,
                mcp_servers=self.mcp_config
            )
        ) as critic_client:
            
            task = f"""Review experiment configuration and parameters.

Proposal: {self.proposal}

After your analysis, end with a final response in this format (so we may parse it):
<feedback>Your assessment here</feedback>
<passed>True</passed>"""
            
            await critic_client.query(task)
            response = await collect_response(critic_client)
            
            # Use XML parsing instead of text analysis
            passed, feedback = parse_critic_xml_response(response['text'], "Experiment Parameters")
            
            return CriticResult(
                passed=passed,
                critic_name="Experiment Parameters",
                feedback=feedback,
                details={"cost": response['result_info'].get('total_cost_usd', 0)}
            )


class MetricsLoggingCritic:
    """AI-powered critic that checks metric and parameter logging"""
    
    def __init__(self, env: str, proposal: str, mcp_config: Dict, code_dir: Optional[str] = None):
        self.env = env
        self.proposal = proposal
        self.mcp_config = mcp_config
        self.code_dir = code_dir or env
        
    async def evaluate(self, actor_work: str) -> CriticResult:
        """Check metrics and logging implementation"""
        print("\n📊 METRICS & LOGGING CRITIC")
        print("-" * 50)
        
        async with ClaudeSDKClient(
            options=ClaudeCodeOptions(
                system_prompt=prompt_for_metrics_critic(self.proposal),
                allowed_tools=["Read", "LS", "Glob", "Grep"],
                cwd=self.code_dir,
                max_turns=10,
                mcp_servers=self.mcp_config
            )
        ) as critic_client:
            
            task = f"""Review metrics and logging implementation.

Proposal: {self.proposal}

After your analysis, end with a final response in this format (so we may parse it):
<feedback>Your assessment here</feedback>
<passed>True</passed>"""
            
            await critic_client.query(task)
            response = await collect_response(critic_client)
            
            # Use XML parsing instead of text analysis
            passed, feedback = parse_critic_xml_response(response['text'], "Metrics & Logging")
            
            return CriticResult(
                passed=passed,
                critic_name="Metrics & Logging",
                feedback=feedback,
                details={"cost": response['result_info'].get('total_cost_usd', 0)}
            )


async def fix_specific_critic_issue(env: str, code_dir: str, proposal: str, critic_name: str, critic_feedback: str, mcp_config: Dict, common_tools: List[str], claude_turns: int = 8) -> Dict[str, Any]:
    """
    Run actor to fix a specific critic's feedback in a targeted way.
    
    Args:
        env: Working directory for the agents
        code_dir: Code directory path
        proposal: Research proposal
        critic_name: Name of the failing critic
        critic_feedback: Specific feedback from the critic
        mcp_config: MCP server configuration
        common_tools: Available tools
        claude_turns: Maximum Claude SDK turns for this focused fix
    
    Returns:
        Actor response data
    """
    print(f"\n🔧 TARGETED FIX FOR {critic_name.upper()}")
    print("-" * 60)
    
    async with ClaudeSDKClient(
        options=ClaudeCodeOptions(
            system_prompt=prompt_for_actor(proposal),
            allowed_tools=common_tools,
            cwd=code_dir,
            max_turns=claude_turns,
            mcp_servers=mcp_config
        )
    ) as actor_client:
        
        targeted_task = f"""Fix the specific issue identified by the {critic_name} critic.

CRITIC FEEDBACK TO ADDRESS:
{critic_feedback}

Your job is to make targeted changes to address this specific critic's concerns. 
Be efficient and focused - just fix what the critic identified.

Focus on:
- Understanding what the critic wants
- Making the minimal necessary changes to satisfy this critic
- Testing your changes to ensure they work
- Being targeted in your implementation

COMMON FIXES FOR SPECIFIC CRITICS:
- Test Runner failures: Check imports, file paths, pytest compatibility, add fallback test execution
- Implementation Completeness: Ensure ALL proposal requirements are implemented
- Experiment Parameters: Create proper config files with all parameters documented
- Metrics & Logging: Implement structured logging with JSON format and timestamps

Build upon what already exists and fix the specific issues mentioned.
Be VERY specific in your fixes - don't just read files, actually IMPLEMENT the missing pieces."""
        
        await actor_client.query(targeted_task)
        response = await collect_response(actor_client)
        
        print(f"\n💰 Targeted fix cost: ${response['result_info'].get('total_cost_usd', 0):.4f}")
        return response


async def run_multi_agent_system(env: str, proposal: str, max_actor_runs: int = 8) -> Dict[str, Any]:
    """
    Run a multi-agent system where an actor must pass all critics before completing.
    
    Args:
        env: Working directory for the agents
        proposal: Research proposal to work on (or empty string to read from plan.md)
        max_actor_runs: Maximum number of individual actor sessions total
    
    Returns:
        Summary JSON with results
    """
    
    # Setup environment
    experiment_info = find_experiment_dir(env)
    code_dir = env
    
    if experiment_info:
        experiment_path, plan_proposal = experiment_info
        code_dir = get_code_dir(experiment_path)
        if not proposal:
            proposal = plan_proposal
            print(f"📄 Using proposal from {experiment_path}/plan.md")
        os.makedirs(code_dir, exist_ok=True)
        print(f"💾 Working in code directory: {code_dir}")
    
    # Configuration
    common_tools = [
        "Edit", "MultiEdit", "Glob", "Grep", "LS", "Read", "Write", "Task",
        "Bash(git add:*)", "Bash(git commit:*)", "Bash(git push:*)",
        "Bash(git status:*)", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git rm:*)",
        "Bash(pytest:*)", "Bash(python -m pytest:*)", "Bash(python test_*.py)",
        "Bash(pip install:*)", "Bash(pip list:*)", "Bash(python -m:*)",
    ]
    mcp_config = {}
    
    # Initialize critics
    critics = [
        CodeCompilationCritic(env, code_dir),
        TestRunnerCritic(env, code_dir),
        ImplementationCompletenessCritic(env, proposal, mcp_config, code_dir),
        # ExperimentParametersCritic(env, proposal, mcp_config, code_dir),
        # MetricsLoggingCritic(env, proposal, mcp_config, code_dir)
    ]
    
    # Initialize tracking
    summary = {
        "proposal": proposal,
        "total_cost": 0.0,
        "final_status": "incomplete",
        "actor_work": [],
        "critic_feedback": [],
        "targeted_fixes": [],
        "actor_runs_used": 0,
        "final_critic_results": [],
        "initial_critic_results": [],  # Pre-actor baseline
        "conversation_history": []     # Full conversation flow
    }
    
    print("=" * 80)
    print(f"🎭 STARTING MULTI-AGENT SYSTEM")
    print(f"📋 Proposal: {proposal[:100]}...")
    print(f"🔄 Max actor runs: {max_actor_runs}")
    print("=" * 80)
    
    # Initial critic evaluation BEFORE any actor work
    print(f"\n🔍 INITIAL CRITICS BASELINE (Pre-Actor)")
    print("-" * 50)
    print("Running critics to establish baseline state...")
    
    initial_failing = []
    for critic in critics:
        try:
            result = await critic.evaluate("")  # Empty work to check baseline
            
            if result.details and 'cost' in result.details:
                summary["total_cost"] += result.details['cost']
            
            summary["initial_critic_results"].append({
                "critic_name": result.critic_name,
                "passed": result.passed,
                "feedback": result.feedback[:200] + "..." if len(result.feedback) > 200 else result.feedback
            })
            
            if not result.passed:
                initial_failing.append(result.critic_name)
                print(f"✗ {result.critic_name} - {result.feedback[:100]}...")
            else:
                print(f"✓ {result.critic_name} - Already passing!")
                
        except Exception as e:
            print(f"⚠️ {critic.__class__.__name__} - Error: {str(e)}")
    
    print(f"\nBaseline: {len(initial_failing)} critics need implementation")
    summary["conversation_history"].append({
        "phase": "initial_baseline",
        "failing_critics": initial_failing
    })
    
    # Initial actor implementation
    print(f"\n🎯 INITIAL ACTOR PHASE")
    print("-" * 50)
    
    async with ClaudeSDKClient(
        options=ClaudeCodeOptions(
            system_prompt=prompt_for_actor(proposal),
            allowed_tools=common_tools,
            cwd=code_dir,
            max_turns=15,
            mcp_servers=mcp_config
        )
    ) as actor_client:
        
        initial_task = "Begin implementing the research proposal. Work systematically and document your progress."
        await actor_client.query(initial_task)
        response = await collect_response(actor_client)
        
        summary["actor_work"].append(response['text'])
        summary["total_cost"] += response['result_info'].get('total_cost_usd', 0)
        summary["actor_runs_used"] = 1
        print(f"\n💰 Initial actor cost: ${response['result_info'].get('total_cost_usd', 0):.4f}")
        
        # Track conversation history
        summary["conversation_history"].append({
            "phase": "initial_actor",
            "task": initial_task,
            "response_length": len(response['text']),
            "cost": response['result_info'].get('total_cost_usd', 0)
        })
        
    
    # Main loop with queue-based approach
    latest_work = summary["actor_work"][-1]
    
    # Create a queue of critics to check
    critic_queue = critics.copy()
    passed_critics = set()  # Track which critics have passed
    final_check = False  # Flag to ensure we do one final comprehensive check
    
    while summary["actor_runs_used"] < max_actor_runs and (critic_queue or not final_check):
        # If queue is empty but we haven't done final check, add all critics back for final verification
        if not critic_queue and not final_check:
            print(f"\n🔍 FINAL COMPREHENSIVE CHECK - Adding all critics back to queue")
            critic_queue = critics.copy()
            passed_critics = set()  # Reset to check all critics again
            final_check = True
        
        # If no critics left to process, break
        if not critic_queue:
            break
            
        print(f"\n🎓 CRITICS EVALUATION (Actor runs: {summary['actor_runs_used']}/{max_actor_runs})")
        if final_check:
            print("🔍 FINAL CHECK MODE - Verifying all critics")
        print(f"📋 Queue: {[c.__class__.__name__ for c in critic_queue]}")
        print("-" * 50)
        
        # Process the first critic in the queue
        current_critic = critic_queue.pop(0)
        critic_name = current_critic.__class__.__name__
        
        # Skip if already passed (but not during final check)
        if critic_name in passed_critics and not final_check:
            continue
            
        print(f"\n🔍 Evaluating {critic_name}")
        result = await current_critic.evaluate(latest_work)
        
        if result.details and 'cost' in result.details:
            summary["total_cost"] += result.details['cost']
        
        if result.passed:
            print(f"✅ {result.critic_name} - PASSED")
            passed_critics.add(critic_name)
            
            # Track history
            summary["conversation_history"].append({
                "phase": f"critic_passed",
                "critic": result.critic_name,
                "actor_runs_used": summary["actor_runs_used"]
            })
        else:
            print(f"❌ {result.critic_name} - FAILED")
            
            # Track history
            summary["conversation_history"].append({
                "phase": f"critic_failed",
                "critic": result.critic_name,
                "actor_runs_used": summary["actor_runs_used"],
                "feedback": result.feedback[:200] + "..." if len(result.feedback) > 200 else result.feedback
            })
            
            # Try to fix this critic
            if summary["actor_runs_used"] < max_actor_runs:
                if final_check:
                    # If we're in final check and found a failure, we need to fix it
                    print(f"\n⚠️ FINAL CHECK FAILED - Found regression in {result.critic_name}")
                    print(f"🔧 Must fix before continuing...")
                    # Reset final check since we found an issue
                    final_check = False
                    passed_critics = set()  # Reset all passed critics since we have a regression
                else:
                    print(f"\n🔧 TARGETED FIX for {result.critic_name}")
                
                print("-" * 60)
                
                # Run targeted fix
                fix_response = await fix_specific_critic_issue(
                    env=env,
                    code_dir=code_dir,
                    proposal=proposal,
                    critic_name=result.critic_name,
                    critic_feedback=result.feedback,
                    mcp_config=mcp_config,
                    common_tools=common_tools,
                    claude_turns=8
                )
                
                summary["actor_runs_used"] += 1
                summary["total_cost"] += fix_response['result_info'].get('total_cost_usd', 0)
                latest_work = fix_response['text']  # Update latest work
                
                # Add this critic back to the FRONT of the queue to re-check immediately
                critic_queue.insert(0, current_critic)
                
                # Track fix in history
                summary["conversation_history"].append({
                    "phase": f"targeted_fix",
                    "critic": result.critic_name,
                    "actor_runs_used": summary["actor_runs_used"],
                    "cost": fix_response['result_info'].get('total_cost_usd', 0)
                })
                
                summary["targeted_fixes"].append({
                    "critic_name": result.critic_name,
                    "fix_cost": fix_response['result_info'].get('total_cost_usd', 0),
                    "actor_runs_used": summary["actor_runs_used"]
                })
            elif final_check:
                # We're in final check, out of runs, and found a failure
                print(f"\n❌ Final check failed for {result.critic_name} but out of actor runs!")
    
    # Compile final results based on what we know
    print(f"\n📊 FINAL SUMMARY")
    print("-" * 50)
    
    # Get the final state of each critic
    final_results = []
    for critic in critics:
        critic_name = critic.__class__.__name__
        passed = critic_name in passed_critics
        
        final_results.append({
            "critic_name": critic_name,
            "passed": passed,
            "feedback": f"{'Passed' if passed else 'Failed'} in final evaluation"
        })
        
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{critic_name}: {status}")
    
    summary["final_critic_results"] = final_results
    
    # Add a note about whether we completed final check
    if final_check and not critic_queue:
        print("\n✓ Completed final comprehensive check")
    elif final_check and critic_queue:
        print(f"\n⚠️ Final check incomplete - {len(critic_queue)} critics remaining")
    else:
        print("\n⚠️ Did not reach final comprehensive check")
    
    # Set final status based on final results
    all_critics_pass = all(result["passed"] for result in final_results)
    if all_critics_pass:
        print("\n🎉 ALL CRITICS PASSED! Implementation complete.")
        summary["final_status"] = "complete"
    else:
        print(f"\n⚠️ Some critics still failing. Used {summary['actor_runs_used']}/{max_actor_runs} actor runs.")
        summary["final_status"] = "incomplete"
    
    # Final summary
    print("\n" + "=" * 80)
    print("🏁 MULTI-AGENT SYSTEM COMPLETE")
    print("=" * 80)
    print(f"💰 Total cost: ${summary['total_cost']:.4f}")
    print(f"🔄 Actor runs used: {summary['actor_runs_used']}/{max_actor_runs}")
    print(f"📊 Status: {summary['final_status']}")
    
    
    # Save results if in experiment structure
    if experiment_info:
        save_experiment_results(experiment_path, summary)
    
    return summary


# Legacy function for backwards compatibility
async def run_cc_agent(env: str, task: str, system_prompt="You are a scientific research assistant"):
    """Legacy single-agent function - redirects to multi-agent system."""
    print("⚠️  Using legacy function - consider using run_multi_agent_system() directly")
    return await run_multi_agent_system(env, task, max_actor_runs=1)


if __name__ == "__main__":
    # Example usage
    research_proposal = """
    Implement a simple web scraper that:
    1. Fetches data from a website
    2. Parses HTML content
    3. Saves results to JSON
    4. Includes proper error handling
    5. Has unit tests
    """
    
    asyncio.run(run_multi_agent_system(
        env="/tmp/test_project",
        proposal=research_proposal,
        max_actor_runs=8
    ))