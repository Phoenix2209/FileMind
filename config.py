# config.py
# Central configuration for FileMind.
# Change OLLAMA_MODEL to whichever model you have pulled locally.

from pathlib import Path

# ── Ollama (offline LLM) ───────────────────────────────────────────────────
OLLAMA_BASE_URL: str = "http://localhost:11434"   # default Ollama port
OLLAMA_MODEL:    str = "llama3"                   # change to: mistral, phi3, gemma, etc.
OLLAMA_TIMEOUT:  int = 120                        # seconds per LLM call

# ── Vision model (for JPEG/image files) ───────────────────────────────────
# Must be a multimodal model you have pulled, e.g. "llava", "llava-phi3"
OLLAMA_VISION_MODEL: str = "llava"

# ── File handling ──────────────────────────────────────────────────────────
SUPPORTED_EXTENSIONS: set[str] = {
    ".txt", ".md", ".log",          # plain text
    ".csv", ".tsv",                  # tabular
    ".json", ".jsonl",               # structured
    ".jpeg", ".jpg", ".png",        # images (vision model)
    ".pdf",        
}

# Max characters read from a single text file before truncating
MAX_CHARS_PER_FILE: int = 12_000

# ── Output ─────────────────────────────────────────────────────────────────
OUTPUT_DIR: Path = Path("output")   # summary JSON saved here
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Prompts ────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are a precise data analyst. The user will give you the contents of one file.
Your job:
1. Write a 1-2 sentence data summary of what the file contains.
2. Extract 3-5 key points as short bullet strings.
3. List notable entities (names, numbers, dates, teams, scores, etc.) as a comma-separated string.
4. Count approximate words/rows.

Respond ONLY with valid JSON — no markdown, no explanation — using this exact schema:
{
  "data_summary": "string",
  "key_points": ["string", ...],
  "entities": "string",
  "word_count": integer
}
"""

GLOBAL_SUMMARY_PROMPT = """\
You are a data analyst. Below are per-file summaries from {n} files.
Write a unified global summary (3-5 sentences) covering the main findings across ALL files.
Also list up to 5 common themes and up to 5 top insights.

Respond ONLY with valid JSON:
{
  "global_summary": "string",
  "common_themes": ["string", ...],
  "top_insights": ["string", ...]
}

Per-file data:
{summaries}
"""