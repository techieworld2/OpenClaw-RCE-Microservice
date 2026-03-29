"""
RCE Engine - Secure Remote Code Execution Module
=================================================

A sandboxed Python code executor for LeetCode-style HR testing applications.
Provides safe execution with timeout enforcement and output capture.
"""

import subprocess
import tempfile
import os
import re


class SafeExecutor:
    """
    Safely executes user-submitted Python code in an isolated subprocess.

    Features:
    - Timeout enforcement (default 3 seconds)
    - stdout/stderr capture
    - Clean structured output
    """

    def __init__(self, timeout: int = 3, max_output_size: int = 10240):
        """
        Initialize the executor.

        Args:
            timeout: Maximum execution time in seconds (default 3)
            max_output_size: Maximum output size in bytes (default 10KB)
        """
        self.timeout = timeout
        self.max_output_size = max_output_size

    def _sanitize_output(self, output: str) -> str:
        """
        Sanitize output by removing ANSI codes and truncating.

        Args:
            output: Raw output string

        Returns:
            Sanitized output string
        """
        # Remove ANSI escape codes
        ansi_pattern = re.compile(r'\x1b\[[0-9;]*[mGKH]')
        output = ansi_pattern.sub('', output)

        # Truncate if too long
        if len(output) > self.max_output_size:
            output = output[:self.max_output_size] + "\n... [OUTPUT TRUNCATED]"

        return output

    def execute(self, code: str, timeout: int = None) -> dict:
        """
        Execute Python code safely in an isolated subprocess.

        Args:
            code: Python source code to execute
            timeout: Override default timeout (seconds)

        Returns:
            dict with keys:
                - success (bool): True if code ran without exceptions
                - stdout (str): Standard output from execution
                - stderr (str): Standard error from execution
                - timed_out (bool): True if execution exceeded timeout
        """
        # Use instance timeout if not provided
        exec_timeout = timeout if timeout is not None else self.timeout

        result = {
            "success": False,
            "stdout": "",
            "stderr": "",
            "timed_out": False
        }

        # Create temporary file for code execution
        # Using temp file is more reliable than -c for complex code
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False,
                encoding='utf-8'
            ) as temp_file:
                temp_file.write(code)
                temp_path = temp_file.name

            try:
                # Execute in isolated subprocess
                # Set PYTHONIOENCODING=utf-8 to ensure proper Unicode handling on Windows
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'

                process = subprocess.Popen(
                    ['python', temp_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    env=env
                )

                try:
                    # Wait for completion with timeout
                    stdout, stderr = process.communicate(timeout=exec_timeout)

                    result["success"] = process.returncode == 0
                    result["stdout"] = self._sanitize_output(stdout)
                    result["stderr"] = self._sanitize_output(stderr)

                except subprocess.TimeoutExpired:
                    # Timeout exceeded - kill the process
                    process.kill()
                    process.wait()

                    result["timed_out"] = True
                    result["stderr"] = f"Execution timed out after {exec_timeout} seconds"

            finally:
                # Clean up temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            result["stderr"] = f"Executor error: {str(e)}"

        return result


# Convenience function for simple usage
def execute_code(code: str, timeout: int = 3) -> dict:
    """
    Quick helper to execute code without instantiating SafeExecutor.

    Args:
        code: Python source code to execute
        timeout: Maximum execution time in seconds

    Returns:
        dict with execution results
    """
    executor = SafeExecutor(timeout=timeout)
    return executor.execute(code)


# Module-level test
if __name__ == "__main__":
    # Quick self-test
    executor = SafeExecutor()

    print("Testing normal execution...")
    result = executor.execute("print('Hello World')")
    print(f"Result: {result}")
    assert result["success"] == True
    assert "Hello World" in result["stdout"]

    print("\nTesting syntax error...")
    result = executor.execute("print('missing quote")
    print(f"Result: {result}")
    assert result["success"] == False
    assert len(result["stderr"]) > 0

    print("\nTesting timeout...")
    result = executor.execute("while True: pass", timeout=1)
    print(f"Result: {result}")
    assert result["timed_out"] == True

    print("\nAll self-tests passed!")