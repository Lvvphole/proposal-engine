from contracts.parse import ParseResult
from integrations.extend import ExtendClient


def run_parse_pipeline(file_url: str, file_name: str, config: dict | None = None) -> ParseResult:
    client = ExtendClient()
    result = client.parse_pdf_sync(file_url=file_url, file_name=file_name, config=config)

    if result.status.upper() not in {"PROCESSED", "COMPLETED", "SUCCESS"}:
        raise RuntimeError(f"Extend parse failed or incomplete: {result.status}")

    if not result.chunks:
        raise RuntimeError("Extend parse returned no chunks")

    return result
