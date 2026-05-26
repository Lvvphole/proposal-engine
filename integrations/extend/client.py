from __future__ import annotations

import os
import httpx

from contracts.parse import ParseBlock, ParseChunk, ParseResult


EXTEND_BASE_URL = os.getenv("EXTEND_BASE_URL", "https://api.extend.ai")
EXTEND_API_VERSION = os.getenv("EXTEND_API_VERSION", "2026-02-09")


class ExtendClient:
    def __init__(self, api_key: str | None = None, timeout: float = 300.0) -> None:
        self.api_key = api_key or os.getenv("EXTEND_API_KEY")
        if not self.api_key:
            raise RuntimeError("EXTEND_API_KEY is required")
        self.timeout = timeout

    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "x-extend-api-version": EXTEND_API_VERSION,
            "Content-Type": "application/json",
        }

    def parse_pdf_sync(self, *, file_url: str, file_name: str, config: dict | None = None) -> ParseResult:
        payload: dict = {"file": {"name": file_name, "url": file_url}}
        if config:
            payload["config"] = config

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(
                f"{EXTEND_BASE_URL}/parse",
                headers=self.headers(),
                json=payload,
            )
            response.raise_for_status()

        return normalize_parse_response(response.json())


def normalize_parse_response(data: dict) -> ParseResult:
    output = data.get("output") or {}
    metrics = data.get("metrics") or {}
    usage = data.get("usage") or {}
    file_obj = data.get("file") or {}

    chunks: list[ParseChunk] = []
    for chunk in output.get("chunks", []):
        metadata = chunk.get("metadata") or {}
        page_range = metadata.get("pageRange") or {}

        blocks: list[ParseBlock] = []
        for block in chunk.get("blocks", []):
            block_metadata = block.get("metadata") or {}
            page = block_metadata.get("page") or {}
            blocks.append(
                ParseBlock(
                    id=block.get("id"),
                    type=block.get("type", "unknown"),
                    content=block.get("content", ""),
                    page_number=page.get("number"),
                    bounding_box=block.get("boundingBox"),
                    polygon=block.get("polygon") or [],
                    metadata=block_metadata,
                )
            )

        chunks.append(
            ParseChunk(
                id=chunk.get("id"),
                type=chunk.get("type", "page"),
                content=chunk.get("content", ""),
                page_start=page_range.get("start"),
                page_end=page_range.get("end"),
                blocks=blocks,
                metadata=metadata,
            )
        )

    return ParseResult(
        parse_run_id=data.get("id"),
        file_id=file_obj.get("id"),
        file_name=file_obj.get("name"),
        status=data.get("status", "UNKNOWN"),
        chunks=chunks,
        page_count=metrics.get("pageCount"),
        processing_time_ms=metrics.get("processingTimeMs"),
        usage_credits=usage.get("credits"),
        raw=data,
    )
