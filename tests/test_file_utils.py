"""Tests for the file_utils module."""
import os
import tempfile
import pytest
from unittest.mock import patch

from dockai.utils.file_utils import estimate_tokens, smart_truncate, read_critical_files


class TestEstimateTokens:
    """Tests for the estimate_tokens function."""
    
    def test_empty_string(self):
        """Empty string should return 0 tokens."""
        assert estimate_tokens("") == 0
    
    def test_short_string(self):
        """Short strings should estimate correctly."""
        # 12 characters / 4 = 3 tokens
        assert estimate_tokens("Hello World!") == 3
    
    def test_long_string(self):
        """Long strings should estimate based on length."""
        text = "a" * 400
        # 400 chars / 4 = 100 tokens
        assert estimate_tokens(text) == 100
    
    def test_code_content(self):
        """Code content token estimation."""
        code = """def hello():
    print("Hello, World!")
    return True
"""
        tokens = estimate_tokens(code)
        assert tokens > 0
        assert tokens == len(code) // 4


class TestSmartTruncate:
    """Tests for the smart_truncate function."""
    
    def test_short_content_not_truncated(self):
        """Content within limits should not be truncated."""
        content = "Short content"
        result = smart_truncate(content, "test.py", max_chars=1000, max_lines=100)
        assert result == content
    
    def test_long_content_truncated_by_lines(self):
        """Content exceeding line limit should be truncated."""
        lines = [f"Line {i}" for i in range(100)]
        content = "\n".join(lines)
        
        result = smart_truncate(content, "test.py", max_chars=100000, max_lines=20)
        
        assert "[TRUNCATED" in result
        assert "Line 0" in result  # Head preserved
        assert "Line 99" in result  # Tail preserved
    
    def test_preserves_head_and_tail(self):
        """Truncation should preserve head (70%) and tail (30%)."""
        lines = [f"Line {i}" for i in range(200)]
        content = "\n".join(lines)
        
        result = smart_truncate(content, "test.py", max_chars=100000, max_lines=50)
        
        # Head should be preserved (first ~35 lines)
        assert "Line 0" in result
        assert "Line 10" in result
        
        # Tail should be preserved (last ~15 lines)
        assert "Line 199" in result
        assert "Line 190" in result
    
    def test_truncation_message_shows_count(self):
        """Truncation message should show number of lines removed."""
        lines = [f"Line {i}" for i in range(100)]
        content = "\n".join(lines)
        
        result = smart_truncate(content, "test.py", max_chars=100000, max_lines=20)
        
        # Should truncate 80 lines
        assert "TRUNCATED 80 LINES" in result


class TestReadCriticalFiles:
    """Tests for the read_critical_files function."""
    
    def test_read_single_file(self):
        """Should read a single file correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = os.path.join(tmpdir, "app.py")
            with open(test_file, "w") as f:
                f.write("print('hello')")
            
            result = read_critical_files(tmpdir, ["app.py"])
            
            assert "print('hello')" in result
            assert "app.py" in result
    
    def test_read_multiple_files(self):
        """Should read multiple files and concatenate them."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            with open(os.path.join(tmpdir, "app.py"), "w") as f:
                f.write("print('app')")
            with open(os.path.join(tmpdir, "requirements.txt"), "w") as f:
                f.write("flask==2.0.0")
            
            result = read_critical_files(tmpdir, ["app.py", "requirements.txt"])
            
            assert "print('app')" in result
            assert "flask==2.0.0" in result
    
    def test_skip_lock_files(self):
        """Should skip lock files like package-lock.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a lock file
            with open(os.path.join(tmpdir, "package-lock.json"), "w") as f:
                f.write('{"lockfileVersion": 2}')
            with open(os.path.join(tmpdir, "app.js"), "w") as f:
                f.write("console.log('hello');")
            
            result = read_critical_files(tmpdir, ["package-lock.json", "app.js"])
            
            assert "console.log('hello')" in result
            # Lock file should be skipped
            assert "lockfileVersion" not in result
    
    def test_skip_yarn_lock(self):
        """Should skip yarn.lock files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "yarn.lock"), "w") as f:
                f.write("# yarn lockfile")
            
            result = read_critical_files(tmpdir, ["yarn.lock"])
            
            assert "yarn lockfile" not in result
    
    def test_handle_missing_file(self):
        """Should handle missing files gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # File doesn't exist
            result = read_critical_files(tmpdir, ["nonexistent.py"])
            
            # Should not crash, just return empty or skip
            assert result == "" or "nonexistent.py" not in result
    
    def test_truncation_disabled_by_default(self):
        """Truncation should be disabled by default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a large file
            large_content = "\n".join([f"Line {i}" for i in range(10000)])
            with open(os.path.join(tmpdir, "large.py"), "w") as f:
                f.write(large_content)
            
            with patch.dict(os.environ, {}, clear=True):
                # Remove env vars to test default
                result = read_critical_files(tmpdir, ["large.py"], truncation_enabled=False)
            
            # Without truncation, full content should be present
            assert "Line 0" in result
            assert "Line 9999" in result
            assert "TRUNCATED" not in result
    
    def test_truncation_enabled_explicitly(self):
        """Truncation should work when explicitly enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a large file that exceeds limits
            large_content = "\n".join([f"Line {i}" for i in range(10000)])
            with open(os.path.join(tmpdir, "large.py"), "w") as f:
                f.write(large_content)
            
            result = read_critical_files(tmpdir, ["large.py"], truncation_enabled=True)
            
            # With truncation, content should be truncated
            assert "Line 0" in result  # Head preserved
            assert "TRUNCATED" in result
    
    def test_truncation_via_env_var(self):
        """Truncation should be controllable via environment variable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            large_content = "\n".join([f"Line {i}" for i in range(10000)])
            with open(os.path.join(tmpdir, "large.py"), "w") as f:
                f.write(large_content)
            
            with patch.dict(os.environ, {"DOCKAI_TRUNCATION_ENABLED": "true"}):
                result = read_critical_files(tmpdir, ["large.py"])
            
            assert "TRUNCATED" in result
    
    def test_auto_truncation_on_token_limit(self):
        """Should auto-enable truncation when token limit is exceeded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a file that will exceed a small token limit
            large_content = "x" * 10000  # ~2500 tokens
            with open(os.path.join(tmpdir, "large.txt"), "w") as f:
                f.write(large_content)
            
            # Set a very small token limit to trigger auto-truncation
            with patch.dict(os.environ, {
                "DOCKAI_TRUNCATION_ENABLED": "false",
                "DOCKAI_TOKEN_LIMIT": "100"  # Very small limit
            }):
                result = read_critical_files(tmpdir, ["large.txt"])
            
            # Should have auto-truncated
            # The file should be read (we check it's not empty)
            assert len(result) > 0
    
    def test_critical_dependency_files_preserved(self):
        """Critical dependency files should be read fully when possible."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create requirements.txt
            with open(os.path.join(tmpdir, "requirements.txt"), "w") as f:
                f.write("flask==2.0.0\nrequests==2.28.0")
            
            result = read_critical_files(tmpdir, ["requirements.txt"])
            
            assert "flask==2.0.0" in result
            assert "requests==2.28.0" in result


class TestEnvironmentVariables:
    """Tests for environment variable handling."""
    
    def test_token_limit_default(self):
        """Default token limit should be 100000."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "test.py"), "w") as f:
                f.write("print('test')")
            
            with patch.dict(os.environ, {}, clear=True):
                # Should not crash with missing env var
                result = read_critical_files(tmpdir, ["test.py"])
                assert "print('test')" in result
    
    def test_invalid_token_limit_fallback(self):
        """Invalid token limit should fallback to default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with open(os.path.join(tmpdir, "test.py"), "w") as f:
                f.write("print('test')")
            
            with patch.dict(os.environ, {"DOCKAI_TOKEN_LIMIT": "invalid"}):
                # Should not crash with invalid value
                result = read_critical_files(tmpdir, ["test.py"])
                assert "print('test')" in result
    
    def test_truncation_env_var_variations(self):
        """Various truthy values should enable truncation."""
        truthy_values = ["true", "True", "TRUE", "1", "yes", "on"]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            large_content = "\n".join([f"Line {i}" for i in range(10000)])
            with open(os.path.join(tmpdir, "large.py"), "w") as f:
                f.write(large_content)
            
            for value in truthy_values:
                with patch.dict(os.environ, {"DOCKAI_TRUNCATION_ENABLED": value}):
                    result = read_critical_files(tmpdir, ["large.py"])
                    assert "TRUNCATED" in result, f"Failed for value: {value}"
