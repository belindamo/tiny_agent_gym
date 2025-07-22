"""Read one or more existing files from the env folder.

Args:
  env (str): Base folder path
  filepath (str or list): Path(s) to file(s) to read, relative to env

Returns:
  str or dict: Contents of the file(s). Returns string for single file, 
               dict mapping filepaths to contents for multiple files.
  None: If file does not exist
"""
import os

def read_existing_file(env, filepath):
  # Handle single filepath or list of filepaths
  if isinstance(filepath, str):
    # Get absolute path by joining env and filepath
    abs_path = os.path.join(env, filepath)
    
    try:
      # Read and return file contents
      with open(abs_path, 'r') as f:
        return f.read()
    except FileNotFoundError:
      return None
  
  else:
    # Read multiple files and return dict of contents
    contents = {}
    for path in filepath:
      abs_path = os.path.join(env, path)
      try:
        with open(abs_path, 'r') as f:
          contents[path] = f.read()
      except FileNotFoundError:
        contents[path] = None
    return contents
    
if __name__ == "__main__":
  # Example with single file
  content = read_existing_file("envs/env_dummy/playground", "test/file.txt")
  print(content)
  
  # Example with multiple files
  contents = read_existing_file("envs/env_dummy/playground", ["test/file1.txt", "test/file.txt", "test/file2.txt"])
  print(contents)