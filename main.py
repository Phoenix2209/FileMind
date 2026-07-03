#!/usr/bin/env python3
# main.py
# GUI entry point for FileMind using tkinter.
# Run with: python main.py

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk
from pathlib import Path

from llm_client import check_ollama_running, list_available_models
from summarizer import run_summary
from schema import SummaryReport
from docx_export import export_to_docx


# ── Colours & fonts ────────────────────────────────────────────────────────
BG          = "#0d0f14"
SURFACE     = "#161923"
BORDER      = "#252a38"
ACCENT      = "#4f8ef7"
GREEN       = "#3ecf8e"
RED         = "#f76f6f"
YELLOW      = "#f7c94f"
TEXT        = "#e2e8f0"
MUTED       = "#64748b"
FONT_MAIN   = ("Segoe UI", 10)
FONT_BOLD   = ("Segoe UI", 10, "bold")
FONT_TITLE  = ("Segoe UI", 16, "bold")
FONT_MONO   = ("Consolas", 9)


class FileMindApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FileMind — AI File Summarizer")
        self.geometry("900x680")
        self.configure(bg=BG)
        self.resizable(True, True)

        self._build_ui()
        self._check_ollama()

    # ── UI BUILD ───────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Header ────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=ACCENT, pady=14)
        header.pack(fill="x")

        tk.Label(
            header, text="  FileMind",
            font=("Segoe UI", 18, "bold"),
            bg=ACCENT, fg="white"
        ).pack(side="left", padx=16)

        tk.Label(
            header, text="AI-powered offline file summarizer",
            font=("Segoe UI", 10),
            bg=ACCENT, fg="#d0e4ff"
        ).pack(side="left")

        self.status_dot = tk.Label(
            header, text="● Checking Ollama…",
            font=FONT_MAIN, bg=ACCENT, fg=YELLOW
        )
        self.status_dot.pack(side="right", padx=16)

        # ── Main content ───────────────────────────────────────────────────
        content = tk.Frame(self, bg=BG, padx=24, pady=20)
        content.pack(fill="both", expand=True)

        # ── Folder row ────────────────────────────────────────────────────
        self._section_label(content, "📁  Folder to Search")

        folder_row = tk.Frame(content, bg=BG)
        folder_row.pack(fill="x", pady=(4, 12))

        self.folder_var = tk.StringVar(value="")
        folder_entry = tk.Entry(
            folder_row,
            textvariable=self.folder_var,
            font=FONT_MONO,
            bg=SURFACE, fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
        )
        folder_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))

        tk.Button(
            folder_row, text="Browse",
            font=FONT_BOLD,
            bg=ACCENT, fg="white",
            activebackground="#3a7de0",
            relief="flat", bd=0,
            padx=16, pady=6,
            cursor="hand2",
            command=self._browse_folder,
        ).pack(side="left")

        # ── Recursive checkbox ─────────────────────────────────────────────
        self.recursive_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            content,
            text="  Search subfolders too (recursive)",
            variable=self.recursive_var,
            font=FONT_MAIN,
            bg=BG, fg=MUTED,
            selectcolor=SURFACE,
            activebackground=BG,
            activeforeground=TEXT,
        ).pack(anchor="w", pady=(0, 14))

        # ── Prompt ────────────────────────────────────────────────────────
        self._section_label(content, "💬  What do you want to find / summarize?")

        self.prompt_text = tk.Text(
            content,
            font=FONT_MAIN,
            bg=SURFACE, fg=TEXT,
            insertbackground=TEXT,
            relief="flat", bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
            height=4,
            wrap="word",
        )
        self.prompt_text.pack(fill="x", pady=(4, 4), ipady=6)
        self.prompt_text.insert("1.0", "Summarize all documents and extract key information.")

        # ── Quick prompt buttons ───────────────────────────────────────────
        quick_frame = tk.Frame(content, bg=BG)
        quick_frame.pack(fill="x", pady=(4, 14))

        tk.Label(quick_frame, text="Quick:", font=FONT_MAIN, bg=BG, fg=MUTED).pack(side="left")

        for label, prompt in [
            ("Invoices",      "Summarize all invoices, extract totals and dates."),
            ("Research",      "Summarize research notes and extract key findings."),
            ("Football",      "Summarize football match stats, scores and top scorers."),
            ("Meeting Notes", "Summarize meeting notes and extract action items."),
        ]:
            tk.Button(
                quick_frame, text=label,
                font=("Segoe UI", 9),
                bg=SURFACE, fg=MUTED,
                activebackground=BORDER,
                relief="flat", bd=0,
                padx=10, pady=4,
                cursor="hand2",
                command=lambda p=prompt: self._set_prompt(p),
            ).pack(side="left", padx=(6, 0))

        # ── Run + Export buttons ─────────────────────────────────────────
        btn_row = tk.Frame(content, bg=BG)
        btn_row.pack(fill="x", pady=(0, 16))

        self.run_btn = tk.Button(
            btn_row,
            text="⚡  Analyze & Summarize",
            font=("Segoe UI", 11, "bold"),
            bg=GREEN, fg="#0d0f14",
            activebackground="#2eab76",
            relief="flat", bd=0,
            padx=24, pady=10,
            cursor="hand2",
            command=self._run,
        )
        self.run_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.export_btn = tk.Button(
            btn_row,
            text="📄  Export to Word",
            font=("Segoe UI", 11, "bold"),
            bg=SURFACE, fg=MUTED,
            activebackground=BORDER,
            relief="flat", bd=0,
            padx=20, pady=10,
            cursor="hand2",
            state="disabled",
            command=self._export_docx,
        )
        self.export_btn.pack(side="left")

        self.last_report: SummaryReport | None = None

        # ── Output log ────────────────────────────────────────────────────
        self._section_label(content, "📋  Output")

        self.output_box = scrolledtext.ScrolledText(
            content,
            font=FONT_MONO,
            bg=SURFACE, fg=TEXT,
            insertbackground=TEXT,
            relief="flat", bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            wrap="word",
            state="disabled",
            height=14,
        )
        self.output_box.pack(fill="both", expand=True, pady=(4, 0))

        # colour tags
        self.output_box.tag_config("accent",  foreground=ACCENT)
        self.output_box.tag_config("green",   foreground=GREEN)
        self.output_box.tag_config("red",     foreground=RED)
        self.output_box.tag_config("yellow",  foreground=YELLOW)
        self.output_box.tag_config("muted",   foreground=MUTED)
        self.output_box.tag_config("bold",    font=("Consolas", 9, "bold"))

    def _section_label(self, parent, text):
        tk.Label(
            parent, text=text,
            font=FONT_BOLD,
            bg=BG, fg=TEXT,
            anchor="w",
        ).pack(fill="x", pady=(0, 2))

    # ── ACTIONS ────────────────────────────────────────────────────────────

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Select folder to search")
        if folder:
            self.folder_var.set(folder)

    def _set_prompt(self, prompt: str):
        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", prompt)

    def _check_ollama(self):
        def check():
            ok = check_ollama_running()
            if ok:
                models = list_available_models()
                self.status_dot.config(
                    text=f"● Ollama connected  |  {', '.join(models[:3]) or 'no models found'}",
                    fg=GREEN
                )
            else:
                self.status_dot.config(text="● Ollama not running", fg=RED)
                self._log("⚠  Ollama is not running!\n", "red")
                self._log("   Open a terminal and run:  ollama serve\n", "yellow")
        threading.Thread(target=check, daemon=True).start()

    def _run(self):
        folder  = self.folder_var.get().strip()
        prompt  = self.prompt_text.get("1.0", "end").strip()
        recurse = self.recursive_var.get()

        # Validate
        if not folder:
            self._log("⚠  Please select a folder first.\n", "red")
            return
        if not prompt:
            self._log("⚠  Please enter a prompt.\n", "red")
            return
        if not Path(folder).exists():
            self._log(f"⚠  Folder not found: {folder}\n", "red")
            return

        self.run_btn.config(state="disabled", text="⏳  Running…")
        self._clear_output()
        self._log(f"📁  Folder : {folder}\n", "accent")
        self._log(f"💬  Prompt : {prompt}\n", "accent")
        self._log(f"🔁  Recursive : {'Yes' if recurse else 'No'}\n\n", "muted")

        def task():
            try:
                report = run_summary(
                    paths=[Path(folder)],
                    prompt=prompt,
                    recursive=recurse,
                    save_json=True,
                    log_fn=self._log,       # pass logger to summarizer
                )
                self.last_report = report
                self._render_report(report)
                self.export_btn.config(state="normal", bg=ACCENT, fg="white")
            except Exception as e:
                self._log(f"\n❌  Error: {e}\n", "red")
            finally:
                self.run_btn.config(state="normal", text="⚡  Analyze & Summarize")

        threading.Thread(target=task, daemon=True).start()

    def _export_docx(self):
        if not self.last_report:
            return
        from pathlib import Path
        out_dir = Path("output")
        out_dir.mkdir(exist_ok=True)
        out_path = out_dir / "summary_report.docx"

        try:
            export_to_docx(self.last_report, out_path)
            self._log(f"\n📄  Word document saved → {out_path.resolve()}\n", "green")
        except Exception as e:
            self._log(f"\n❌  Failed to export Word doc: {e}\n", "red")

    # ── OUTPUT RENDERING ───────────────────────────────────────────────────

    def _render_report(self, report: SummaryReport):
        self._log("\n" + "─" * 60 + "\n", "muted")
        self._log("  RESULTS\n", "bold")
        self._log("─" * 60 + "\n\n", "muted")

        # Stats
        self._log(f"  Total files  : {report.total_files}\n")
        self._log(f"  Processed    : {report.processed}\n", "green")
        if report.failed:
            self._log(f"  Failed       : {report.failed}\n", "red")
        self._log(f"  Model        : {report.model_used}\n\n", "muted")

        # Global summary
        if report.global_summary.global_summary:
            self._log("🌐  GLOBAL SUMMARY\n", "accent")
            self._log(report.global_summary.global_summary + "\n\n")

        # Common themes
        if report.global_summary.common_themes:
            self._log("🔗  COMMON THEMES\n", "yellow")
            for t in report.global_summary.common_themes:
                self._log(f"   ◆ {t}\n")
            self._log("\n")

        # Top insights
        if report.global_summary.top_insights:
            self._log("💡  TOP INSIGHTS\n", "green")
            for i in report.global_summary.top_insights:
                self._log(f"   ▶ {i}\n")
            self._log("\n")

        # Per file
        self._log("─" * 60 + "\n", "muted")
        self._log("  PER FILE BREAKDOWN\n", "bold")
        self._log("─" * 60 + "\n\n", "muted")

        for fs in report.files:
            self._log(f"  📄 {fs.filename}  ", "accent")
            self._log(f"[{fs.file_type}  {fs.file_size_kb} KB]\n", "muted")
            if not fs.success:
                self._log(f"     ❌ {fs.error}\n\n", "red")
                continue
            if fs.data_summary:
                self._log(f"     {fs.data_summary}\n")
            for p in fs.key_points:
                self._log(f"     • {p}\n", "muted")
            if fs.entities:
                self._log(f"     Entities: {fs.entities}\n", "yellow")
            self._log("\n")

        self._log("─" * 60 + "\n", "muted")
        self._log("✅  Done! Report saved to output/summary_report.json\n", "green")

    # ── HELPERS ────────────────────────────────────────────────────────────

    def _log(self, message: str, tag: str = ""):
        def _write():
            self.output_box.config(state="normal")
            if tag:
                self.output_box.insert("end", message, tag)
            else:
                self.output_box.insert("end", message)
            self.output_box.see("end")
            self.output_box.config(state="disabled")
        self.after(0, _write)

    def _clear_output(self):
        self.output_box.config(state="normal")
        self.output_box.delete("1.0", "end")
        self.output_box.config(state="disabled")


# ── Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = FileMindApp()
    app.mainloop()