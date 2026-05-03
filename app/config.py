from pathlib import Path
from typing import Annotated
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

GpioPin = Annotated[int, Field(ge=0, le=27)]


class Settings(BaseSettings):
    port: int = 8000
    base_url: str = ""
    camera_stream_url: str = ""
    motor_speed_default: Annotated[float, Field(ge=0.0, le=1.0)] = 0.75
    pan_servo_pin: GpioPin = 12
    tilt_servo_pin: GpioPin = 13
    buzzer_pin: GpioPin = 18
    obstacle_threshold_cm: Annotated[float, Field(gt=0.0)] = 20.0
    api_username: str = ""
    api_password: str = ""
    motor_rate_limit: Annotated[int, Field(ge=0)] = 20
    session_secret_key: Annotated[str, Field(min_length=32)] = "dev-only-secret-change-in-production-min-32ch"
    data_dir: Path = Path.home() / ".local" / "share" / "robocar"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("camera_stream_url")
    @classmethod
    def must_be_http(cls, v: str) -> str:
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("camera_stream_url must start with http:// or https://")
        return v


settings = Settings()
