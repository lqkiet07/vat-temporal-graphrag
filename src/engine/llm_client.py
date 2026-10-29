"""LLM client supporting local Ollama, Google Gemini API, and OpenAI API."""
from collections.abc import Iterator
import json
import os
from json import JSONDecodeError
from urllib.error import URLError
import urllib.request


def check_ollama_available(
    host: str = "http://localhost:11434",
    timeout: float = 2.0,
) -> bool:
    """Check if the local Ollama service is reachable."""
    req = urllib.request.Request(host, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status == 200
    except (URLError, OSError, TimeoutError):
        return False


def _call_gemini_api(prompt: str, api_key: str, model: str = "gemini-2.5-flash", timeout: float = 30.0) -> str | None:
    """Call Google Gemini REST API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048}
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    return parts[0].get("text")
    except Exception as e:
        print(f"Gemini API call failed: {e}")
        return None
    return None


def _call_openai_api(prompt: str, api_key: str, model: str = "gpt-4o-mini", timeout: float = 30.0) -> str | None:
    """Call OpenAI Chat Completions API."""
    url = "https://api.openai.com/v1/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": "Bạn là Trợ lý Pháp lý Thuế GTGT Việt Nam chuyên nghiệp."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
    }).encode("utf-8")
    
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content")
    except Exception as e:
        print(f"OpenAI API call failed: {e}")
        return None
    return None


def _call_ollama(prompt: str, model: str = "qwen2.5:7b", host: str = "http://localhost:11434", timeout: float = 30.0) -> str | None:
    """Generate a response from Ollama API using the specified prompt and model."""
    url = f"{host}/api/generate"
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
            res = data.get("response")
            return str(res) if res is not None else None
    except (URLError, OSError, TimeoutError, JSONDecodeError):
        return None


def generate_llm_response(
    prompt: str,
    model: str = "qwen2.5:7b",
    host: str = "http://localhost:11434",
    timeout: float = 30.0,
) -> str | None:
    """Generate a response using Ollama API, with optional Gemini/OpenAI cloud provider."""
    # 1. Check Gemini API key if configured
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        res = _call_gemini_api(prompt, gemini_key, timeout=timeout)
        if res:
            return res

    # 2. Check OpenAI API key if configured
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        res = _call_openai_api(prompt, openai_key, timeout=timeout)
        if res:
            return res

    # 3. Direct Ollama invocation
    return _call_ollama(prompt, model=model, host=host, timeout=timeout)


def generate_llm_response_stream(
    prompt: str,
    model: str = "qwen2.5:7b",
    host: str = "http://localhost:11434",
    timeout: float = 120.0,
) -> Iterator[str]:
    """Stream response chunks from Ollama, yielding text fragments as they arrive.

    Ollama answers a streaming request with NDJSON: one JSON object per line. Any
    transport or decoding failure ends the stream silently so callers can fall back
    to a deterministic answer instead of surfacing a 500.
    """
    url = f"{host}/api/generate"
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": True,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            for raw_line in response:
                chunk = _parse_stream_chunk(raw_line)
                if chunk is None:
                    continue
                token = chunk.get("response")
                if token:
                    yield str(token)
                if chunk.get("done"):
                    return
    except (URLError, OSError, TimeoutError, JSONDecodeError):
        return


def _parse_stream_chunk(raw_line: bytes) -> dict | None:
    """Decode a single NDJSON line of an Ollama stream, skipping malformed lines."""
    line = raw_line.decode("utf-8", errors="replace").strip()
    if not line:
        return None
    try:
        chunk = json.loads(line)
    except JSONDecodeError:
        return None
    return chunk if isinstance(chunk, dict) else None

