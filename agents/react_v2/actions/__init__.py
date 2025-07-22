from typing import Tuple
from .run_terminal_command import run_terminal_command

# DSL for available actions
ACTIONS = {
    "run_terminal_command": {
      "description": "Run a terminal command and return stdout/stderr", 
      "args": ["command"]
    },
}

class Actions:
    def __init__(self, env):
        self.env = env

    def run_terminal_command(self, command: str) -> Tuple[str, str]:
      """Run a terminal command and return stdout/stderr"""
      return run_terminal_command(self.env, command)
