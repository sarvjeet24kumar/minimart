"""
Common Schemas
"""

from math import ceil
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.common.constants import NORMALIZATION_BYPASS_FIELDS


T = TypeVar("T")


class NormalizedModel(BaseModel):
    """
    Base model that automatically normalizes string inputs.
    
    """

    @model_validator(mode="before")
    @classmethod
    def normalize_strings(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        bypass_normalization = NORMALIZATION_BYPASS_FIELDS

        normalized = {}
        for key, value in data.items():
            if isinstance(value, str):
                value = value.strip()
                if key not in bypass_normalization:
                    value = value.lower()

            normalized[key] = value

        return normalized


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response schema."""

    total: int = Field(..., description="Total number of items")
    page: int = Field(..., description="Current page number (1-based)")
    size: int = Field(..., description="Number of items per page")
    pages: int = Field(default=0, description="Total number of pages")
    data: list[T]

    @model_validator(mode="after")
    def compute_pages(self) -> "PaginatedResponse":
        if self.pages == 0:
            self.pages = ceil(self.total / self.size) if self.total > 0 else 1
        return self

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    """Generic message response schema."""

    message: str
