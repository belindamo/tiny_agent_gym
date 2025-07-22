"""Delete an existing file from the env folder.

Args:
  env (str): Base folder path
  filepath (str): Path to file to delete, relative to env
  
Returns:
  bool: True if deletion was successful, False if file not found
"""
import os

def delete_existing_file(env, filepath):
  # Get absolute path by joining env and filepath
  abs_path = os.path.join(env, filepath)
  
  try:
    # Delete the file
    os.remove(abs_path)
    
    # Get the directory path
    dir_path = os.path.dirname(abs_path)
    
    # If directory exists and is empty, remove it
    if os.path.exists(dir_path) and not os.listdir(dir_path):
      os.rmdir(dir_path)
      
    return True
    
  except FileNotFoundError:
    return False
if __name__ == "__main__":
  # Example usage
  success = delete_existing_file("envs/env_dummy/playground", "test/file.txt")
  print(f"Deletion {'succeeded' if success else 'failed'}")