"""
Pydantic DTOs for type-safe data transfer
Provides validation and serialization between layers
"""
from pydantic import BaseModel, Field, field_validator, ConfigDict
from decimal import Decimal
from datetime import datetime
from uuid import UUID
from typing import Optional


class ProductDTO(BaseModel):
    """Type-safe DTO for Product - used in service layer"""

    sku: str = Field(min_length=1, max_length=255)
    name: str = Field(default="")
    description: str = Field(default="")
    price: Optional[Decimal] = Field(default=None, ge=0)
    active: bool = Field(default=True)
    category_id: Optional[int] = None

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, v: str) -> str:
        return v.strip()

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < 0:
            raise ValueError("Price must be non-negative")
        return v

    model_config = ConfigDict(from_attributes=True)


class ProductCreateDTO(BaseModel):
    """DTO for creating products via API"""

    sku: str = Field(min_length=1, max_length=255)
    name: str = Field(default="")
    description: str = Field(default="")
    price: Optional[Decimal] = Field(default=None, ge=0)
    active: bool = Field(default=True)
    category_id: Optional[int] = None
    tag_ids: list[int] = Field(default_factory=list)


class ProductResponseDTO(BaseModel):
    """DTO for product API responses"""

    id: int
    sku: str
    name: str
    description: str
    price: Optional[Decimal]
    active: bool
    category_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImportJobDTO(BaseModel):
    """Type-safe DTO for ImportJob"""

    id: UUID
    filename: str
    status: str
    stage: str
    total_rows: Optional[int]
    processed_rows: int
    created_count: int
    updated_count: int
    error_count: int
    percent: float = 0.0
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_model(cls, job):
        """Create DTO from Django model with calculated percent"""
        return cls(
            id=job.id,
            filename=job.filename,
            status=job.status,
            stage=job.stage,
            total_rows=job.total_rows,
            processed_rows=job.processed_rows,
            created_count=job.created_count,
            updated_count=job.updated_count,
            error_count=job.error_count,
            percent=job.percent_complete,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error=job.error,
        )


class ImportResultDTO(BaseModel):
    """DTO for import completion result"""

    job_id: UUID
    total_rows: int
    created_count: int
    updated_count: int
    error_count: int
    duration_seconds: float


class PresignedUploadDTO(BaseModel):
    """DTO for presigned upload response"""

    job_id: UUID
    upload_url: str
    fields: dict[str, str]
    expires_in: int = 3600


class ImportProgressDTO(BaseModel):
    """DTO for progress notifications"""

    job_id: UUID
    status: str
    stage: str
    processed_rows: int
    total_rows: Optional[int]
    percent: float
    created_count: int = 0
    updated_count: int = 0

