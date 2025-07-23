import os
import fcntl
from datetime import datetime
from pathlib import Path

def get_formatted_datetime() -> str:
  return datetime.now().strftime("%Y%m%d%H%M%S%f")[:18]

def get_next_experiment_number() -> int:
  """
  Gets the next experiment number and increments the counter.
  Uses file locking to ensure thread safety.
  Returns the original number before incrementing.
  """
  exp_file = Path(__file__).parent / "next_exp_number"
  
  # Create file if it doesn't exist
  if not exp_file.exists():
    exp_file.write_text("1")
  
  with open(exp_file, 'r+') as f:
    # Get an exclusive lock
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    try:
      # Read current number
      current_num = int(f.read().strip() or "1")
      
      # Seek to beginning and write incremented number
      f.seek(0)
      f.write(str(current_num + 1))
      f.truncate()
      
      return current_num
    finally:
      # Release the lock
      fcntl.flock(f.fileno(), fcntl.LOCK_UN) 