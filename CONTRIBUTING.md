# Contributing

PowerplanPVD supports Python 3.11 and newer. Create a virtual environment and install the project
with its development dependencies:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
```

Before opening a pull request, run the same checks used by continuous integration:

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest --cov=sputterplan --cov-report=term-missing --cov-fail-under=80
.\.venv\Scripts\python.exe -m pip wheel . --no-deps --wheel-dir dist
```

Changes to calculation behavior should include focused unit tests and corresponding updates to the
calculation model or configuration reference. Do not commit experimental or unapproved laboratory
workbooks; the repository ignore rules intentionally exclude them.
