@echo off
pushd "%~dp0"
copy /y origin\zhoCN\item_dlc02\*.* mod\zhoCN\item_dlc02\ >nul
if errorlevel 1 goto :error
copy /y origin\zhoCN\menu_dlc02\*.* mod\zhoCN\menu_dlc02\ >nul
if errorlevel 1 goto :error
uv run --project tools\souls-translation-tool souls-translation-tool --config souls-translation.toml translation build --game-a origin\engUS\item_dlc02 --game-b origin\zhoCN\item_dlc02 --mod-a mod\engUS\item_dlc02 --translation item --output mod\zhoCN\item_dlc02
if errorlevel 1 goto :error
uv run --project tools\souls-translation-tool souls-translation-tool --config souls-translation.toml translation build --game-a origin\engUS\menu_dlc02 --game-b origin\zhoCN\menu_dlc02 --mod-a mod\engUS\menu_dlc02 --translation menu --output mod\zhoCN\menu_dlc02
if errorlevel 1 goto :error
popd
exit /b 0

:error
popd
exit /b 1
