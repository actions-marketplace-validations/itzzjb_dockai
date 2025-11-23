import json
from unittest.mock import patch, MagicMock
from dockai.analyzer import analyze_repo_needs

@patch("dockai.analyzer.OpenAI")
def test_analyze_repo_needs(mock_openai):
    # Setup mock response
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({
        "stack": "Python/Flask",
        "files_to_read": ["requirements.txt", "app.py"]
    })
    mock_client.chat.completions.create.return_value = mock_response
    
    # Run function
    result = analyze_repo_needs(["requirements.txt", "app.py", "README.md"])
    
    # Assertions
    assert result["stack"] == "Python/Flask"
    assert "requirements.txt" in result["files_to_read"]
    mock_client.chat.completions.create.assert_called_once()
