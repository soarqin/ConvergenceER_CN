# Convergence for Elden Ring 简体中文翻译

## 翻译说明
* 进行文本翻译只需要修改item和menu目录下的txt文件
* txt文件中的开头的字母表示：
  * `<` 法环游戏原始英文语言文本，参考用
  * `>` MOD中的英文语言文本，参考用
  * `-` 法环游戏原始中文语言文本，参考用
  * `=` MOD翻译后的中文语言文本，翻译的时候只需要改这一行，留空表示未翻译，工具处理时会采用英文版的文本

## 重新打包
* 运行`update_fmg.bat`重新生成fmg文件
* 运行`repack_dcx.bat`打包`item.msgbnd.dcx`和`menu.msgbnd.dcx`，生成于`stage`目录下

## 放到MOD中测试
* 把两个文件复制到Convergence的`mod\msg\zhoCN`(如果没有这个目录则需要自己创建，大小写不敏感)下即可

## 贡献者
* [KrukaL](https://github.com/KrukaL)
  + 1.2的大量翻译修正以及1.3绝大多数词条的翻译，没有他大家不可能快玩到这个完整的翻译版本
  + 1.4.2之后提供了大量翻译问题的修正

## 鸣谢
* [Convergence MOD for Elden Ring](https://www.nexusmods.com/eldenring/mods/3419): 原MOD
* [Yabber+](https://github.com/sekirodubi/YabberPlus): 解包和打包msgbnd.dcx文件
* [fmgcarry](https://github.com/soarqin/fmgcarry): 自制fmg处理和合并工具
