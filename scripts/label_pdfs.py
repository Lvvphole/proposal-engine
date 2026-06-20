"""Golden dataset labeling tool.

CLI tool for creating ground-truth labels from real supplier quotes.
Extracts text from PDFs, runs a candidate extraction, and prompts
the human labeler for corrections.

Usage:
    python scripts/label_pdfs.py <pdf_path> --suite line_items
    python scripts/label_pdfs.py <pdf_path> --suite classifier
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text content from a PDF file."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(str(pdf_path))
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        return text.strip()
    except ImportError:
        print("PyMuPDF not installed. Install with: pip install pymupdf")
        sys.exit(1)


def prompt_for_label(text: str, suite: str) -> dict | None:
    """Interactive labeling session.

    Shows extracted text and prompts the user to provide ground truth.
    """
    print("\n" + "=" * 60)
    print("DOCUMENT TEXT (first 2000 chars):")
    print("=" * 60)
    print(text[:2000])
    print("=" * 60)

    if suite == "classifier":
        print("\nClassification Label:")
        print("  Formats: structured_table, semi_structured, unstructured")
        print("  Pipelines: a, b, c")

        fmt = input("  Format: ").strip()
        pipeline = input("  Pipeline: ").strip()

        if not fmt or not pipeline:
            print("Skipped.")
            return None

        tags = input("  Tags (comma-separated): ").strip().split(",")
        tags = [t.strip() for t in tags if t.strip()]

        return {
            "expected": {"format": fmt, "pipeline": pipeline},
            "tags": tags,
        }

    elif suite == "line_items":
        print("\nLine Item Labels:")
        print("  Enter items one per line as: description | qty | unit_price | extended_price")
        print("  Empty line to finish.")

        items = []
        while True:
            line = input("  > ").strip()
            if not line:
                break
            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 4:
                print("  Expected 4 fields separated by |")
                continue
            items.append(
                {
                    "description": parts[0],
                    "quantity": float(parts[1]),
                    "unit_price": float(parts[2]),
                    "extended_price": float(parts[3]),
                }
            )

        if not items:
            print("Skipped.")
            return None

        tags = input("  Tags (comma-separated): ").strip().split(",")
        tags = [t.strip() for t in tags if t.strip()]

        return {
            "expected": {"line_items": items},
            "tags": tags,
        }

    else:
        print(f"Unknown suite: {suite}")
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Label supplier quote PDFs for golden datasets")
    parser.add_argument("pdf_path", type=Path, help="Path to the PDF file")
    parser.add_argument("--suite", required=True, choices=["classifier", "line_items", "recovery"])
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output .jsonl file (default: eval/goldens/<suite>_v1.jsonl)",
    )
    args = parser.parse_args()

    if not args.pdf_path.exists():
        print(f"File not found: {args.pdf_path}")
        return 1

    output_path = args.output or Path(f"eval/goldens/{args.suite}_v1.jsonl")

    # Extract text
    text = extract_text_from_pdf(args.pdf_path)
    if not text:
        print("No text extracted from PDF.")
        return 1

    # Get label from human
    label = prompt_for_label(text, args.suite)
    if label is None:
        return 0

    # Count existing entries to generate ID
    existing = 0
    if output_path.exists():
        with output_path.open() as f:
            existing = sum(1 for line in f if line.strip())

    prefix = args.suite[:3]
    case_id = f"{prefix}-{existing + 1:03d}"

    entry = {
        "id": case_id,
        "input": text[:5000],  # Truncate for storage
        **label,
    }

    with output_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")

    print(f"\nSaved as {case_id} to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
