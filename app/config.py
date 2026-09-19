from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_base_url: str = "http://localhost:11434/v1"
    llm_model: str = "llama3"
    llm_api_key: str = "ollama"
    met_office_api_key: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
