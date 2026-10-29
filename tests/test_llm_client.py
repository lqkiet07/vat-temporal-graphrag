import json
from unittest.mock import MagicMock, patch
from urllib.error import URLError
import pytest

from src.engine.llm_client import check_ollama_available, generate_llm_response


def test_check_ollama_available_success():
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.getcode.return_value = 200
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        assert check_ollama_available() is True


def test_check_ollama_available_failure():
    with patch("urllib.request.urlopen", side_effect=URLError("Connection refused")):
        assert check_ollama_available() is False


def test_generate_llm_response_success():
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"response": "Issue: test\\nRule: test", "done": true}'
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = generate_llm_response("Test prompt")
        assert result == "Issue: test\nRule: test"


@pytest.mark.parametrize("error", [TimeoutError("timed out"), URLError("Connection refused")])
def test_generate_llm_response_timeout_or_error(error):
    with patch("urllib.request.urlopen", side_effect=error):
        result = generate_llm_response("Test prompt")
        assert result is None


def test_generate_llm_response_sends_correct_payload():
    mock_resp = MagicMock()
    mock_resp.read.return_value = b'{"response": "OK", "done": true}'
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        generate_llm_response(prompt="Hello", model="qwen2.5:7b", host="http://localhost:11434")

        assert mock_urlopen.called
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "http://localhost:11434/api/generate"
        assert req.get_header("Content-type") == "application/json"

        body = json.loads(req.data.decode("utf-8"))
        assert body == {
            "model": "qwen2.5:7b",
            "prompt": "Hello",
            "stream": False,
        }
