# FileMind — AI File Summarizer (Offline)

Reads TXT, CSV, JSON, MD, JPEG/PNG files and summarises them into a
unified report using a **local LLM via Ollama** — no internet required.

---

## Project Structure

```
filemind/
├── main.py          ← CLI entry point (run this)
├── config.py        ← Model names, paths, prompts
├── schema.py        ← Pydantic data models
├── file_reader.py   ← Reads all file types incl. JPEG
├── llm_client.py    ← Ollama REST API wrapper
├── summarizer.py    ← Orchestrates the full pipeline
├── display.py       ← Rich terminal table output
├── requirements.txt
└── sample_data/     ← Test files
```

---

## Setup

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Install Ollama
Download from https://ollama.com and install for your OS.

### 3. Pull a text model
```bash
ollama pull llama3          # good general model
# OR
ollama pull mistral         # lighter, fast
# OR
ollama pull phi3            # very lightweight
```

### 4. Pull a vision model (for JPEG/PNG)
```bash
ollama pull llava           # multimodal vision model
# OR
ollama pull llava-phi3      # lighter vision model
```

### 5. Start Ollama server
```bash
ollama serve
```

---

## Usage

```bash
# Summarize a folder of files
python main.py sample_data/

# Specific files with a custom prompt
python main.py file1.txt file2.csv photo.jpg -p "Summarize football match stats"

# Recursive folder scan
python main.py data/ -r -p "Extract player names and scores"

# Check Ollama connection
python main.py --check

# Use a different model
python main.py data/ --model mistral

# Don't save JSON report
python main.py data/ --no-save
```

---

## Changing the Model

Edit `config.py`:
```python
OLLAMA_MODEL        = "llama3"    # text model
OLLAMA_VISION_MODEL = "llava"     # image model
```

Or pass `--model <name>` at runtime.

---

## Output

- **Terminal**: Rich table with per-file breakdown + global summary panel
- **JSON file**: `output/summary_report.json` (full structured data)

---

## Supported File Types

| Extension      | Reader          |
|----------------|-----------------|
| .txt .md .log  | Plain text      |
| .csv .tsv      | CSV parser      |
| .json .jsonl   | JSON parser     |
| .jpeg .jpg .png| Vision LLM      |
