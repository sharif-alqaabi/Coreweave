"""One chat() function for every generative model call in Helix, so the provider is a config choice.

    LLM_PROVIDER=wandb      -> W&B Inference (OpenAI-compatible), auth = WANDB_API_KEY
    LLM_PROVIDER=openai     -> any OpenAI-compatible endpoint: OPENAI_BASE_URL + OPENAI_API_KEY
    LLM_PROVIDER=anthropic  -> Anthropic SDK, auth = ANTHROPIC_API_KEY
    LLM_PROVIDER=litellm    -> LiteLLM, any of its ~100 providers; model = LITELLM_MODEL (e.g. "openai/Qwen/..." with
                               OPENAI_BASE_URL set to W&B Inference, or "anthropic/claude-sonnet-5", or "ollama/llama3")

    chat(system, user, model=None, max_tokens=800) -> str
    chat_typed(system, user, Schema, ...) -> Schema      validated structured output (Instructor); the critic uses this
"""
import json, re
from helix.settings import settings

WANDB_INFERENCE = settings.WANDB_INFERENCE


def provider():
    return settings.provider()


def _openai_client():
    import openai
    p = provider()
    if p == "wandb":
        # W&B Inference needs the OpenAI-Project header as "entity/project" for auth + usage tracking
        proj = settings.wandb_entity_project or f"{settings.wandb_entity}/{settings.wandb_project}"
        return openai.OpenAI(base_url=WANDB_INFERENCE, api_key=settings.wandb_api_key, project=proj), settings.wandb_model
    return openai.OpenAI(base_url=settings.openai_base_url, api_key=settings.openai_api_key), settings.openai_model


def _litellm_kwargs(model):
    """LiteLLM routes on the model prefix; an OpenAI-compatible endpoint (W&B Inference) is 'openai/<model>' + api_base."""
    kw = {"model": model or settings.litellm_model or f"openai/{settings.wandb_model}"}
    if kw["model"].startswith("openai/") and (settings.openai_base_url or settings.wandb_api_key):
        kw["api_base"] = settings.openai_base_url or WANDB_INFERENCE
        kw["api_key"] = settings.openai_api_key or settings.wandb_api_key
        if not settings.openai_base_url:
            proj = settings.wandb_entity_project or f"{settings.wandb_entity}/{settings.wandb_project}"
            kw["extra_headers"] = {"OpenAI-Project": proj}
    return kw


def chat(system, user, model=None, max_tokens=800, temperature=0.0, json_mode=False):
    """json_mode asks the provider for a JSON object where supported; prompts already ask for JSON."""
    p = provider()
    if p == "anthropic":
        import anthropic
        msg = anthropic.Anthropic().messages.create(
            model=model or settings.anthropic_model, max_tokens=max_tokens,
            temperature=temperature, system=system, messages=[{"role": "user", "content": user}])
        return msg.content[0].text
    if p == "litellm":
        import litellm
        r = litellm.completion(**_litellm_kwargs(model), max_tokens=max_tokens, temperature=temperature,
                               messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                               **({"response_format": {"type": "json_object"}} if json_mode else {}))
        return r.choices[0].message.content or ""
    import openai
    client, default = _openai_client()
    model = model or default
    try:
        r = client.chat.completions.create(model=model, max_tokens=max_tokens, temperature=temperature,
                                           messages=[{"role": "system", "content": system},
                                                     {"role": "user", "content": user}],
                                           **({"response_format": {"type": "json_object"}} if json_mode else {}))
    except openai.APIStatusError as e:
        if e.status_code in (402, 429) and "quota" in str(e).lower():
            raise SystemExit(f"\n[{p}] model quota exhausted for {model}. Add credits (W&B: https://wandb.ai/subscriptions -> Billing, "
                             "pay-as-you-go) or set LLM_PROVIDER/OPENAI_BASE_URL/OPENAI_API_KEY to another provider.\n") from None
        raise
    msg = r.choices[0].message
    return msg.content or getattr(msg, "reasoning_content", None) or ""   # some models put text elsewhere


def parse_typed(text, schema):
    """Fallback for providers without structured output: the first JSON object in the text, validated against the schema."""
    for m in re.finditer(r"\{.*?\}", text, re.S):
        try:
            return schema.model_validate(json.loads(m.group()))
        except Exception:
            continue
    raise ValueError(f"no {schema.__name__} in model output: {text[:120]!r}")


def chat_typed(system, user, schema, model=None, max_tokens=800, temperature=0.0, max_retries=2):
    """A pydantic model back, validated; Instructor re-prompts the model with the validation error on a bad reply.
    Falls back to chat() + parse_typed() if Instructor is not installed or the provider has no structured mode."""
    p = provider()
    try:
        import instructor
    except ImportError:
        return parse_typed(chat(system, user, model=model, max_tokens=max_tokens, temperature=temperature, json_mode=True), schema)
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    if p == "anthropic":
        import anthropic
        client = instructor.from_anthropic(anthropic.Anthropic())
        return client.messages.create(model=model or settings.anthropic_model, max_tokens=max_tokens, temperature=temperature,
                                      system=system, messages=msgs[1:], response_model=schema, max_retries=max_retries)
    if p == "litellm":
        import litellm
        client = instructor.from_litellm(litellm.completion, mode=instructor.Mode.JSON)
        return client.chat.completions.create(**_litellm_kwargs(model), max_tokens=max_tokens, temperature=temperature,
                                              messages=msgs, response_model=schema, max_retries=max_retries)
    raw, default = _openai_client()
    client = instructor.from_openai(raw, mode=instructor.Mode.JSON)        # JSON mode works on non-OpenAI endpoints (W&B, Ollama)
    return client.chat.completions.create(model=model or default, max_tokens=max_tokens, temperature=temperature,
                                          messages=msgs, response_model=schema, max_retries=max_retries)
