#!/usr/bin/env python3
"""
Test script for the multi-agent system
"""

import asyncio
import sys
import os
from cc_agent import run_multi_agent_system


async def test_basic():
    """Test basic functionality with a simple proposal"""
    print("Testing basic multi-agent system...")
    
    # Simple test proposal with explicit metrics
    test_proposal = """
    Create a simple calculator module that:
    1. Has functions for add, subtract, multiply, divide
    2. Includes proper error handling for division by zero
    3. Has comprehensive unit tests (target: >95% code coverage)
    4. Logs all operations to a file with timestamps
    
    Required Metrics & Logging:
    - Test Coverage: Must achieve >95% line coverage
    - Performance: All operations must complete in <1ms
    - Error Rate: Division by zero must be handled gracefully
    - Operation Count: Log total number of each operation type
    - Response Time: Track and log execution time for each operation
    - Memory Usage: Monitor peak memory usage during operations
    
    Configuration Parameters:
    - Logging level (INFO, DEBUG, ERROR)
    - Output file path for operation logs
    - Precision settings for floating-point operations
    - Timeout settings for operations
    """
    
    # Create a test directory
    test_dir = "/tmp/test_multiagent"
    os.makedirs(test_dir, exist_ok=True)
    
    result = await run_multi_agent_system(
        env=test_dir,
        proposal=test_proposal,
        max_actor_runs=6  # 1 initial + up to 5 targeted fixes
    )
    
    print("\nTest Results:")
    print(f"Final Status: {result['final_status']}")
    print(f"Total Cost: ${result['total_cost']:.4f}")
    print(f"Actor Runs Used: {result['actor_runs_used']}")
    
    return result


async def test_experiment_structure():
    """Test with experiment directory structure"""
    print("\nTesting with experiment structure...")
    
    # Create experiment structure
    exp_dir = "/tmp/test_experiment_env"
    exp_path = os.path.join(exp_dir, "experiments", "test_exp")
    code_path = os.path.join(exp_path, "code")
    
    os.makedirs(exp_path, exist_ok=True)
    os.makedirs(code_path, exist_ok=True)
    
    # Write a plan.md file with explicit metrics
    plan_content = """# Experiment Plan

## Research Question
Can we build a reliable web scraper with comprehensive monitoring?

## Implementation Requirements
1. Create a web scraper that fetches data from a URL
2. Parse HTML to extract specific elements
3. Save results to JSON format
4. Include error handling for network issues
5. Write unit tests for all functions (target: >90% coverage)
6. Log all operations with timestamps and performance metrics

## Evaluation Metrics

### Primary Metrics
- **Success Rate:** (Successful requests) / (Total requests), target: >95%
- **Response Time:** Average time per request, target: <2 seconds
- **Data Quality:** (Valid JSON records) / (Total records), target: >98%

### Secondary Metrics
- **Error Rate:** (Failed requests) / (Total requests), target: <5%
- **Memory Usage:** Peak memory during scraping, target: <100MB
- **Throughput:** Requests per second, target: >10 req/s

### Required Logging & Tracking
- **Request Metrics:** URL, response time, status code, data size
- **Error Tracking:** Error types, frequencies, timestamps
- **Performance Metrics:** Memory usage, CPU usage, network bandwidth
- **Data Quality:** Validation results, parsing errors, missing fields
- **Configuration:** User agents, timeouts, retry settings

## Success Criteria
- All functions have tests (>90% coverage)
- Code handles errors gracefully (all error types logged)
- Results are saved in proper JSON format with validation
- Comprehensive logging captures all required metrics
- Performance targets are met and documented
"""
    
    with open(os.path.join(exp_path, "plan.md"), "w") as f:
        f.write(plan_content)
    
    # Run with empty proposal (should read from plan.md)
    result = await run_multi_agent_system(
        env=exp_dir,
        proposal="",  # Empty to trigger plan.md reading
        max_actor_runs=6  # 1 initial + up to 5 targeted fixes
    )
    
    print("\nExperiment Structure Test Results:")
    print(f"Final Status: {result['final_status']}")
    print(f"Total Cost: ${result['total_cost']:.4f}")
    print(f"Code directory exists: {os.path.exists(code_path)}")
    
    # Check if results were saved
    results_dir = os.path.join(exp_path, "results")
    results_md = os.path.join(exp_path, "results.md")
    print(f"Results directory created: {os.path.exists(results_dir)}")
    print(f"Results.md updated: {os.path.exists(results_md)}")
    
    if os.path.exists(results_dir):
        json_files = [f for f in os.listdir(results_dir) if f.startswith("multiagent_summary_")]
        print(f"JSON summary files created: {len(json_files)}")
    
    return result


if __name__ == "__main__":
    print("Multi-Agent System Test Suite")
    print("=" * 50)
    
    # Run tests
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Test 1: Basic functionality
        result1 = loop.run_until_complete(test_basic())
        
        # Test 2: Experiment structure
        result2 = loop.run_until_complete(test_experiment_structure())
        
        print("\n" + "=" * 50)
        print("All tests completed!")
        
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
    except Exception as e:
        print(f"\nError during tests: {e}")
        import traceback
        traceback.print_exc()
    finally:
        loop.close()
