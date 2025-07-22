from typing import Optional, Tuple
from .delete_existing_file import delete_existing_file
from .edit_existing_file import edit_existing_file
from .read_existing_file_s import read_existing_file
from .create_new_file import create_new_file
from .run_terminal_command import run_terminal_command

# DSL for available actions
ACTIONS = {
    "create_file": {
        "description": "Create a new file, optionally with content",
        "args": ["filepath", "content"],
    },
    "delete_file": {"description": "Delete an existing file", "args": ["filepath"]},
    "edit_file": {
        "description": "Edit an existing file by using AI to determine targeted edits based on query",
        "args": ["filepath", "query"],
    },
    "read_file": {
        "description": "Read contents of one or more filepaths. Takes in a string of filepath for one file, or a list of filepaths for multiple. Returns string or list depending",
        "args": ["filepath"],
    },
    "run_terminal_command": {
      "description": "Run a terminal command and return stdout/stderr", 
      "args": ["command"]
    },
}

class ActionsReAct:
    def __init__(self, env):
        self.env = env

    def create_file(self, filepath: str, content: str) -> bool:
        """Create a new file, optionally with content"""
        return create_new_file(self.env, filepath, content)

    def delete_file(self, filepath: str) -> bool:
        """Delete an existing file"""
        return delete_existing_file(self.env, filepath)

    def edit_file(self, filepath: str, query: str) -> bool:
        """Edit an existing file by using AI to determine targeted edits based on query"""
        return edit_existing_file(self.env, filepath, query)

    def read_file(self, filepath: str) -> Optional[str]:
        """Read contents of one or more filepaths. Takes in a string of filepath for one file, or a list of filepaths for multiple. Returns string or list depending"""
        return read_existing_file(self.env, filepath)
      
    def execute_terminal_command(self, command: str) -> Tuple[str, str]:
      """Run a terminal command and return stdout/stderr"""
      return run_terminal_command(self.env, command)
