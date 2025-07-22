"""Get the folder structure in a string, given a folder path, with AI-generated descriptions"""

import os
from .ai import ai
import html
from typing import Optional

# Folders to ignore
IGNORE_FOLDERS = {"__pycache__", "scratch", ".git"}


def escape_xml(text: str) -> str:
    """Escape special characters for XML"""
    return html.escape(text, quote=True)


def directory(root_path: str, max_depth: Optional[int] = None) -> str:
    """Get folder structure with AI descriptions in XML format

    Args:
      root_path (str): Path to folder to analyze
      max_depth (int, optional): Maximum depth of directory traversal.
                               0 means only immediate children.
                               None means no limit. Defaults to None.

    Returns:
      str: XML string containing folder structure with descriptions
    """
    output = ["<directory>"]

    def process_dir(path: str, level: int = 0) -> None:
        if max_depth is not None and level > max_depth:
            return

        indent = "  " * (level + 1)
        # Process files first
        for file in os.listdir(path):
            file_path = os.path.join(path, file)
            if os.path.isfile(file_path):
                rel_file_path = os.path.relpath(file_path, root_path)
                with open(file_path, "r") as f:
                    try:
                        content = f.read()
                    except:
                        content = ""
                description = ai(
                    "You are a helpful assistant that writes 1 sentence summaries of files.",
                    f"File: {rel_file_path}\n\nSummarize this file in 1 sentence: {content}",
                )
                output.append(
                    f'{indent}<file name="{escape_xml(file)}" description="{escape_xml(description)}" />'
                )

        # Then process subdirectories
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path) and item not in IGNORE_FOLDERS:
                output.append(f'{indent}<folder name="{escape_xml(item)}">')
                process_dir(item_path, level + 1)
                output.append(f"{indent}</folder>")

    process_dir(root_path)
    output.append("</directory>")
    return "\n".join(output)


if __name__ == "__main__":
    # print(directory('envs/env_dummy', max_depth=0))
    print(directory("envs/vanilla_nn_old/playground"))
    # print(directory('envs/env_dummy', max_depth=3))
    # print(directory('envs/env_dummy/playground'))
