import logging
import sys
import os
from pathlib import Path

class PrintToLogger:
    """Redirects stdout/stderr to logging while preserving original streams"""
    def __init__(self, is_stderr=False):
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        self._is_stderr = is_stderr
        self._buffer = []
        # Store the original fileno
        self._fileno = self._stderr.fileno() if is_stderr else self._stdout.fileno()
        
    def write(self, text):
        if text.strip():
            if self._is_stderr:
                logging.getLogger("stderr").error(text.rstrip())
            else:
                logging.getLogger("stdout").info(text.rstrip())
        
        # Also write to original stdout/stderr
        if self._is_stderr:
            self._stderr.write(text)
        else:
            self._stdout.write(text)
        
    def flush(self):
        if self._is_stderr:
            self._stderr.flush()
        else:
            self._stdout.flush()
            
    def fileno(self):
        # Return the stored fileno
        return self._fileno
    
    def isatty(self):
        # Check if the original stream is a terminal
        if self._is_stderr:
            return self._stderr.isatty()
        else:
            return self._stdout.isatty()

def silence_loggers(logger_names):
    """Silence specific loggers by setting them to WARNING level"""
    for logger_name in logger_names:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

def setup_logging(run_dir: Path):
    """Set up comprehensive logging configuration for the run"""
    # Configure main logging
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(run_dir / "all.log"),
            logging.StreamHandler()
        ],
        force=True
    )

    # Add separate log files for info and errors
    root_logger = logging.getLogger()
    
    info_handler = logging.FileHandler(run_dir / "info.log")
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(info_handler)
    
    error_handler = logging.FileHandler(run_dir / "error.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(error_handler)
    
    # Configure stderr logger to use the same error.log file
    stderr_logger = logging.getLogger("stderr")
    stderr_logger.addHandler(error_handler)
    stderr_logger.setLevel(logging.ERROR)
    stderr_logger.propagate = False  # Prevent duplication with root logger

def redirect_stdout_stderr():
    """Redirect stdout/stderr to logging (only if not in subprocess)"""
    if not os.environ.get('MCP_SUBPROCESS'):
        sys.stdout = PrintToLogger(is_stderr=False)
        sys.stderr = PrintToLogger(is_stderr=True) 