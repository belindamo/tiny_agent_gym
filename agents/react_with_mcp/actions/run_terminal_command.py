import subprocess
import os
from pathlib import Path

def run_terminal_command(env_path, command):
  """
  Run `command` with env_path as the working directory. Returns (stdout, stderr).
  
  Args:
    env_path: Path to the environment directory to run the command in
    command: The command to execute
  
  Security Note:
    This function attempts to restrict file operations to the env_path directory,
    but it cannot guarantee complete isolation. For true isolation, consider using
    Docker containers.
  """
  # Store original directory so we can restore it later
  original_dir = os.getcwd()

  # Convert env_path to absolute path
  env_path_abs = Path(os.path.abspath(env_path))

  # Basic security check - look for suspicious patterns in command
  suspicious_patterns = ['../', '~/', '\\']
  if any(pattern in command for pattern in suspicious_patterns):
    return ("", "Error: Command contains suspicious path patterns that might access files outside the working directory")

  try:
    # Verify env_path exists and is a directory
    if not env_path_abs.is_dir():
      return ("", f"Error: {env_path_abs} is not a valid directory")

    # Change to the target directory
    os.chdir(env_path_abs)
    
    # Run the command directly, capturing stdout and stderr
    result = subprocess.run(
      command,
      shell=True,  # Allow shell commands like pipes and redirects
      capture_output=True,
      text=True
    )
    return (result.stdout, result.stderr)
  except Exception as e:
    # In case of error launching the command itself
    return ("", str(e))
  finally:
    # Change back to original directory
    os.chdir(original_dir)

