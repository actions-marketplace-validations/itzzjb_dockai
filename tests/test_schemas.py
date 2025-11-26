"""Tests for the schemas module."""
import pytest
from dockai.core.schemas import (
    AnalysisResult,
    HealthEndpoint,
    DockerfileResult,
    SecurityIssue,
    SecurityReviewResult,
    PlanningResult,
    ReflectionResult,
    HealthEndpointDetectionResult,
    ReadinessPatternResult,
    IterativeDockerfileResult,
)


class TestHealthEndpoint:
    """Test HealthEndpoint schema."""
    
    def test_creation(self):
        """Test creating a health endpoint."""
        endpoint = HealthEndpoint(path="/health", port=8080)
        assert endpoint.path == "/health"
        assert endpoint.port == 8080


class TestAnalysisResult:
    """Test AnalysisResult schema."""
    
    def test_minimal_creation(self):
        """Test creating with minimal required fields."""
        result = AnalysisResult(
            thought_process="Analyzing project",
            stack="Python",
            project_type="service",
            files_to_read=["app.py"],
            build_command=None,
            start_command="python app.py",
            suggested_base_image="python:3.11",
            recommended_wait_time=10
        )
        
        assert result.stack == "Python"
        assert result.project_type == "service"
        assert result.suggested_base_image == "python:3.11"
        assert result.build_command is None
        assert result.start_command == "python app.py"
    
    def test_full_creation(self):
        """Test creating with all fields."""
        health = HealthEndpoint(path="/health", port=8080)
        result = AnalysisResult(
            thought_process="Full analysis",
            stack="Node.js",
            project_type="service",
            files_to_read=["package.json", "index.js"],
            build_command="npm install",
            start_command="npm start",
            suggested_base_image="node:20-alpine",
            health_endpoint=health,
            recommended_wait_time=10
        )
        
        assert result.build_command == "npm install"
        assert result.start_command == "npm start"
        assert result.health_endpoint.path == "/health"
        assert result.recommended_wait_time == 10
    
    def test_dict_conversion(self):
        """Test converting to dict."""
        result = AnalysisResult(
            thought_process="Test",
            stack="Go",
            project_type="service",
            files_to_read=["main.go"],
            build_command="go build -o app",
            start_command="./app",
            suggested_base_image="golang:1.21",
            recommended_wait_time=5
        )
        
        d = result.model_dump()
        assert d["stack"] == "Go"
        assert d["suggested_base_image"] == "golang:1.21"


class TestDockerfileResult:
    """Test DockerfileResult schema."""
    
    def test_creation(self):
        """Test creating a Dockerfile result."""
        result = DockerfileResult(
            thought_process="Creating Dockerfile",
            dockerfile="FROM python:3.11\nCMD python app.py",
            project_type="service"
        )
        
        assert "FROM python:3.11" in result.dockerfile
        assert result.project_type == "service"


class TestSecurityIssue:
    """Test SecurityIssue schema."""
    
    def test_creation(self):
        """Test creating a security issue."""
        issue = SecurityIssue(
            severity="high",
            description="Running as root user",
            line_number=5,
            suggestion="Add USER instruction"
        )
        
        assert issue.severity == "high"
        assert issue.line_number == 5


class TestSecurityReviewResult:
    """Test SecurityReviewResult schema."""
    
    def test_secure_review(self):
        """Test review with no issues."""
        review = SecurityReviewResult(
            thought_process="Reviewed Dockerfile",
            is_secure=True,
            issues=[]
        )
        
        assert review.is_secure is True
        assert len(review.issues) == 0
    
    def test_insecure_review(self):
        """Test review with security issues."""
        issue = SecurityIssue(
            severity="high",
            description="Running as root",
            line_number=1,
            suggestion="Add USER instruction"
        )
        review = SecurityReviewResult(
            thought_process="Found vulnerabilities",
            is_secure=False,
            issues=[issue],
            dockerfile_fixes=["Add USER instruction"],
            fixed_dockerfile="FROM python:3.11-slim\nUSER app"
        )
        
        assert review.is_secure is False
        assert len(review.issues) == 1
        assert review.fixed_dockerfile is not None


class TestPlanningResult:
    """Test PlanningResult schema."""
    
    def test_creation(self):
        """Test creating a planning result."""
        plan = PlanningResult(
            thought_process="Planning multi-stage build",
            base_image_strategy="Use python:3.11-slim for runtime",
            build_strategy="Multi-stage for smaller image",
            optimization_priorities=["security", "size"],
            potential_challenges=["Large dependencies"],
            mitigation_strategies=["Use multi-stage build"],
            use_multi_stage=True,
            use_minimal_runtime=True,
            use_static_linking=False,
            estimated_image_size="100-200MB"
        )
        
        assert plan.use_multi_stage is True
        assert "security" in plan.optimization_priorities


class TestReflectionResult:
    """Test ReflectionResult schema."""
    
    def test_with_fixes(self):
        """Test reflection with fix suggestions."""
        result = ReflectionResult(
            thought_process="Analyzed build failure",
            root_cause_analysis="Missing dependency libpq-dev",
            was_error_predictable=False,
            what_was_tried="Standard Python Dockerfile",
            why_it_failed="Missing C library for psycopg2",
            lesson_learned="Check for C dependencies in Python packages",
            should_change_base_image=False,
            should_change_build_strategy=True,
            new_build_strategy="Install build dependencies first",
            specific_fixes=["Add libpq-dev", "Install build-essential"],
            needs_reanalysis=False,
            confidence_in_fix="high"
        )
        
        assert result.root_cause_analysis == "Missing dependency libpq-dev"
        assert len(result.specific_fixes) == 2
        assert result.confidence_in_fix == "high"
    
    def test_no_retry(self):
        """Test reflection with different approach needed."""
        result = ReflectionResult(
            thought_process="Fundamental issue",
            root_cause_analysis="Incompatible architecture",
            was_error_predictable=True,
            what_was_tried="ARM-based image on x86",
            why_it_failed="Architecture mismatch",
            lesson_learned="Check target architecture",
            should_change_base_image=True,
            suggested_base_image="python:3.11-slim-amd64",
            should_change_build_strategy=False,
            specific_fixes=["Use platform-specific base image"],
            needs_reanalysis=True,
            reanalysis_focus="Target platform",
            confidence_in_fix="medium"
        )
        
        assert result.needs_reanalysis is True


class TestHealthEndpointDetectionResult:
    """Test HealthEndpointDetectionResult schema."""
    
    def test_with_endpoint(self):
        """Test detection with endpoint found."""
        endpoint = HealthEndpoint(path="/health", port=8080)
        result = HealthEndpointDetectionResult(
            thought_process="Found /health endpoint",
            health_endpoints_found=[endpoint],
            primary_health_endpoint=endpoint,
            confidence="high",
            evidence=["Found @app.get('/health') in main.py"]
        )
        
        assert result.confidence == "high"
        assert result.primary_health_endpoint.path == "/health"
    
    def test_without_endpoint(self):
        """Test detection with no endpoint found."""
        result = HealthEndpointDetectionResult(
            thought_process="No health endpoint found",
            health_endpoints_found=[],
            confidence="none",
            evidence=[],
            suggested_health_path="/health"
        )
        
        assert result.confidence == "none"
        assert result.suggested_health_path == "/health"


class TestReadinessPatternResult:
    """Test ReadinessPatternResult schema."""
    
    def test_with_patterns(self):
        """Test readiness pattern detection."""
        result = ReadinessPatternResult(
            thought_process="Found startup patterns",
            startup_success_patterns=["Listening on port", "Server started"],
            startup_failure_patterns=["Error:", "Failed to"],
            estimated_startup_time=5,
            max_wait_time=30,
            technology_detected="FastAPI",
            technology_specific_patterns=["Uvicorn running"]
        )
        
        assert len(result.startup_success_patterns) == 2
        assert result.technology_detected == "FastAPI"


class TestIterativeDockerfileResult:
    """Test IterativeDockerfileResult schema."""
    
    def test_creation(self):
        """Test creating iterative result."""
        result = IterativeDockerfileResult(
            thought_process="Fixed build error",
            previous_issues_addressed=["Missing dependency"],
            dockerfile="FROM python:3.11-slim\nRUN apt-get update && apt-get install -y libpq-dev",
            changes_summary=["Added libpq-dev installation"],
            confidence_in_fix="high",
            fallback_strategy="Try using full Python image",
            project_type="service"
        )
        
        assert "libpq-dev" in result.dockerfile
        assert result.confidence_in_fix == "high"

