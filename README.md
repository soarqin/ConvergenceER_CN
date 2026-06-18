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
* 运行`repack_dcx.bat`打包`item.msgbnd.dcx`、`menu.msgbnd.dcx`、`item_dlc02.msgbnd.dcx`和`menu_dlc02.msgbnd.dcx`，生成于`stage`目录下

## 放到MOD中测试
* 把几个文件复制到Convergence的`Convergence\msg\zhoCN`(如果没有这个目录则需要自己创建，大小写不敏感)下即可

## 游戏更新后的改动文本提取
* 创建一个 `update` 目录
* 把英文版的 `item_dlc02.msgbnd.dcx` 和 `menu_dlc02.msgbnd.dcx` 复制进去
* 运行 `extract_updates.bat`
* 就会在当前目录生成所有改动过的 txt 条目，我暂时没有做合回去的功能，需要手动把他们的内容翻译完后合并回 `item` 和 `menu` 里的对应文本文件
* 以后可能会制作一个工具完成自动合并的功能

## 贡献者
* 2.2.3A版本及以前
  * [KrukaL](https://github.com/KrukaL)
    * 1.2的大量翻译修正以及1.3绝大多数词条的翻译，没有他大家不可能快玩到这个完整的翻译版本
    * 1.4.2之后提供了大量翻译问题的修正
    * 2.0.1之后的部分文本修正和大量翻译用词统一工作
    * 2.1.0的全部翻译工作
    * 2.2.3的部分修正
* 3.0 的讨论、翻译、校对、修正工作
  * [KrukaL](https://github.com/KrukaL)
  * Cinderella小辛
  * [名侦探的锋刃灰原哀](https://github.com/terrsia)

## 鸣谢
* [Convergence MOD for Elden Ring](https://www.nexusmods.com/eldenring/mods/3419): 原MOD
* [Yabber+](https://github.com/sekirodubi/YabberPlus): 解包和打包msgbnd.dcx文件
* [fmgcarry](https://github.com/soarqin/fmgcarry): 自制fmg处理和合并工具
