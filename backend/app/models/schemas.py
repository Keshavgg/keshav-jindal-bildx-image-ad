from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator


class GenerationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationRequest(BaseModel):
    """
    Structured product context and image URL provided by the user.
    """
    image_url: HttpUrl = Field(
        ...,
        description="Publicly reachable product image URL",
        examples=["https://bildx.ai/samples/assets/roam-front.webp"]
    )
    product_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the product",
        examples=["ROAM Lock 750"]
    )
    product_description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Factual product description",
        examples=["A 750 ml insulated steel tumbler with a locking sip lid."]
    )
    target_audience: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Intended customer segment or audience",
        examples=["Commuters, gym users and day hikers"]
    )
    key_benefits: List[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of factual key benefits provided in the product context",
        examples=[["Up to 12 hours cold", "Carry loop", "Locking lid"]]
    )
    tone: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Desired advertising tone",
        examples=["Adventurous and practical"]
    )


class CreativeCopy(BaseModel):
    """
    Grounded creative copy generated for the ad with strictly enforced word count limits.
    """
    headline: str = Field(
        ...,
        description="Headline (strictly up to 8 words)"
    )
    supporting_text: str = Field(
        ...,
        description="Supporting copy (strictly up to 20 words)"
    )
    cta: str = Field(
        ...,
        description="Call to action (strictly up to 4 words)"
    )
    visual_direction: str = Field(
        ...,
        description="Visual style or scene direction for the background"
    )

    @field_validator("headline")
    @classmethod
    def validate_headline_words(cls, v: str) -> str:
        words = v.strip().split()
        if len(words) > 8:
            raise ValueError(f"Headline must not exceed 8 words (found {len(words)}: '{v}')")
        if len(words) == 0:
            raise ValueError("Headline cannot be empty")
        return v.strip()

    @field_validator("supporting_text")
    @classmethod
    def validate_supporting_words(cls, v: str) -> str:
        words = v.strip().split()
        if len(words) > 20:
            raise ValueError(f"Supporting text must not exceed 20 words (found {len(words)}: '{v}')")
        if len(words) == 0:
            raise ValueError("Supporting text cannot be empty")
        return v.strip()

    @field_validator("cta")
    @classmethod
    def validate_cta_words(cls, v: str) -> str:
        words = v.strip().split()
        if len(words) > 4:
            raise ValueError(f"CTA must not exceed 4 words (found {len(words)}: '{v}')")
        if len(words) == 0:
            raise ValueError("CTA cannot be empty")
        return v.strip()


class GenerationMetadata(BaseModel):
    """
    Audit trail and operational metadata for the generation.
    """
    model: str
    prompt_version: str
    source_url: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    retry_count: int = 0


class GenerationStatusResponse(BaseModel):
    """
    Real-time status returned to the client.
    """
    task_id: str
    status: GenerationStatus
    idempotency_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    retry_count: int = 0
    error_message: Optional[str] = None
    creative_copy: Optional[CreativeCopy] = None
    ad_image_url: Optional[str] = None
    metadata: Optional[GenerationMetadata] = None


class HealthResponse(BaseModel):
    status: str
    provider: str
    active_tasks: int
    queue_capacity: int
    max_concurrent_calls: int
