from pydantic import BaseModel, Field


class ParseBlock(BaseModel):
    id: str | None = None
    type: str
    content: str
    page_number: int | None = None
    bounding_box: dict | None = None
    polygon: list[dict] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ParseChunk(BaseModel):
    id: str | None = None
    type: str = "page"
    content: str
    page_start: int | None = None
    page_end: int | None = None
    blocks: list[ParseBlock] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ParseResult(BaseModel):
    provider: str = "extend"
    parse_run_id: str | None = None
    file_id: str | None = None
    file_name: str | None = None
    status: str
    chunks: list[ParseChunk]
    page_count: int | None = None
    processing_time_ms: int | None = None
    usage_credits: int | None = None
    raw: dict = Field(default_factory=dict)
