from pydantic import BaseModel, Field
from typing import List, Optional


class QuoteCreate(BaseModel):
    text: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    tags: List[str] = []


class QuoteUpdate(BaseModel):
    text: Optional[str] = None
    author: Optional[str] = None
    tags: Optional[List[str]] = None