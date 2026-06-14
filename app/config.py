from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str = "a_very_secret_key_for_jwt_auth_change_in_production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    database_url: str = "sqlite+aiosqlite:///./bible_quiz.db"

    class Config:
        env_file = ".env"

settings = Settings()
