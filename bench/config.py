"""Model registry and price table (USD per 1M tokens)."""

MODELS = {
    # key: provider, api model id, call kwargs, prices (in, cached_in, out)
    "claude-sonnet-5.5": dict(provider="anthropic", model="claude-sonnet-5-5",
                              # display=summarized only changes what is returned (a summary of the thinking), not behaviour
                              kwargs={"output_config": {"effort": "low"},
                                      "thinking": {"type": "adaptive", "display": "summarized"}},
                              price=(2.0, 0.2, 10.0)),
    "gpt-6.1-terra": dict(provider="openai", model="gpt-6.1-terra",
                          kwargs={"reasoning_effort": "low"},
                          price=(1.0, 0.05, 5.0)),
    "grok-4.3": dict(provider="xai", model="grok-4.3", kwargs={},
                     price=(1.25, 0.2, 2.5)),
    "grok-4.7": dict(provider="xai", model="grok-4.7", kwargs={},
                     price=(2.0, 0.2, 6.0)),
    # wave 2 additions (low reasoning effort, like the others). Prices are conservative estimates.
    "mistral-large-4": dict(provider="mistral", model="mistral-large-4",
                            kwargs={"reasoning_effort": "low"}, price=(2.0, 0.2, 6.0), max_tokens=8000),
    "kimi-k3": dict(provider="moonshot", model="kimi-k3",
                    kwargs={"reasoning_effort": "low"}, price=(3.0, 0.3, 15.0)),
    # wave 3 robustness check (Anthropic family)
    "claude-opus-5.5": dict(provider="anthropic", model="claude-opus-5-5",
                            kwargs={"output_config": {"effort": "low"},
                                    "thinking": {"type": "adaptive", "display": "summarized"}},
                            price=(4.0, 0.4, 20.0)),
    # cheap judge for message classification
    "claude-haiku-5.5": dict(provider="anthropic", model="claude-haiku-5-5",
                             kwargs={"output_config": {"effort": "low"}},
                             price=(0.10, 0.01, 0.50)),
}
