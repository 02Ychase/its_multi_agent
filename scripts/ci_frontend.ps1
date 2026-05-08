$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\..\front\agent_web_ui"
npm ci
npm run build
Set-Location "$PSScriptRoot\..\front\knowlege_platform_ui"
npm ci
npm run build
