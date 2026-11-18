"""Pydantic request models for the system configuration API."""

from typing import Any

from pydantic import BaseModel, Field, model_validator


class ConfigUpdateRequest(BaseModel):
    """Partial system-config update; only supplied keys are persisted."""

    values: dict[str, Any] = Field(default_factory=dict)


class ConfigResetRequest(BaseModel):
    """Reset one configuration section or all user overrides."""

    section: str | None = Field(default=None, min_length=1)
    all: bool = False

    @model_validator(mode="after")
    def require_exactly_one_scope(self) -> "ConfigResetRequest":
        if self.all and self.section is not None:
            raise ValueError("section and all are mutually exclusive")
        if not self.all and self.section is None:
            raise ValueError("section or all is required")
        return self
