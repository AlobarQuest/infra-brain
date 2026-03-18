from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    app_name: str = "infra-brain"
    app_env: str = "development"
    log_level: str = "INFO"
    port: int = 8000
    allowed_hosts: str = "localhost"

    model_config = ConfigDict(env_file=".env", extra="ignore")


settings = Settings()
