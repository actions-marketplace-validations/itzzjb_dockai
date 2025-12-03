
import pytest
import sys

def run_tests():
    result = pytest.main(["tests/test_langsmith.py", "-v"])
    with open("pytest_result.txt", "w") as f:
        f.write(f"Exit code: {result}\n")

if __name__ == "__main__":
    run_tests()
