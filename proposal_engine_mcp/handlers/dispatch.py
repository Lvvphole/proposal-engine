"""Centralized tool dispatch."""

from __future__ import annotations

from typing import Any


async def handle(name: str, args: dict) -> dict[str, Any]:
    if name == "submit_quote":
        from contracts.envelope import Envelope
        envelope = Envelope(
            source_filename=args["filename"],
            source_content_type=args.get("content_type", "application/pdf"),
            source_bytes_b64=args["content_b64"],
            contractor_id=args.get("contractor_id"),
        )
        return {"envelope_id": envelope.id, "status": envelope.status, "message": f"Quote '{args['filename']}' received."}

    elif name == "get_proposal_status":
        return {"envelope_id": args["envelope_id"], "status": "review_pending"}

    elif name == "list_recent_proposals":
        return {"proposals": [], "total": 0}

    elif name == "register_contractor":
        import uuid
        cid = str(uuid.uuid4())[:8]
        from rag.contractor_context import register_contractor
        register_contractor(cid, {"name": args["name"], "company": args.get("company", ""), "markup_rules": {"default_pct": args.get("default_markup_pct", 0.20)}, "payment_terms": args.get("payment_terms", "Due on completion")})
        return {"contractor_id": cid, "name": args["name"]}

    elif name == "list_contractors":
        from rag.contractor_context import list_contractors
        return {"contractors": list_contractors()}

    elif name == "get_contractor":
        from rag.contractor_context import get_context
        return get_context(args["contractor_id"])

    elif name == "register_supplier":
        from rag.supplier_catalog import register_supplier
        register_supplier(args["name"], preferred_pipeline=args.get("preferred_pipeline", "c"), notes=args.get("notes", ""))
        return {"name": args["name"], "preferred_pipeline": args.get("preferred_pipeline", "c")}

    elif name == "list_suppliers":
        from rag.supplier_catalog import list_suppliers
        return {"suppliers": list_suppliers()}

    return {"error": f"Unknown tool: {name}"}
