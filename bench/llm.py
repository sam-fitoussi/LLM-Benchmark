"""Unified, logged, cost-tracked LLM calls for Anthropic, OpenAI and xAI."""
import json
import os
import threading
import time
import uuid

import anthropic
import openai

from .config import MODELS


class Budget:
    """Thread-safe running spend tracker with a hard cap."""

    def __init__(self, cap_usd: float, start: float = 0.0):
        self.cap = cap_usd
        self.spent = start
        self.calls = 0
        self.lock = threading.Lock()

    def add(self, usd: float):
        with self.lock:
            self.spent += usd
            self.calls += 1

    def exhausted(self) -> bool:
        return self.spent >= self.cap


class CallLogger:
    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()

    def log(self, rec: dict):
        with self.lock, open(self.path, "a") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


_clients = {}
_clients_lock = threading.Lock()


def _client(provider):
    with _clients_lock:
        if provider not in _clients:
            if provider == "anthropic":
                _clients[provider] = anthropic.Anthropic(max_retries=0)
            elif provider == "openai":
                _clients[provider] = openai.OpenAI(max_retries=0)
            else:
                base, key = {"xai": ("https://api.x.ai/v1", "XAI_API_KEY"),
                             "mistral": ("https://api.mistral.ai/v1", "MISTRAL_API_KEY"),
                             "moonshot": ("https://api.moonshot.ai/v1", "MOONSHOT_API_KEY")}[provider]
                _clients[provider] = openai.OpenAI(base_url=base, api_key=os.environ[key], max_retries=0,
                                                   timeout=300)
        return _clients[provider]


def call(model_key: str, system: str, user: str, *, budget: Budget, logger: CallLogger,
         meta: dict, max_tokens: int = 4000) -> dict:
    """Returns dict(text, status, usage, cost, ...). status in ok | refusal | error."""
    cfg = MODELS[model_key]
    prov = cfg["provider"]
    max_tokens = max(max_tokens, cfg.get("max_tokens", 0))
    pin, pcache, pout = cfg["price"]
    rec = dict(call_id=uuid.uuid4().hex[:12], ts=time.time(), model_key=model_key,
               api_model=cfg["model"], kwargs=cfg["kwargs"], system=system, user=user, **meta)
    last_err = None
    for attempt in range(6):
        t0 = time.time()
        try:
            if prov == "anthropic":
                r = _client(prov).messages.create(
                    model=cfg["model"], max_tokens=max_tokens,
                    system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                    messages=[{"role": "user", "content": user}], **cfg["kwargs"])
                text = "".join(b.text for b in r.content if b.type == "text")
                thinking_text = "\n".join(getattr(b, "thinking", "") or "" for b in r.content if b.type == "thinking")
                u = r.usage
                cache_read = u.cache_read_input_tokens or 0
                cache_write = u.cache_creation_input_tokens or 0
                inp = u.input_tokens
                out = u.output_tokens
                cost = (inp * pin + cache_read * pcache + cache_write * pin * 1.25 + out * pout) / 1e6
                status = "refusal" if r.stop_reason == "refusal" else "ok"
                extra = dict(stop_reason=r.stop_reason, reasoning_text=thinking_text or None,
                             stop_details=(r.stop_details.model_dump() if getattr(r, "stop_details", None) else None))
                usage = dict(input=inp, cache_read=cache_read, cache_write=cache_write, output=out)
            else:
                lim = {"max_completion_tokens": max_tokens} if prov in ("openai", "xai") else {"max_tokens": max_tokens}
                r = _client(prov).chat.completions.create(
                    model=cfg["model"],
                    messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                    **lim, **cfg["kwargs"])
                ch = r.choices[0]
                content = ch.message.content
                reasoning_text = getattr(ch.message, "reasoning_content", None) or \
                    (ch.message.model_extra or {}).get("reasoning_content")
                if isinstance(content, list):  # Mistral reasoning models: [{"type":"thinking",...},{"type":"text",...}]
                    texts, thoughts = [], []
                    for part in content:
                        part = part if isinstance(part, dict) else getattr(part, "__dict__", {})
                        if part.get("type") == "text":
                            texts.append(part.get("text", ""))
                        elif part.get("type") == "thinking":
                            for t in part.get("thinking", []) or []:
                                thoughts.append(t.get("text", "") if isinstance(t, dict) else str(t))
                    text = "".join(texts)
                    reasoning_text = "\n".join(thoughts) or reasoning_text
                else:
                    text = content or ""
                u = r.usage
                cached = getattr(getattr(u, "prompt_tokens_details", None), "cached_tokens", 0) or 0
                reasoning = getattr(getattr(u, "completion_tokens_details", None), "reasoning_tokens", 0) or 0
                inp = u.prompt_tokens - cached
                out = u.completion_tokens
                # xAI reports reasoning tokens separately from completion tokens
                if prov == "xai":
                    out = u.completion_tokens + reasoning
                cost = (inp * pin + cached * pcache + out * pout) / 1e6
                refusal = getattr(ch.message, "refusal", None)
                status = "refusal" if refusal or ch.finish_reason == "content_filter" else "ok"
                extra = dict(stop_reason=ch.finish_reason, refusal_text=refusal, reasoning_text=reasoning_text)
                usage = dict(input=inp, cache_read=cached, output=out, reasoning=reasoning)
            budget.add(cost)
            rec.update(status=status, text=text, usage=usage, cost=cost, latency=time.time() - t0,
                       attempt=attempt, **extra)
            logger.log(rec)
            return rec
        except (anthropic.RateLimitError, openai.RateLimitError, anthropic.APIConnectionError,
                openai.APIConnectionError, anthropic.InternalServerError, openai.InternalServerError,
                anthropic.APITimeoutError, openai.APITimeoutError) as e:
            last_err = repr(e)[:500]
            time.sleep(min(60, 2 ** attempt * 2))
        except (anthropic.APIStatusError, openai.APIStatusError) as e:
            code = getattr(e, "status_code", 0)
            last_err = repr(e)[:500]
            if code in (408, 409, 429, 529) or code >= 500:
                time.sleep(min(60, 2 ** attempt * 2))
                continue
            break
    rec.update(status="error", text="", error=last_err, cost=0.0)
    logger.log(rec)
    return rec
