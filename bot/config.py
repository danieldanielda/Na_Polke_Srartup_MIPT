from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path("./.bot.env"), env_file_encoding="utf-8", extra="allow"
    )
    
    tg_api_key: str
    agents_api_base: str
    rag_collection_id: str = 'default'
    model_api_key: str
    model_api: str
    translate_model_name: str
    langfuse_secret_key: str
    langfuse_public_key: str
    langfuse_host: str
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_port: int
    postgres_db: str