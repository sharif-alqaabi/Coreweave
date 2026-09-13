"""One chat() function for every model call in Helix, so the provider is a config choice.

    LLM_PROVIDER=wandb      -> W&B Inference (OpenAI-compatible), auth = WANDB_API_KEY
    LLM_PROVIDER=openai     -> any OpenAI-compatible endpoint: OPENAI_BASE_URL + OPENAI_API_KEY
    LLM_PROVIDER=anthropic  -> Anthropic SDK, auth = ANTHROPIC_API_KEY

    chat(system, user, model=None, max_tokens=800) -> str
"""
import os

WANDB_INFERENCE = "https://api.inference.wandb.ai/v1"


def provider():
    p = os.getenv("LLM_PROVIDER")
    if p:
        return p
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("WANDB_API_KEY"):
        return "wandb"
    return "openai"


def chat(system, user, model=None, max_tokens=800, temperature=0.0, json_mode=False):
    """json_mode is accepted for compatibility with the older agents; prompts already ask for JSON."""
    p = provider()
    if p == "anthropic":
        import anthropic
        msg = anthropic.Anthropic().messages.create(
            model=model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5"), max_tokens=max_tokens,
            temperature=temperature, system=system, messages=[{"role": "user", "content": user}])
        return msg.content[0].text
    import openai
    if p == "wandb":
        # W&B Inference needs the OpenAI-Project header as "entity/project" for auth + usage tracking
        proj = os.getenv("WANDB_ENTITY_PROJECT") or f"{os.getenv('WANDB_ENTITY', '')}/{os.getenv('WANDB_PROJECT', 'helix')}"
        client = openai.OpenAI(base_url=WANDB_INFERENCE, api_key=os.environ["WANDB_API_KEY"], project=proj)
        model = model or os.getenv("WANDB_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
    else:
        client = openai.OpenAI(base_url=os.getenv("OPENAI_BASE_URL"), api_key=os.environ["OPENAI_API_KEY"])
        model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    r = client.chat.completions.create(model=model, max_tokens=max_tokens, temperature=temperature,
                                       messages=[{"role": "system", "content": system},
                                                 {"role": "user", "content": user}])
    return r.choices[0].message.content
