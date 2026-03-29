"""
Test Suite for RCE Engine
=========================

Unit tests for the SafeExecutor class using unittest framework.
Tests cover: normal execution, syntax errors, and timeout enforcement.
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rce_engine import SafeExecutor, execute_code


class TestSafeExecutor(unittest.TestCase):
    """Test cases for SafeExecutor class."""

    def setUp(self):
        """Create executor instance for each test."""
        self.executor = SafeExecutor(timeout=3)

    def test_hello_world_execution(self):
        """Test 1: Standard execution with stdout capture."""
        result = self.executor.execute("print('Hello World')")

        self.assertTrue(result["success"], "Execution should succeed")
        self.assertIn("Hello World", result["stdout"], "Output should contain 'Hello World'")
        self.assertEqual(result["stderr"], "", "No errors expected")
        self.assertFalse(result["timed_out"], "Should not timeout")

    def test_syntax_error_handling(self):
        """Test 2: Syntax error should be captured in stderr."""
        result = self.executor.execute("print('missing closing quote")

        self.assertFalse(result["success"], "Execution should fail on syntax error")
        self.assertTrue(len(result["stderr"]) > 0, "stderr should contain error message")
        self.assertFalse(result["timed_out"], "Should not timeout on syntax error")

    def test_infinite_loop_timeout(self):
        """Test 3: Infinite loop must trigger timeout protection."""
        malicious_code = """
while True:
    pass
"""
        result = self.executor.execute(malicious_code, timeout=2)

        self.assertTrue(result["timed_out"], "Infinite loop should trigger timeout")
        self.assertFalse(result["success"], "Timed out execution should not succeed")

    def test_return_value_capture(self):
        """Test 4: Multi-line code execution and output capture."""
        code = """
x = 5
y = 10
print(f'Sum: {x + y}')
"""
        result = self.executor.execute(code)

        self.assertTrue(result["success"], "Multi-line code should execute")
        self.assertIn("Sum: 15", result["stdout"], "Output should show computed result")

    def test_import_allowed(self):
        """Test 5: Standard library imports should work."""
        result = self.executor.execute("import math; print(math.pi)")

        self.assertTrue(result["success"], "Import should work")
        self.assertIn("3.14", result["stdout"][:10], "Should print pi value")

    def test_convenience_function(self):
        """Test 6: execute_code convenience function works."""
        result = execute_code("print('test')", timeout=2)

        self.assertIn("test", result["stdout"], "Convenience function should work")


class TestEdgeCases(unittest.TestCase):
    """Edge case tests for robustness."""

    def test_empty_code(self):
        """Empty code should execute without error."""
        result = execute_code("")
        self.assertTrue(result["success"], "Empty code should succeed")
        self.assertEqual(result["stdout"], "", "No output expected")

    def test_unicode_output(self):
        """Unicode characters should be handled correctly."""
        result = execute_code("print('Hello 世界 🌍')")

        self.assertTrue(result["success"], "Unicode should work")
        self.assertIn("世界", result["stdout"], "Unicode should be preserved")


if __name__ == "__main__":
    unittest.main(verbosity=2)