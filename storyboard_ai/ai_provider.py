"""AI provider abstraction.

Story-planning (text) models are configured here. Image-generation models are a separate, future
concern and are deliberately NOT selected here.

Configuration (environment variables, never stored in project files):
  OPENAI_API_KEY          required for AI mode
  STORYBOARD_AI_MODEL     story-planning model (default: DEFAULT_MODEL)
  STORYBOARD_AI_TIMEOUT   seconds per request (default 120)
  STORYBOARD_AI_API       'responses' (default) or 'chat' for Chat-Completions-only compatible servers
  OPENAI_BASE_URL         optional, read by the OpenAI SDK itself
"""

import json
import os
import random
import time

from .schema import to_strict

DEFAULT_MODEL = "gpt-5-mini"
MODEL_SUGGESTIONS = ["gpt-5-mini", "gpt-5", "gpt-5.1", "gpt-4.1", "gpt-4.1-mini", "gpt-4o"]


class AIProviderError(Exception):
    """kind: config | auth | timeout | network | rate_limit | api | refusal | bad_response | cancelled"""

    def __init__(self, kind, message, retryable=False):
        super().__init__(message)
        self.kind = kind
        self.retryable = retryable

    def user_message(self):
        hints = {
            "config": "Set the OPENAI_API_KEY environment variable and restart the app.",
            "auth": "Check that OPENAI_API_KEY is valid and has access to the selected model.",
            "timeout": "The AI service did not respond in time. Try again, or raise STORYBOARD_AI_TIMEOUT.",
            "network": "Could not reach the AI service. Check your internet connection or proxy.",
            "rate_limit": "Rate limit or quota reached. Wait a moment, or check your plan and billing.",
            "refusal": "The model declined this request. Try rephrasing the message.",
            "bad_response": "The model returned data that could not be used.",
        }
        hint = hints.get(self.kind, "")
        return f"{self}\n\n{hint}".strip()


class AIProvider:
    name = "base"
    model = ""

    def generate_json(self, system, user, schema, schema_name):
        """Return a dict that the provider believes matches `schema` (caller still validates)."""
        raise NotImplementedError

    def describe(self):
        return {"provider": self.name, "model": self.model}


def api_key_available():
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def openai_sdk_available():
    try:
        import openai  # noqa: F401
        return True
    except ImportError:
        return False


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, model=None, api_key=None, timeout=None, max_retries=3, api_style=None,
                 client=None, sleep=time.sleep):
        self.model = (model or os.environ.get("STORYBOARD_AI_MODEL") or DEFAULT_MODEL).strip()
        self.timeout = float(timeout or os.environ.get("STORYBOARD_AI_TIMEOUT") or 120)
        self.max_retries = max(0, int(max_retries))
        self.api_style = (api_style or os.environ.get("STORYBOARD_AI_API") or "responses").strip().lower()
        self._sleep = sleep
        if client is not None:
            self.client = client
            return
        try:
            import openai
        except ImportError:
            raise AIProviderError("config", "The 'openai' package is not installed. Run: pip install -r requirements.txt")
        key = api_key or os.environ.get("OPENAI_API_KEY", "").strip()
        if not key:
            raise AIProviderError("config", "No OpenAI API key found (OPENAI_API_KEY is not set).")
        # SDK retries disabled: retries are bounded and classified below.
        self.client = openai.OpenAI(api_key=key, timeout=self.timeout, max_retries=0)

    # ---- error classification
    @staticmethod
    def classify(exc):
        try:
            import openai
        except ImportError:  # pragma: no cover
            return AIProviderError("api", str(exc))
        if isinstance(exc, openai.APITimeoutError):
            return AIProviderError("timeout", "The AI request timed out.", retryable=True)
        if isinstance(exc, openai.APIConnectionError):
            return AIProviderError("network", f"Network error contacting the AI service: {exc}", retryable=True)
        if isinstance(exc, (openai.AuthenticationError, openai.PermissionDeniedError)):
            return AIProviderError("auth", f"Authentication failed: {_api_msg(exc)}")
        if isinstance(exc, openai.RateLimitError):
            msg = _api_msg(exc)
            quota = "insufficient_quota" in msg or "quota" in msg.lower()
            return AIProviderError("rate_limit", f"Rate limit / quota error: {msg}", retryable=not quota)
        if isinstance(exc, openai.NotFoundError):
            return AIProviderError("api", f"Model or endpoint not found: {_api_msg(exc)}")
        if isinstance(exc, openai.BadRequestError):
            return AIProviderError("api", f"The AI service rejected the request: {_api_msg(exc)}")
        if isinstance(exc, openai.InternalServerError):
            return AIProviderError("api", f"AI service error: {_api_msg(exc)}", retryable=True)
        if isinstance(exc, openai.APIStatusError):
            return AIProviderError("api", f"AI service error ({exc.status_code}): {_api_msg(exc)}",
                                   retryable=exc.status_code >= 500)
        return AIProviderError("api", f"Unexpected AI error: {exc}")

    def _call(self, system, user, schema, schema_name):
        strict = to_strict(schema)
        if self.api_style == "chat":
            r = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                response_format={"type": "json_schema",
                                 "json_schema": {"name": schema_name, "schema": strict, "strict": True}})
            msg = r.choices[0].message
            if getattr(msg, "refusal", None):
                raise AIProviderError("refusal", f"Model refusal: {msg.refusal}")
            return msg.content or ""
        r = self.client.responses.create(
            model=self.model, instructions=system, input=user,
            text={"format": {"type": "json_schema", "name": schema_name, "schema": strict, "strict": True}})
        for item in getattr(r, "output", None) or []:
            for part in getattr(item, "content", None) or []:
                if getattr(part, "type", "") == "refusal":
                    raise AIProviderError("refusal", f"Model refusal: {getattr(part, 'refusal', '')}")
        if getattr(r, "status", "completed") == "incomplete":
            reason = getattr(getattr(r, "incomplete_details", None), "reason", "unknown")
            raise AIProviderError("bad_response", f"The model response was incomplete ({reason}).")
        return getattr(r, "output_text", "") or ""

    def generate_json(self, system, user, schema, schema_name):
        attempt = 0
        while True:
            try:
                text = self._call(system, user, schema, schema_name)
                break
            except AIProviderError:
                raise
            except Exception as exc:  # SDK errors -> classified, bounded retry
                err = self.classify(exc)
                if not err.retryable or attempt >= self.max_retries:
                    if attempt:
                        err.args = (f"{err} (after {attempt + 1} attempts)",)
                    raise err from exc
                self._sleep(min(30.0, 2 ** attempt + random.uniform(0, 0.5)))
                attempt += 1
        return parse_json_text(text)


def parse_json_text(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{"):] if "{" in text else text
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise AIProviderError("bad_response", f"The model returned malformed JSON ({e.msg} at char {e.pos}).")
    if not isinstance(data, dict):
        raise AIProviderError("bad_response", "The model returned JSON that is not an object.")
    return data


def _api_msg(exc):
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        err = body.get("error", body)
        if isinstance(err, dict) and err.get("message"):
            return f"{err['message']} [{err.get('code') or err.get('type') or ''}]".replace(" []", "")
    return getattr(exc, "message", None) or str(exc)


class MockProvider(AIProvider):
    """Deterministic provider for tests and offline development.

    `responses` is a list consumed in order; each item is a dict (returned), a str (parsed as JSON,
    so malformed strings exercise repair paths), an Exception (raised), or a callable
    (schema_name, system, user) -> any of the above.
    """
    name = "mock"

    def __init__(self, responses, model="mock-model"):
        self.responses = list(responses)
        self.model = model
        self.calls = []

    def generate_json(self, system, user, schema, schema_name):
        self.calls.append({"schema_name": schema_name, "system": system, "user": user})
        if not self.responses:
            raise AIProviderError("api", "MockProvider ran out of responses.")
        r = self.responses.pop(0)
        if callable(r) and not isinstance(r, Exception):
            r = r(schema_name, system, user)
        if isinstance(r, Exception):
            raise r
        if isinstance(r, str):
            return parse_json_text(r)
        return json.loads(json.dumps(r))
