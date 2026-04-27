from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db: str = "full_stack_data"
    redis_url: str = "redis://localhost:6379/0"
    redis_queue_key: str = "full_stack:due_jobs"
    scheduler_interval_seconds: float = 30.0
    worker_pool_size: int = 8


settings = Settings()
