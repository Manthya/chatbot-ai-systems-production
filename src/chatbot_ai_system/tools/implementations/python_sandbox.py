"""Local Python Sandbox tool implementation."""

import logging
import re
import subprocess
import tempfile
import os
import sys
from typing import Dict, Any
from pydantic import BaseModel, Field

from chatbot_ai_system.tools.base import MCPTool

logger = logging.getLogger(__name__)

class PythonSandboxArgs(BaseModel):
    code: str = Field(..., description="The Python code to execute.")
    timeout: int = Field(default=10, description="Execution timeout in seconds (default: 10).")

class LocalPythonSandbox(MCPTool):
    """Tool for running Python code locally."""

    name = "run_python_script"
    description = (
        "MUST be used whenever you need to run Python code, calculate values, or process data. "
        "DO NOT just write the code in text; you MUST execute it using this tool to get the result. "
        "The code runs in a temporary file. Use print() to output results."
    )
    
    args_schema = PythonSandboxArgs

    async def run(self, code: str, timeout: int = 10) -> str:
        """Execute the python script."""
        
        # Security: Basic check to prevent dangerous system calls?
        # Ideally we'd scan for os.system, subprocess.Popen, etc.
        # But for "Phase 6.5 Free Tools" we rely on the user knowing this is local execution.
        # Adding a basic warning log.
        if "subprocess" in code or "os.system" in code:
             logger.warning("Code contains potential system command execution.")

        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
                tmp.write(code)
                tmp_path = tmp.name

            # Run the script
            # Use specific python executable or sys.executable
            result = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            output = result.stdout
            error = result.stderr
            
            # Clean up
            os.remove(tmp_path)
            
            if result.returncode != 0:
                return f"Error (Exit Code {result.returncode}):\n{error}\nOutput:\n{output}"
            
            return output if output.strip() else "Script executed successfully (no output)."

        except subprocess.TimeoutExpired:
            return f"Error: Execution timed out after {timeout} seconds."
        except Exception as e:
            return f"System Error: {str(e)}"
