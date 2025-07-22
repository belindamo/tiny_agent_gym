"""Create a new file given the file path.

Creates any missing parent directories and optionally writes content to the file.

Args:
  env (str): Base folder path
  filepath (str): Path to create file at, relative to env
  content (str, optional): Text content to write to file. Defaults to empty string.
"""

import os


def create_new_file(env, filepath, content=""):
    # Get absolute path by joining env and filepath
    abs_path = os.path.join(env, filepath)

    # Create parent directories if they don't exist
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    # Create the file and write content if provided
    with open(abs_path, "w") as f:
        f.write(content)
    return True


if __name__ == "__main__":
    create_new_file("envs/env_dummy/playground", "test/file.txt", "Hello world!")
