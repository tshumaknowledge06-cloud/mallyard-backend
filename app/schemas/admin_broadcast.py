from typing import Literal

from pydantic import BaseModel, Field


class BroadcastRequest(BaseModel):
    audience: Literal[
        "all",
        "merchants",
        "delivery_partners",
        "customers",
    ]

    subject: str = Field(
        ...,
        min_length=1,
        max_length=200,
    )

    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
    )


class BroadcastResponse(BaseModel):
    message: str
    audience: str
    targeted: int
    sent: int
    failed: int