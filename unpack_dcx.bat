@echo off

setlocal enableextensions

pushd update

"..\tools\Yabber+.exe" .\item_dlc02.msgbnd.dcx
mkdir .\engUS\item_dlc02
copy /y .\item_dlc02-msgbnd-dcx\GR\data\INTERROOT_win64\msg\engUS\*.fmg .\engUS\item_dlc02\

"..\tools\Yabber+.exe" .\menu_dlc02.msgbnd.dcx
mkdir .\engUS\menu_dlc02
copy /y .\menu_dlc02-msgbnd-dcx\GR\data\INTERROOT_win64\msg\engUS\*.fmg .\engUS\menu_dlc02\

rd /s /q item_dlc02-msgbnd-dcx menu_dlc02-msgbnd-dcx

popd

endlocal
