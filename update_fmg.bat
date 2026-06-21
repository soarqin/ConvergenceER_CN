@echo off
copy /y origin\zhoCN\item_dlc02\*.* mod\zhoCN\item_dlc02\
copy /y origin\zhoCN\menu_dlc02\*.* mod\zhoCN\menu_dlc02\
tools\fmgcarry.exe origin\engUS\item_dlc02 mod\engUS\item_dlc02 mod\zhoCN\item_dlc02 item
tools\fmgcarry.exe origin\engUS\menu_dlc02 mod\engUS\menu_dlc02 mod\zhoCN\menu_dlc02 menu
