"""Edit an existing file by modifying only what is necessary based on a query.

Uses AI to determine and make targeted edits while preserving the rest of the file.

Args:
  env (str): Base folder path
  filepath (str): Path to file to edit, relative to env
  query (str): Description of the edit to make
  
Returns:
  bool: True if edit was successful, False if file not found
"""
import os
from helpers.ai import ai

def edit_existing_file(env, filepath, query):
  # Get absolute path by joining env and filepath
  abs_path = os.path.join(env, filepath)
  
  try:
    # Read current file contents
    with open(abs_path, 'r') as f:
      current_content = f.read()
      
    # Ask AI to make the edit
    system_prompt = "You are an expert. Given a file's content and an edit request, output ONLY the new content with the requested changes while preserving everything else."
    user_prompt = f"File content:\n{current_content}\n\nRequested edit: {query}\n\nOutput the new file content:"
    
    
    
    new_content = ai(system_prompt, user_prompt)
    
    # Strip code block markers if present
    if new_content.startswith("```"):
      # Find the first newline to skip language identifier if present
      first_nl = new_content.find("\n")
      # Remove opening ``` and optional language
      new_content = new_content[first_nl + 1:]
      
    # Remove closing ``` if present  
    if new_content.endswith("```"):
      new_content = new_content[:-3]
      
    # Write the edited content back to file
    with open(abs_path, 'w') as f:
      f.write(new_content)
      
    return True
    
  except FileNotFoundError:
    return False
    
if __name__ == "__main__":
  # Example usage
  success = edit_existing_file("envs/env_dummy/playground", "test/file.txt", 
                             "Add a docstring explaining what this file does")
  print(f"Edit {'succeeded' if success else 'failed'}")