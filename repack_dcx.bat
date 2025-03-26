@echo off

pushd stage

"..\tools\Yabber+.exe" .\item_dlc02.msgbnd.dcx
copy /y ..\mod\zhoCN\item_dlc02\*.fmg .\item_dlc02-msgbnd-dcx\GR\data\INTERROOT_win64\msg\zhoCN\
"..\tools\Yabber+.exe" .\item_dlc02-msgbnd-dcx

"..\tools\Yabber+.exe" .\menu_dlc02.msgbnd.dcx
copy /y ..\mod\zhoCN\menu_dlc02\*.fmg .\menu_dlc02-msgbnd-dcx\GR\data\INTERROOT_win64\msg\zhoCN\
"..\tools\Yabber+.exe" .\menu_dlc02-msgbnd-dcx

rd /s /q item_dlc02-msgbnd-dcx menu_dlc02-msgbnd-dcx

popd
