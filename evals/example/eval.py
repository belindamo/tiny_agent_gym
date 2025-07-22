from models import Run, EvalResult, eval_function
import subprocess
import re
from pathlib import Path

@eval_function
def eval_markdown(r: Run) -> EvalResult:
    """Evaluate the markdown task by running the tests"""
    
    env_path = Path(r.dir_name)
    eval_dir = Path(__file__).parent
    
    # Check that the unit tests weren't modified
    test_file_original_contents = (eval_dir / "solution" / "tests.py").read_text()
    test_file_environment_contents = (env_path / "tests.py").read_text()
    if test_file_environment_contents != test_file_original_contents:
        return EvalResult(passed=False, result="Agent modified the unit tests!")
    
    # Run unit tests
    result = subprocess.run(
        ["pytest", "-q", "--tb=no", "tests.py"],
        cwd=str(env_path),
        capture_output=True,
        text=True,
        check=False,
    )
    
    # Find how many passed
    results = re.search(
        r"(?:(\d+)\s+failed,?\s*)?(?:(\d+)\s+passed,?\s*)?(?:(\d+)\s+skipped)?",
        result.stdout.strip().split("\n")[-1],
    )
    
    # Count the results
    failed = int(results.group(1) or 0)
    passed = int(results.group(2) or 0)
    skipped = int(results.group(3) or 0)
    total = failed + passed + skipped
    
    # Score
    score = float(total > 0 and (passed / total))
    details = f"Failed: {failed}, Passed: {passed}, Skipped: {skipped}, Total: {total}, Score: {score:.2f}"
    
    return EvalResult(passed=score > 0.8, result=details)