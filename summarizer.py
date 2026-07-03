# summarizer.py
# Orchestrates the full pipeline:
#   discover/receive files → read → LLM summarize → global summary → SummaryReport

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Callable

from rich.console import Console
from rich.progress import (
    Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
)

from config import OLLAMA_MODEL, OUTPUT_DIR
from file_reader import FileReadResult, read_file, discover_files
from llm_client import (
    summarize_text_file,
    summarize_image_file,
    build_global_summary,
)
from schema import FileSummary, GlobalSummary, SummaryReport

console = Console()


# ── Main entry point ───────────────────────────────────────────────────────

def run_summary(
    paths:     list[Path],
    prompt:    str,
    recursive: bool = False,
    save_json: bool = True,
    log_fn:    Optional[Callable[[str, str], None]] = None,
) -> SummaryReport:
    """
    Full pipeline. Call this from main.py.

    Args:
        paths:     List of file paths OR folder paths (folders are scanned).
        prompt:    User's task description string.
        recursive: Recurse into sub-folders when scanning directories.
        save_json: Whether to save the JSON report to OUTPUT_DIR.
        log_fn:    Optional GUI log function(message, tag) for live updates.

    Returns:
        A validated SummaryReport instance.
    """

    def log(msg: str, tag: str = ""):
        """Log to GUI if available, else print to terminal."""
        if log_fn:
            log_fn(msg, tag)
        else:
            print(msg, end="")

    # ── 1. Resolve all file paths ──────────────────────────────────────────
    all_files: list[Path] = []
    for p in paths:
        if p.is_dir():
            found = discover_files(p, recursive=recursive)
            all_files.extend(found)
            log(f"  📁 Scanned {p.name}: {len(found)} file(s) found\n", "muted")
        elif p.is_file():
            all_files.append(p)
        else:
            log(f"  ⚠ Skipping (not found): {p}\n", "yellow")

    if not all_files:
        log("  No supported files found.\n", "red")
        return _empty_report(prompt)

    log(f"\n→ {len(all_files)} file(s) to process\n\n", "accent")

    # ── 2. Read + summarize each file ──────────────────────────────────────
    file_summaries: list[FileSummary] = []
    summaries_for_global: list[dict] = []

    for i, fp in enumerate(all_files, start=1):
        log(f"  [{i}/{len(all_files)}] Processing {fp.name}…\n", "muted")

        # Read
        result: FileReadResult = read_file(fp)

        if not result.success:
            fs = FileSummary(
                filename=result.filename,
                filepath=result.filepath,
                file_type=result.file_type,
                file_size_kb=result.file_size_kb,
                success=False,
                error=result.error,
            )
            file_summaries.append(fs)
            log(f"     ❌ {result.error}\n", "red")
            continue

        # Summarize via LLM
        try:
            if result.is_image:
                llm_data = summarize_image_file(result.image_b64, prompt)
            else:
                llm_data = summarize_text_file(result.text, prompt)
        except Exception as exc:
            llm_data = {}
            log(f"     ⚠ LLM error: {exc}\n", "red")

        fs = FileSummary(
            filename=result.filename,
            filepath=result.filepath,
            file_type=result.file_type,
            file_size_kb=result.file_size_kb,
            data_summary=llm_data.get("data_summary", ""),
            key_points=llm_data.get("key_points", []),
            entities=llm_data.get("entities", ""),
            word_count=llm_data.get("word_count", 0),
        )
        file_summaries.append(fs)
        summaries_for_global.append({
            "filename":     fs.filename,
            "data_summary": fs.data_summary,
            "key_points":   fs.key_points,
            "entities":     fs.entities,
        })
        log(f"     ✓ Done\n", "green")

    # ── 3. Global summary ──────────────────────────────────────────────────
    log("\n→ Generating global summary…\n", "accent")
    global_data: dict = {}
    if summaries_for_global:
        try:
            global_data = build_global_summary(
                summaries_for_global, prompt, n=len(summaries_for_global)
            )
        except Exception as exc:
            log(f"  ⚠ Global summary failed: {exc}\n", "red")

    global_summary = GlobalSummary(
        global_summary=global_data.get("global_summary", ""),
        common_themes=global_data.get("common_themes", []),
        top_insights=global_data.get("top_insights", []),
    )

    # ── 4. Build report ────────────────────────────────────────────────────
    successful = [f for f in file_summaries if f.success]
    failed     = [f for f in file_summaries if not f.success]

    report = SummaryReport(
        prompt=prompt,
        total_files=len(all_files),
        processed=len(successful),
        failed=len(failed),
        model_used=OLLAMA_MODEL,
        files=file_summaries,
        global_summary=global_summary,
    )

    # ── 5. Save JSON ───────────────────────────────────────────────────────
    if save_json:
        out_path = OUTPUT_DIR / "summary_report.json"
        out_path.write_text(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return report


# ── Helpers ────────────────────────────────────────────────────────────────

def _empty_report(prompt: str) -> SummaryReport:
    return SummaryReport(
        prompt=prompt,
        total_files=0,
        processed=0,
        model_used=OLLAMA_MODEL,
    )