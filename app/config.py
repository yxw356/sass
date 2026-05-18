from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    vllm_base_url: str = "http://127.0.0.1:8000/v1"
    vllm_api_key: str = "vllm_api_key_12345"
    vllm_model: str = "Qwen3.6-35B-A3B"
    vllm_context_window: int = 32768

    chroma_path: str = "./chroma_db"
    chroma_collection: str = "kb_documents"
    upload_dir: str = "./data/uploads"

    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_local_files_only: bool = False
    similarity_top_k: int = 5

    app_host: str = "0.0.0.0"
    app_port: int = 8080

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir)

    @property
    def chroma_path_resolved(self) -> Path:
        return Path(self.chroma_path)

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def default_local_embedding_dir(self) -> Path:
        return self.project_root / "models" / "bge-small-zh-v1.5"

    @property
    def embedding_model_resolved(self) -> str:
        configured = Path(self.embedding_model)
        if configured.is_dir():
            return str(configured.resolve())
        local_default = self.default_local_embedding_dir
        if local_default.is_dir():
            return str(local_default.resolve())
        return self.embedding_model

    @property
    def embedding_use_local_files_only(self) -> bool:
        if self.embedding_local_files_only:
            return True
        return Path(self.embedding_model_resolved).is_dir()


settings = Settings()
