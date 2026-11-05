"""Optional, provider-agnostic AI explanations.

The deterministic provider is always available. LLM providers only receive the
rule facts and the cited source snippet (never file system access) and their
output is stored as *advisory text*: it never replaces the deterministic
evidence, the citations, or generated code.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

import httpx

from ..config import Settings

SYSTEM_PROMPT = (
    "You explain legacy COBOL business rules to modernization engineers. "
    "Use only the facts and source snippet provided. Do not invent field names, line numbers or behaviour. "
    "If something is unclear from the snippet, say so. Answer in at most 120 words, plain text."
)


@dataclass
class Explanation:
    text: str
    provider: str
    model: str | None
    advisory: bool  # True for LLM output


class ExplanationProvider(Protocol):
    name: str

    def explain(self, rule: dict, snippet: str) -> Explanation: ...


class DeterministicProvider:
    name = "deterministic"

    def explain(self, rule: dict, snippet: str) -> Explanation:
        parts = [rule.get("description", "").rstrip(".") + "."]
        if rule.get("decision_tables"):
            for t in rule["decision_tables"]:
                parts.append(f"It evaluates {t['subject']} across {len(t['rows'])} branches (line {t['line']}).")
        for c in rule.get("conditions", [])[:4]:
            parts.append(f"When {c['text']} (line {c['line']}).")
        for c in rule.get("calculations", [])[:4]:
            parts.append(f"Calculation: {c['text']} (line {c['line']}).")
        if rule.get("inputs"):
            parts.append("Inputs: " + ", ".join(rule["inputs"][:10]) + ".")
        if rule.get("outputs"):
            parts.append("Outputs: " + ", ".join(rule["outputs"][:10]) + ".")
        return Explanation(" ".join(parts), self.name, None, advisory=False)


def _user_prompt(rule: dict, snippet: str) -> str:
    facts = {k: rule.get(k) for k in ("name", "description", "inputs", "outputs", "conditions", "calculations", "file", "line_start", "line_end")}
    return f"Rule facts (deterministic analysis):\n{json.dumps(facts, indent=1)[:4000]}\n\nCOBOL source:\n{snippet[:6000]}\n\nExplain the business intent."


class OpenAICompatibleProvider:
    """Any OpenAI-compatible /v1/chat/completions endpoint (hosted or local)."""

    name = "openai-compatible"

    def __init__(self, base_url: str, api_key: str | None, model: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def explain(self, rule: dict, snippet: str) -> Explanation:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": _user_prompt(rule, snippet)}],
            "temperature": 0,
        }
        r = httpx.post(f"{self.base_url}/chat/completions", json=body, headers=headers, timeout=self.timeout)
        r.raise_for_status()
        text = r.json()["choices"][0]["message"]["content"].strip()
        return Explanation(text, self.name, self.model, advisory=True)


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, api_key: str, model: str, timeout: float, base_url: str | None = None) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.base_url = (base_url or "https://api.anthropic.com").rstrip("/")

    def explain(self, rule: dict, snippet: str) -> Explanation:
        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        body = {"model": self.model, "max_tokens": 400, "system": SYSTEM_PROMPT, "messages": [{"role": "user", "content": _user_prompt(rule, snippet)}]}
        r = httpx.post(f"{self.base_url}/v1/messages", json=body, headers=headers, timeout=self.timeout)
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text").strip()
        return Explanation(text, self.name, self.model, advisory=True)


def get_provider(settings: Settings) -> ExplanationProvider:
    kind = settings.llm_provider.lower()
    if kind == "openai-compatible" and settings.llm_base_url and settings.llm_model:
        return OpenAICompatibleProvider(settings.llm_base_url, settings.llm_api_key, settings.llm_model, settings.llm_timeout_s)
    if kind == "anthropic" and settings.llm_api_key and settings.llm_model:
        return AnthropicProvider(settings.llm_api_key, settings.llm_model, settings.llm_timeout_s, settings.llm_base_url)
    return DeterministicProvider()
