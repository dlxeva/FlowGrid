"""LLM client for Framing Ledger - calls LLM API for decision extraction.

Supported providers: openai, anthropic, custom (OpenAI-compatible), local (OpenAI-compatible local).
"""

import json
import os
from typing import Optional

import httpx
from rich.console import Console

console = Console()

# Default LLM configuration
DEFAULT_CONFIG = {
    "provider": "openai",  # openai, anthropic, custom, or local
    "model": "gpt-4o-mini",
    "temperature": 0.3,
    "max_tokens": 4096,
}

# Supported provider values for --llm flag
VALID_PROVIDERS = {"openai", "anthropic", "custom", "local"}


def get_llm_config() -> dict:
    """Get LLM configuration from environment variables."""
    config = DEFAULT_CONFIG.copy()
    
    # Provider
    if provider := os.getenv("FLG_LLM_PROVIDER"):
        config["provider"] = provider.lower()
    
    # Model
    if model := os.getenv("FLG_LLM_MODEL"):
        config["model"] = model
    
    # Temperature
    if temp := os.getenv("FLG_LLM_TEMPERATURE"):
        try:
            config["temperature"] = float(temp)
        except ValueError:
            pass
    
    # Max tokens
    if max_tokens := os.getenv("FLG_LLM_MAX_TOKENS"):
        try:
            config["max_tokens"] = int(max_tokens)
        except ValueError:
            pass
    
    return config


def get_api_key(provider: str) -> Optional[str]:
    """Get API key for the specified provider."""
    env_vars = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "custom": "FLG_LLM_API_KEY",
        "local": "FLG_LLM_API_KEY",  # local uses same env var as custom
    }

    env_var = env_vars.get(provider, "FLG_LLM_API_KEY")
    return os.getenv(env_var)


def get_base_url(provider: str) -> str:
    """Get base URL for the specified provider."""
    # Check for custom base URL first
    if custom_url := os.getenv("FLG_LLM_BASE_URL"):
        return custom_url

    # Default URLs
    urls = {
        "openai": "https://api.openai.com/v1",
        "anthropic": "https://api.anthropic.com",
        "local": "http://localhost:11434/v1",  # Ollama default
    }

    return urls.get(provider, "https://api.openai.com/v1")


def call_openai(prompt: str, config: dict) -> str:
    """Call OpenAI API."""
    api_key = get_api_key("openai")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    base_url = get_base_url("openai")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": "You are a decision extraction expert. Extract decisions from conversation transcripts and format them according to the 9-field template."},
            {"role": "user", "content": prompt},
        ],
        "temperature": config["temperature"],
        "max_tokens": config["max_tokens"],
    }
    
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def call_anthropic(prompt: str, config: dict) -> str:
    """Call Anthropic API."""
    api_key = get_api_key("anthropic")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    
    base_url = get_base_url("anthropic")
    
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": config["model"],
        "max_tokens": config["max_tokens"],
        "messages": [
            {"role": "user", "content": prompt},
        ],
        "temperature": config["temperature"],
    }
    
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            f"{base_url}/v1/messages",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]


def call_custom_api(prompt: str, config: dict) -> str:
    """Call custom API (OpenAI-compatible)."""
    api_key = get_api_key("custom")
    base_url = get_base_url("custom")
    
    if not api_key:
        raise ValueError("FLG_LLM_API_KEY environment variable not set")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": "You are a decision extraction expert."},
            {"role": "user", "content": prompt},
        ],
        "temperature": config["temperature"],
        "max_tokens": config["max_tokens"],
    }
    
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def call_llm(prompt: str, provider: Optional[str] = None) -> str:
    """Call LLM API with the given prompt.

    Args:
        prompt: The prompt to send to the LLM
        provider: Override provider (openai, anthropic, custom, local)

    Returns:
        LLM response text

    Raises:
        ValueError: If API key is not set
        httpx.HTTPStatusError: If API call fails
    """
    config = get_llm_config()

    if provider:
        provider = provider.lower()
        if provider not in VALID_PROVIDERS:
            raise ValueError(f"Unknown provider: {provider}. Supported: {', '.join(sorted(VALID_PROVIDERS))}")
        config["provider"] = provider

    provider = config["provider"]

    console.print(f"[dim]Calling {provider} API ({config['model']})...[/dim]")

    try:
        if provider == "openai":
            return call_openai(prompt, config)
        elif provider == "anthropic":
            return call_anthropic(prompt, config)
        elif provider in ("custom", "local"):
            return call_custom_api(prompt, config)
        else:
            raise ValueError(f"Unknown provider: {provider}. Supported: {', '.join(sorted(VALID_PROVIDERS))}")
    except httpx.HTTPStatusError as e:
        console.print(f"[red]API Error: {e.response.status_code} - {e.response.text}[/red]")
        raise
    except Exception as e:
        console.print(f"[red]LLM Error: {e}[/red]")
        raise


def is_llm_available(provider: Optional[str] = None) -> bool:
    """Check if any LLM provider is configured and available.

    Args:
        provider: Specific provider to check. If None, checks all.

    Returns:
        True if at least one provider has its API key set.
    """
    if provider:
        return get_api_key(provider) is not None

    # Check all providers
    providers_to_check = ["openai", "anthropic", "custom", "local"]
    for p in providers_to_check:
        if get_api_key(p):
            return True

    # Also check if FLG_LLM_BASE_URL is set (custom endpoint might not need key)
    if os.getenv("FLG_LLM_BASE_URL"):
        return True

    return False


def parse_llm_response(response: str) -> list[dict]:
    """Parse LLM response into structured decisions.

    Supports two formats:
    1. JSON array of decisions with fields: content, type, confidence, reasoning,
       rejected_alternatives, reversal_conditions
    2. Markdown D-XXX sections (legacy format)

    Returns:
        List of decision dicts with keys: id, content (and other structured fields
        if available from JSON parsing).
    """
    # --- Try JSON first (preferred format) ---
    json_found, decisions = _parse_json_decisions(response)
    if json_found:
        return decisions  # may be empty list if no decisions found

    # --- Fallback to markdown D-XXX parsing ---
    return _parse_markdown_decisions(response)


def _parse_json_decisions(response: str) -> tuple[bool, list[dict]]:
    """Try to parse JSON-format decisions from LLM response.

    Returns:
        (json_found, decisions) — json_found=True if valid JSON was detected
        (even if empty), False if no JSON was found and caller should fallback.
    """
    json_text = response.strip()
    try:
        data = json.loads(json_text)
        if isinstance(data, dict) and "decisions" in data:
            data = data["decisions"]
        if isinstance(data, list):
            decisions = []
            for i, d in enumerate(data):
                if isinstance(d, dict) and "what" in d:
                    decisions.append({
                        "id": d.get("id", f"D-LLM-{i+1:03d}"),
                        "content": d.get("what", ""),
                        "type": d.get("type", "llm_extracted"),
                        "confidence": d.get("confidence", "medium"),
                        "reasoning": d.get("why", ""),
                        "rejected_alternatives": d.get("rejected", ""),
                        "reversal_conditions": d.get("reverse_condition", ""),
                        "related_goals": d.get("related_goals", ""),
                    })
            # JSON was valid — return even if empty list
            return True, decisions
        # Valid JSON but not a list/decisions dict — treat as unfound
        return False, []
    except (json.JSONDecodeError, TypeError):
        pass

    # Try to extract JSON block from markdown
    import re
    json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', response, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            if isinstance(data, dict) and "decisions" in data:
                data = data["decisions"]
            if isinstance(data, list):
                decisions = []
                for i, d in enumerate(data):
                    if isinstance(d, dict) and "what" in d:
                        decisions.append({
                            "id": d.get("id", f"D-LLM-{i+1:03d}"),
                            "content": d.get("what", ""),
                            "type": d.get("type", "llm_extracted"),
                            "confidence": d.get("confidence", "medium"),
                            "reasoning": d.get("why", ""),
                            "rejected_alternatives": d.get("rejected", ""),
                            "reversal_conditions": d.get("reverse_condition", ""),
                            "related_goals": d.get("related_goals", ""),
                        })
                return True, decisions
        except (json.JSONDecodeError, TypeError):
            pass

    return False, []


def _parse_markdown_decisions(response: str) -> list[dict]:
    """Parse markdown D-XXX format decisions (legacy)."""
    decisions = []
    current_decision = None
    current_content = []

    for line in response.split("\n"):
        # Check for decision header (## D-XXX | title)
        if line.startswith("## D-") and "|" in line:
            # Save previous decision
            if current_decision:
                decisions.append({
                    "id": current_decision,
                    "content": "\n".join(current_content).strip(),
                })

            # Start new decision
            parts = line.split("|", 1)
            current_decision = parts[0].strip().replace("## ", "")
            current_content = [line]
        elif current_decision:
            current_content.append(line)

    # Save last decision
    if current_decision:
        decisions.append({
            "id": current_decision,
            "content": "\n".join(current_content).strip(),
        })

    # If no D-XXX found, try to parse as single decision
    if not decisions and response.strip() and "本轮对话无明确决策" not in response and "no decision" not in response.lower():
        decisions.append({
            "id": "D-NEW",
            "content": response.strip(),
        })

    return decisions
