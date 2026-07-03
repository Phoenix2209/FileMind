# schema.py
# Pydantic v2 data models used throughout FileMind.
# These validate LLM output and define the shape of the final report.

from __future__ import annotations
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class FileSummary(BaseModel):
    """Summary produced by the LLM for a single file."""

    filename:     str  = Field(..., description="Original filename")
    filepath:     str  = Field(..., description="Absolute path to the file")
    file_type:    str  = Field(..., description="Extension, e.g. .csv")
    file_size_kb: float = Field(..., description="File size in kilobytes")

    # LLM-generated fields
    data_summary: str        = Field(default="", description="1-2 sentence summary")
    key_points:   list[str]  = Field(default_factory=list, description="3-5 bullet points")
    entities:     str        = Field(default="", description="Notable entities found")
    word_count:   int        = Field(default=0, description="Approx word/row count")

    # Status
    success: bool            = Field(default=True)
    error:   Optional[str]   = Field(default=None)

    @field_validator("key_points", mode="before")
    @classmethod
    def ensure_list(cls, v):
        if isinstance(v, str):
            return [v]
        return v or []

    @field_validator("word_count", mode="before")
    @classmethod
    def ensure_int(cls, v):
        try:
            return int(v)
        except (TypeError, ValueError):
            return 0


class GlobalSummary(BaseModel):
    """Synthesised summary across all files."""

    global_summary: str       = Field(default="", description="Combined overview")
    common_themes:  list[str] = Field(default_factory=list)
    top_insights:   list[str] = Field(default_factory=list)

    @field_validator("common_themes", "top_insights", mode="before")
    @classmethod
    def ensure_list(cls, v):
        return v if isinstance(v, list) else []


class SummaryReport(BaseModel):
    """Full report returned by the summarizer."""

    prompt:         str              = Field(..., description="User's original task description")
    total_files:    int              = Field(..., description="Number of files processed")
    processed:      int              = Field(..., description="Files successfully summarised")
    failed:         int              = Field(default=0)
    model_used:     str              = Field(..., description="Ollama model name")
    files:          list[FileSummary]= Field(default_factory=list)
    global_summary: GlobalSummary    = Field(default_factory=GlobalSummary)

    def to_dict(self) -> dict:
        return self.model_dump()