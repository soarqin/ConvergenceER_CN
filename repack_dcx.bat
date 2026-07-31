@echo off
pushd "%~dp0"
uv run --project tools\souls-translation-tool souls-translation-tool --config souls-translation.toml project build --output stage
set "exit_code=%errorlevel%"
popd
exit /b %exit_code%
