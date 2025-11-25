from dockai.error_parser import parse_docker_error, format_error_message, enhance_error_feedback

def test_parse_missing_file_error():
    """Test parsing of missing file errors"""
    error_output = """
    ERROR: failed to solve: failed to compute cache key: failed to calculate checksum of ref
    /go.sum: not found
    """
    
    error_type, fixes = parse_docker_error(error_output)
    assert error_type == "Missing File or Directory"
    assert len(fixes) > 0
    assert any("lock file" in fix.lower() for fix in fixes)

def test_parse_permission_denied_error():
    """Test parsing of permission denied errors"""
    error_output = "Error: permission denied while trying to connect to the Docker daemon socket"
    
    error_type, fixes = parse_docker_error(error_output)
    assert error_type == "Permission Denied"
    assert len(fixes) > 0

def test_parse_network_error():
    """Test parsing of network errors"""
    error_output = """
    ERROR: failed to fetch https://registry.npmjs.org/express
    connection refused
    """
    
    error_type, fixes = parse_docker_error(error_output)
    assert error_type == "Network Error"
    assert any("internet connection" in fix.lower() for fix in fixes)

def test_parse_package_not_found():
    """Test parsing of package not found errors"""
    error_output = "ERROR: Could not find a version that satisfies the requirement invalid-package"
    
    error_type, fixes = parse_docker_error(error_output)
    assert error_type == "Package Not Found"
    assert any("package name" in fix.lower() for fix in fixes)

def test_parse_syntax_error():
    """Test parsing of Dockerfile syntax errors"""
    error_output = "Dockerfile:5: syntax error: unexpected token"
    
    error_type, fixes = parse_docker_error(error_output)
    assert error_type == "Dockerfile Syntax Error"
    assert any("syntax" in fix.lower() for fix in fixes)

def test_parse_port_conflict():
    """Test parsing of port conflict errors"""
    error_output = "Error: port 3000 is already allocated"
    
    error_type, fixes = parse_docker_error(error_output)
    assert error_type == "Port Conflict"
    assert any("docker ps" in fix.lower() for fix in fixes)

def test_parse_base_image_error():
    """Test parsing of base image errors"""
    error_output = "Error: pull access denied for invalid-image, repository does not exist"
    
    error_type, fixes = parse_docker_error(error_output)
    assert error_type == "Base Image Error"
    assert any("image name" in fix.lower() for fix in fixes)

def test_parse_unknown_error():
    """Test parsing of unknown errors"""
    error_output = "Some completely unknown error message"
    
    error_type, fixes = parse_docker_error(error_output)
    assert error_type == "Unknown Error"
    assert len(fixes) > 0

def test_format_error_message():
    """Test error message formatting"""
    error_type = "Test Error"
    error_output = "ERROR: This is a test error\nFailed to do something"
    fixes = ["Fix 1", "Fix 2", "Fix 3"]
    
    formatted = format_error_message(error_type, error_output, fixes)
    
    assert "Test Error" in formatted
    assert "Fix 1" in formatted
    assert "Fix 2" in formatted
    assert "Fix 3" in formatted
    assert "💡" in formatted

def test_enhance_error_feedback():
    """Test the main enhance_error_feedback function"""
    error_output = """
    Docker build failed:
    ERROR: failed to compute cache key: /package-lock.json: not found
    """
    
    enhanced = enhance_error_feedback(error_output)
    
    assert "Missing File" in enhanced
    assert "💡" in enhanced
    assert "Suggested Fixes" in enhanced
    assert len(enhanced) > 100  # Should be a substantial message
