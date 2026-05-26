from integrations.extend.client import normalize_parse_response


def test_normalize_extend_parse_response() -> None:
    raw = {
        "id": "pr_test",
        "file": {"id": "file_test", "name": "quote.pdf"},
        "status": "PROCESSED",
        "output": {
            "chunks": [
                {
                    "id": "chunk_1",
                    "type": "page",
                    "content": "Quote total 100.00",
                    "metadata": {"pageRange": {"start": 1, "end": 1}},
                    "blocks": [
                        {
                            "id": "block_1",
                            "type": "text",
                            "content": "Quote total 100.00",
                            "metadata": {"page": {"number": 1}},
                            "boundingBox": {"left": 0, "top": 0, "right": 10, "bottom": 10},
                            "polygon": []
                        }
                    ]
                }
            ]
        },
        "metrics": {"pageCount": 1, "processingTimeMs": 100},
        "usage": {"credits": 2}
    }

    result = normalize_parse_response(raw)

    assert result.provider == "extend"
    assert result.parse_run_id == "pr_test"
    assert result.page_count == 1
    assert result.usage_credits == 2
    assert result.chunks[0].blocks[0].page_number == 1
