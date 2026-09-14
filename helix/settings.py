"""One place for configuration. Every value comes from the environment or .env (pydantic-settings), with the same
names the rest of the code has always used, so `os.getenv("CRITIC_MODEL")` and `settings.critic_model` agree.

    from helix.settings import settings
    settings.provider()            -> "anthropic" | "wandb" | "openai" | "litellm"
    settings.llm_available()       -> True if any generative-model key is set
"""
from __future__ import annotations
import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=os.path.join(ROOT, ".env"), env_file_encoding="utf-8", extra="ignore", case_sensitive=False)

    # generative models (helix/llm.py)
    llm_provider: str | None = Field(default=None, alias="LLM_PROVIDER")           # anthropic | wandb | openai | litellm; auto if unset
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-sonnet-5", alias="ANTHROPIC_MODEL")
    wandb_api_key: str | None = Field(default=None, alias="WANDB_API_KEY")
    wandb_model: str = Field(default="Qwen/Qwen3-235B-A22B-Instruct-2507", alias="WANDB_MODEL")
    wandb_entity: str = Field(default="", alias="WANDB_ENTITY")
    wandb_project: str = Field(default="helix", alias="WANDB_PROJECT")
    wandb_entity_project: str | None = Field(default=None, alias="WANDB_ENTITY_PROJECT")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    litellm_model: str | None = Field(default=None, alias="LITELLM_MODEL")           # e.g. "openai/Qwen/Qwen3-235B-A22B-Instruct-2507"

    # roles
    critic_model: str | None = Field(default=None, alias="CRITIC_MODEL")
    architect_model: str | None = Field(default=None, alias="ARCHITECT_MODEL")
    architect_models: str = Field(default="deepseek-ai/DeepSeek-V3.1,Qwen/Qwen3-235B-A22B-Instruct-2507", alias="ARCHITECT_MODELS")
    jury_a: str = Field(default="deepseek-ai/DeepSeek-V3.1", alias="JURY_A")
    jury_b: str = Field(default="openai/gpt-oss-120b", alias="JURY_B")
    jury_c: str = Field(default="moonshotai/Kimi-K2.6", alias="JURY_C")

    # guardrails
    max_sections: int = Field(default=3, alias="MAX_SECTIONS")
    max_words: int = Field(default=900, alias="MAX_WORDS")

    # verification and graph
    typesafe_api_key: str | None = Field(default=None, alias="TYPESAFE_API_KEY")
    ncbi_email: str = Field(default="", alias="NCBI_EMAIL")
    helix_ner: str = Field(default="regex", alias="HELIX_NER")                       # regex | gliner
    helix_embeddings: str = Field(default="minishlab/potion-base-8M", alias="HELIX_EMBEDDINGS")

    # mcp
    helix_mcp_host: str = Field(default="0.0.0.0", alias="HELIX_MCP_HOST")
    helix_mcp_port: int = Field(default=8765, alias="HELIX_MCP_PORT")
    helix_mcp_token: str | None = Field(default=None, alias="HELIX_MCP_TOKEN")

    WANDB_INFERENCE: str = "https://api.inference.wandb.ai/v1"

    def provider(self) -> str:
        if self.llm_provider:
            return self.llm_provider
        if self.anthropic_api_key:
            return "anthropic"
        if self.wandb_api_key:
            return "wandb"
        return "openai"

    def llm_available(self) -> bool:
        return bool(self.anthropic_api_key or self.wandb_api_key or self.openai_api_key or self.litellm_model)

    def typesafe_available(self) -> bool:
        return bool(self.typesafe_api_key)

    def architects(self) -> list[str]:
        return [m for m in self.architect_models.split(",") if m]


settings = Settings()
