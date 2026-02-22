import datetime
import subprocess
from typing import Any, Type

from pydantic import BaseModel

from .base import MCPTool


class GetCurrentTimeArgs(BaseModel):
    pass


class GetCurrentTimeTool(MCPTool):
    name: str = "get_current_time"
    description: str = "Get the current system time in ISO format."
    args_schema: Type[BaseModel] = GetCurrentTimeArgs

    async def run(self, **kwargs) -> Any:
        return datetime.datetime.now().isoformat()


class CheckRepoStatusArgs(BaseModel):
    pass


class CheckRepoStatusTool(MCPTool):
    name: str = "check_repo_status"
    description: str = "Check the git status of the current repository."
    args_schema: Type[BaseModel] = CheckRepoStatusArgs

    async def run(self, **kwargs) -> Any:
        try:
            result = subprocess.run(["git", "status"], capture_output=True, text=True, check=True)
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"Error checking git status: {e}"
        except Exception as e:
            return f"Failed to execute git command: {e}"
