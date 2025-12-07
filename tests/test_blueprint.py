import pytest
from unittest.mock import MagicMock, patch
from dockai.core.schemas import BlueprintResult, PlanningResult, RuntimeConfigResult, HealthEndpointDetectionResult
from dockai.agents.agent_functions import create_blueprint
from dockai.core.agent_context import AgentContext

@pytest.fixture
def mock_context():
    context = MagicMock(spec=AgentContext)
    context.file_contents = "def main():\n    print('Hello World')"
    context.analysis_result = {
        "stack": "Python",
        "project_type": "script"
    }
    context.retry_history = []
    return context

@patch("dockai.agents.agent_functions.create_llm")
@patch("dockai.agents.agent_functions.safe_invoke_chain")
def test_create_blueprint(mock_invoke, mock_create_llm, mock_context):
    # Setup mock LLM
    mock_llm = MagicMock()
    mock_create_llm.return_value = mock_llm
    mock_llm.with_structured_output.return_value = MagicMock()
    
    # Setup mock result
    mock_plan = PlanningResult(
        thought_process="Planning thought process...",
        base_image_strategy="python:3.11-slim",
        build_strategy="Single-stage build",
        optimization_priorities=["Size"],
        potential_challenges=["None"],
        mitigation_strategies=["None"],
        lessons_applied=[],
        use_multi_stage=False,
        use_minimal_runtime=True,
        use_static_linking=False,
        estimated_image_size="100MB"
    )
    
    mock_runtime = RuntimeConfigResult(
        thought_process="Runtime thought process...",
        primary_health_endpoint=None,
        health_confidence="none",
        startup_success_patterns=["Started"],
        startup_failure_patterns=["Failed"],
        estimated_startup_time=5,
        max_wait_time=30
    )
    
    expected_result = BlueprintResult(
        thought_process="Analysis...",
        plan=mock_plan,
        runtime_config=mock_runtime
    )
    
    mock_invoke.return_value = expected_result
    
    # Execute
    result, usage = create_blueprint(mock_context)
    
    # Verify
    assert isinstance(result, BlueprintResult)
    assert result.plan.base_image_strategy == "python:3.11-slim"
    assert len(result.runtime_config.startup_success_patterns) == 1
    
    # Verify LLM was called with correct context
    mock_create_llm.assert_called_with(agent_name="blueprint", temperature=0.2)
    mock_invoke.assert_called_once()
    call_args = mock_invoke.call_args[0][1]
    assert call_args["stack"] == "Python"
    assert call_args["file_contents"] == "def main():\n    print('Hello World')"
