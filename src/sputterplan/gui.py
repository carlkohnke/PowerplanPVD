"""Small desktop launcher for users who prefer not to use a terminal."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .configuration import load_config
from .errors import SputterPlanError
from .outputs import write_outputs
from .pipeline import create_plan


class PlannerWindow(ttk.Frame):
    def __init__(self, parent: tk.Tk) -> None:
        super().__init__(parent, padding=16)
        self.parent = parent
        self.config_path = tk.StringVar()
        self.output_path = tk.StringVar(value=str(Path.cwd() / "results"))
        self.status = tk.StringVar(value="Choose a YAML or JSON configuration.")
        self.grid(sticky="nsew")
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        ttk.Label(self, text="Configuration").grid(row=0, column=0, sticky="w", pady=6)
        ttk.Entry(self, textvariable=self.config_path).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(self, text="Browse", command=self._choose_config).grid(row=0, column=2)

        ttk.Label(self, text="Output folder").grid(row=1, column=0, sticky="w", pady=6)
        ttk.Entry(self, textvariable=self.output_path).grid(row=1, column=1, sticky="ew", padx=8)
        ttk.Button(self, text="Browse", command=self._choose_output).grid(row=1, column=2)

        ttk.Button(self, text="Create plan", command=self._run).grid(
            row=2, column=1, sticky="w", pady=(12, 8)
        )
        ttk.Label(self, textvariable=self.status, wraplength=650).grid(
            row=3, column=0, columnspan=3, sticky="w"
        )

    def _choose_config(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("Configuration", "*.yaml *.yml *.json"), ("All files", "*.*")]
        )
        if path:
            self.config_path.set(path)

    def _choose_output(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self.output_path.set(path)

    def _run(self) -> None:
        try:
            config = load_config(self.config_path.get())
            result = create_plan(config)
            paths = write_outputs(result, config, self.output_path.get())
            summary = result.summary()
            self.status.set(
                f"Created {summary['breakpoint_count']} change points over "
                f"{summary['total_time_min']:.1f} min. Wrote {len(paths)} files."
            )
            messagebox.showinfo("SputterPlan", self.status.get())
        except (SputterPlanError, OSError, ValueError) as exc:
            self.status.set(str(exc))
            messagebox.showerror("SputterPlan", str(exc))


def main() -> None:
    root = tk.Tk()
    root.title("SputterPlan")
    root.geometry("760x190")
    PlannerWindow(root)
    root.mainloop()


if __name__ == "__main__":
    main()
