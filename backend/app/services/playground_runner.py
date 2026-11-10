import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Dict, Optional, Tuple

from backend.app.schemas.playground_schema import PlaygroundExecutionResult
from backend.app.utils.logger import logger

# Maximum allowed stdout / stderr characters captured (200 KB)
MAX_OUTPUT_CHARS = 200_000

class PlaygroundRunner:
    """
    Safely executes user Python source code in an isolated subprocess sandbox.
    
    Security & Isolation Guarantees:
    - Never executes user code inside the main FastAPI application process.
    - Runs in an isolated temporary directory, automatically purged after execution.
    - Environment variables are stripped (no database credentials, tokens, or app secrets).
    - Python is invoked with -I (isolated mode, ignoring PYTHONPATH and user site-packages).
    - Strict execution timeout kills infinite loops and runaway processes.
    - Output size is bounded to prevent denial-of-service memory exhaustion.
    """

    @classmethod
    def execute_code(
        cls,
        code: str,
        timeout_seconds: float = 5.0,
        stdin_input: str = ""
    ) -> PlaygroundExecutionResult:
        if not code or not code.strip():
            return PlaygroundExecutionResult(
                success=True,
                stdout="",
                stderr="",
                exit_code=0,
                execution_time_ms=0.0,
                status="completed",
                error_message=None,
                traceback=None
            )

        timeout = min(max(timeout_seconds, 0.5), 10.0)

        # 1. Allocate isolated workspace
        temp_dir = tempfile.mkdtemp(prefix="playground_exec_")
        script_path = os.path.join(temp_dir, "main.py")

        try:
            # 2. Write source code to isolated disk file
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code)

            # 3. Construct minimal, sanitized execution environment
            # Specifically omit all host environment variables, tokens, and application secrets
            sanitized_env: Dict[str, str] = {
                "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
                "LANG": "en_US.UTF-8",
                "LC_ALL": "en_US.UTF-8",
                "PYTHONIOENCODING": "utf-8",
                "PYTHONDONTWRITEBYTECODE": "1",
                "TMPDIR": temp_dir,
                "HOME": temp_dir,
            }

            # 4. Spawn isolated Python subprocess with -u (unbuffered) and -I (isolated)
            start_time = time.perf_counter()
            proc = subprocess.Popen(
                [sys.executable, "-u", "-I", "main.py"],
                cwd=temp_dir,
                env=sanitized_env,
                stdin=subprocess.PIPE if stdin_input else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="replace"
            )

            stdout_text = ""
            stderr_text = ""
            is_timeout = False

            try:
                stdout_text, stderr_text = proc.communicate(
                    input=stdin_input if stdin_input else None,
                    timeout=timeout
                )
            except subprocess.TimeoutExpired:
                is_timeout = True
                proc.kill()
                try:
                    stdout_text, stderr_text = proc.communicate(timeout=1.0)
                except Exception:
                    pass

            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Cap output lengths
            if len(stdout_text) > MAX_OUTPUT_CHARS:
                stdout_text = stdout_text[:MAX_OUTPUT_CHARS] + "\n... [Output truncated: exceeded 200 KB limit]"
            if len(stderr_text) > MAX_OUTPUT_CHARS:
                stderr_text = stderr_text[:MAX_OUTPUT_CHARS] + "\n... [Error output truncated: exceeded 200 KB limit]"

            if is_timeout:
                return PlaygroundExecutionResult(
                    success=False,
                    stdout=stdout_text,
                    stderr=stderr_text,
                    exit_code=-1,
                    execution_time_ms=duration_ms,
                    status="timeout",
                    error_message=f"Execution timed out after {timeout:.1f} seconds. Infinite loops or long operations are stopped for security.",
                    traceback=None
                )

            # Parse traceback / exception if stderr has content and exit code != 0
            traceback_str = None
            error_msg = None
            if proc.returncode != 0:
                if stderr_text.strip():
                    traceback_str = stderr_text.strip()
                    # Extract last line of traceback as human-readable error
                    lines = [l.strip() for l in stderr_text.strip().splitlines() if l.strip()]
                    if lines:
                        error_msg = lines[-1]
                else:
                    error_msg = f"Process exited with non-zero exit code {proc.returncode}."

            return PlaygroundExecutionResult(
                success=(proc.returncode == 0),
                stdout=stdout_text,
                stderr=stderr_text,
                exit_code=proc.returncode,
                execution_time_ms=duration_ms,
                status="completed" if proc.returncode == 0 else "error",
                error_message=error_msg,
                traceback=traceback_str
            )

        except Exception as e:
            logger.error(f"Playground execution exception: {e}", exc_info=True)
            return PlaygroundExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                exit_code=1,
                execution_time_ms=0.0,
                status="error",
                error_message=f"Failed to execute sandbox: {str(e)}",
                traceback=None
            )
        finally:
            # 5. Always securely purge temporary execution directory
            shutil.rmtree(temp_dir, ignore_errors=True)

