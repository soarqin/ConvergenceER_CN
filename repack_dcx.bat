@echo off

pushd stage

"..\tools\Yabber+.exe" .\item.msgbnd.dcx
copy /y ..\mod\zhoCN\item_dlc02\*.fmg .\item-msgbnd-dcx\GR\data\INTERROOT_win64\msg\zhoCN\
del /q /f .\item-msgbnd-dcx\GR\data\INTERROOT_win64\msg\zhoCN\*_dlc*.fmg
"..\tools\Yabber+.exe" .\item-msgbnd-dcx

"..\tools\Yabber+.exe" .\menu.msgbnd.dcx
copy /y ..\mod\zhoCN\menu_dlc02\*.fmg .\menu-msgbnd-dcx\GR\data\INTERROOT_win64\msg\zhoCN\
del /q /f .\menu-msgbnd-dcx\GR\data\INTERROOT_win64\msg\zhoCN\*_dlc*.fmg
"..\tools\Yabber+.exe" .\menu-msgbnd-dcx

"..\tools\Yabber+.exe" .\item_dlc02.msgbnd.dcx
copy /y ..\mod\zhoCN\item_dlc02\*.fmg .\item_dlc02-msgbnd-dcx\GR\data\INTERROOT_win64\msg\zhoCN\
"..\tools\Yabber+.exe" .\item_dlc02-msgbnd-dcx

"..\tools\Yabber+.exe" .\menu_dlc02.msgbnd.dcx
copy /y ..\mod\zhoCN\menu_dlc02\*.fmg .\menu_dlc02-msgbnd-dcx\GR\data\INTERROOT_win64\msg\zhoCN\
"..\tools\Yabber+.exe" .\menu_dlc02-msgbnd-dcx

popd
