$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\backend\app"
python -m pip install -r requirements.txt
ruff check .
pytest tests -m "not integration" -v
