@echo off

pushd stage

"..\tools\Yabber+.exe" .\item.msgbnd.dcx
copy /y ..\mod\zhoCN\item\*.fmg .\item-msgbnd-dcx\GR\data\INTERROOT_win64\msg\zhoCN\
"..\tools\Yabber+.exe" .\item-msgbnd-dcx

"..\tools\Yabber+.exe" .\menu.msgbnd.dcx
copy /y ..\mod\zhoCN\menu\*.fmg .\menu-msgbnd-dcx\GR\data\INTERROOT_win64\msg\zhoCN\
"..\tools\Yabber+.exe" .\menu-msgbnd-dcx

popd
