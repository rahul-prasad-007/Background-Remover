from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Defaults tuned for ~8GB RAM Windows PCs (auto-downscale, never hard-crash)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Shankar Card AI Image Enhancer"
    performance_profile: str = "low"

    max_file_size_mb: int = 20
    allowed_extensions: set[str] = {".png", ".jpg", ".jpeg", ".webp"}
    upload_dir: Path = Path(__file__).resolve().parent.parent / "uploads"
    output_dir: Path = Path(__file__).resolve().parent.parent / "outputs"
    weights_dir: Path = Path(__file__).resolve().parent.parent / "weights"

    # Comma-separated, e.g. https://myapp.onrender.com,http://localhost:5173
    cors_origins: str = Field(
        default=(
            "http://localhost:5173,http://127.0.0.1:5173,"
            "http://localhost:3000,http://127.0.0.1:3000"
        )
    )
    device: str = "cpu"

    bg_provider: str = "local"
    birefnet_model: str = "birefnet-general-lite"
    birefnet_max_side: int = 768
    birefnet_pad: int = 24

    remove_bg_api_key: str = ""
    remove_bg_size: str = "hd"
    remove_bg_type: str = "auto"
    remove_bg_timeout: float = 120.0
    remove_bg_max_upload_side: int = 2500

    safe_input_side: int = 1600

    realesrgan_scale: int = 2
    realesrgan_tile: int = 128
    realesrgan_threads: int = 2
    realesrgan_fast_4x: bool = True
    realesrgan_4x_max_input: int = 720
    realesrgan_2x_max_input: int = 1000
    use_torch_realesrgan: bool = True

    gfpgan_upscale: int = 1
    max_process_side: int = 1000
    hd_min_side: int = 99999
    max_output_side: int = 2800

    preload_models: bool = False
    use_gfpgan_model: bool = False
    unload_models_after_use: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def apply_profile_defaults(self) -> None:
        if self.performance_profile.lower() == "quality":
            self.safe_input_side = 2400
            self.max_process_side = 1600
            self.max_output_side = 4096
            self.realesrgan_tile = 192
            self.realesrgan_2x_max_input = 1400
            self.realesrgan_4x_max_input = 1000
            self.birefnet_max_side = 1024
            self.birefnet_pad = 32
            self.use_gfpgan_model = True
            self.max_file_size_mb = 20
            self.remove_bg_size = "full"
            self.remove_bg_max_upload_side = 4000


settings = Settings()
settings.apply_profile_defaults()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.output_dir.mkdir(parents=True, exist_ok=True)
settings.weights_dir.mkdir(parents=True, exist_ok=True)
