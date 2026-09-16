"""Desktop launcher for validating configurations and creating plans."""

from __future__ import annotations

import os
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from .configuration import load_config
from .errors import SputterPlanError
from .outputs import write_outputs
from .pipeline import create_plan
from .presentation import format_summary_text


def suggested_output_path(config_path: str) -> str:
    if not config_path.strip():
        return str(Path.cwd() / "results")
    path = Path(config_path).expanduser().resolve()
    return str(path.parent / "results" / path.stem)


def open_local_path(path: Path) -> None:
    """Open a report or folder using the operating system's normal application."""
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        webbrowser.open(path.resolve().as_uri())


class PlannerWindow(ttk.Frame):
    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent, padding=22)
        self.parent = parent
        self.config_path = tk.StringVar()
        self.output_path = tk.StringVar(value=suggested_output_path(""))
        self.include_plots = tk.BooleanVar(value=True)
        self.overwrite = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Choose a configuration to begin.")
        self.last_report: Path | None = None
        self.last_output: Path | None = None
        self._build()

    def _build(self) -> None:
        self.grid(sticky="nsew")
        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(8, weight=1)

        ttk.Label(self, text="SputterPlan", style="Title.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w"
        )
        ttk.Label(
            self,
            text="Validate a composition profile and create an operator-ready sputtering plan.",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 18))

        ttk.Label(self, text="Configuration file").grid(row=2, column=0, sticky="w", pady=7)
        config_entry = ttk.Entry(self, textvariable=self.config_path)
        config_entry.grid(row=2, column=1, sticky="ew", padx=10)
        ttk.Button(self, text="Browse…", command=self._choose_config).grid(row=2, column=2)

        ttk.Label(self, text="Output folder").grid(row=3, column=0, sticky="w", pady=7)
        ttk.Entry(self, textvariable=self.output_path).grid(row=3, column=1, sticky="ew", padx=10)
        ttk.Button(self, text="Browse…", command=self._choose_output).grid(row=3, column=2)

        options = ttk.Frame(self)
        options.grid(row=4, column=1, sticky="w", pady=(4, 12))
        ttk.Checkbutton(options, text="Create plots", variable=self.include_plots).grid(
            row=0, column=0, padx=(0, 20)
        )
        ttk.Checkbutton(
            options, text="Overwrite existing SputterPlan files", variable=self.overwrite
        ).grid(row=0, column=1)

        actions = ttk.Frame(self)
        actions.grid(row=5, column=0, columnspan=3, sticky="w")
        self.validate_button = ttk.Button(
            actions, text="Validate", command=lambda: self._start("validate")
        )
        self.validate_button.grid(row=0, column=0, padx=(0, 8))
        self.create_button = ttk.Button(
            actions, text="Create plan", style="Accent.TButton", command=lambda: self._start("plan")
        )
        self.create_button.grid(row=0, column=1, padx=(0, 8))
        self.report_button = ttk.Button(
            actions, text="Open report", command=self._open_report, state="disabled"
        )
        self.report_button.grid(row=0, column=2, padx=(0, 8))
        self.folder_button = ttk.Button(
            actions, text="Open output folder", command=self._open_folder, state="disabled"
        )
        self.folder_button.grid(row=0, column=3)

        self.progress = ttk.Progressbar(self, mode="indeterminate")
        self.progress.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(15, 5))
        ttk.Label(self, textvariable=self.status).grid(
            row=7, column=0, columnspan=3, sticky="nw", pady=(0, 8)
        )

        summary_frame = ttk.LabelFrame(self, text="Run summary", padding=10)
        summary_frame.grid(row=8, column=0, columnspan=3, sticky="nsew")
        summary_frame.columnconfigure(0, weight=1)
        summary_frame.rowconfigure(0, weight=1)
        self.summary_text = scrolledtext.ScrolledText(
            summary_frame, height=18, wrap="word", font=("Consolas", 10), state="disabled"
        )
        self.summary_text.grid(sticky="nsew")
        self.summary_text.configure(tabs=(24,))

        config_entry.focus_set()
        self.parent.bind("<Control-o>", lambda _event: self._choose_config())
        self.parent.bind("<Control-Return>", lambda _event: self._start("plan"))

    def _choose_config(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose SputterPlan configuration",
            filetypes=[("YAML or JSON", "*.yaml *.yml *.json"), ("All files", "*.*")],
        )
        if path:
            self.config_path.set(path)
            self.output_path.set(suggested_output_path(path))
            self.status.set("Configuration selected. Validate it or create the plan.")

    def _choose_output(self) -> None:
        path = filedialog.askdirectory(title="Choose output folder")
        if path:
            self.output_path.set(path)

    def _set_busy(self, busy: bool) -> None:
        state = "disabled" if busy else "normal"
        self.validate_button.configure(state=state)
        self.create_button.configure(state=state)
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()

    def _set_summary(self, text: str) -> None:
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", "end")
        self.summary_text.insert("1.0", text)
        self.summary_text.configure(state="disabled")

    def _start(self, action: str) -> None:
        config = self.config_path.get().strip()
        output = self.output_path.get().strip()
        include_plots = self.include_plots.get()
        overwrite = self.overwrite.get()
        if not config:
            messagebox.showwarning("SputterPlan", "Choose a YAML or JSON configuration first.")
            return
        if action == "plan" and not output:
            messagebox.showwarning("SputterPlan", "Choose an output folder first.")
            return
        self._set_busy(True)
        self.status.set("Validating inputs…" if action == "validate" else "Creating plan…")
        thread = threading.Thread(
            target=self._worker,
            args=(action, config, output, include_plots, overwrite),
            daemon=True,
        )
        thread.start()

    def _worker(
        self,
        action: str,
        config_path: str,
        output_path: str,
        include_plots: bool,
        overwrite: bool,
    ) -> None:
        try:
            config = load_config(config_path)
            result = create_plan(config)
            paths: list[Path] = []
            if action == "plan":
                paths = write_outputs(
                    result,
                    config,
                    output_path,
                    include_plots=include_plots,
                    overwrite=overwrite,
                )
            self.parent.after(0, lambda: self._finish_success(action, result.summary(), paths))
        except (SputterPlanError, OSError, ValueError) as exc:
            self.parent.after(0, lambda message=str(exc): self._finish_error(message))
        except Exception as exc:  # noqa: BLE001 - keep the desktop app responsive on unexpected faults
            message = (
                f"Unexpected error: {exc}\n\nPlease save this message when reporting the problem."
            )
            self.parent.after(
                0,
                lambda message=message: self._finish_error(message),
            )

    def _finish_success(self, action: str, summary: dict, paths: list[Path]) -> None:
        self._set_busy(False)
        self._set_summary(format_summary_text(summary))
        if action == "validate":
            self.status.set("Validation complete. The configuration can produce a plan.")
            return
        self.last_output = Path(self.output_path.get()).resolve()
        self.last_report = self.last_output / "report.html"
        self.report_button.configure(state="normal")
        self.folder_button.configure(state="normal")
        self.status.set(f"Plan complete. Wrote {len(paths)} files to {self.last_output}")

    def _finish_error(self, message: str) -> None:
        self._set_busy(False)
        self.status.set("Could not complete the request. Review the message below.")
        self._set_summary(message)
        messagebox.showerror("SputterPlan", message)

    def _open_report(self) -> None:
        if self.last_report and self.last_report.exists():
            open_local_path(self.last_report)

    def _open_folder(self) -> None:
        if self.last_output and self.last_output.exists():
            open_local_path(self.last_output)


def main() -> None:
    root = tk.Tk()
    root.title("SputterPlan")
    root.geometry("920x700")
    root.minsize(760, 560)
    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")
    style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"))
    style.configure("Subtitle.TLabel", font=("Segoe UI", 10), foreground="#4d5656")
    style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
    PlannerWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
