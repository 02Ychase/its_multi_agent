$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\backend\knowledge"
python -m pip install -r requirements.txt
ruff check .
pytest tests -m "not integration" -v
