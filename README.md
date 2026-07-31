# Convergence for Elden Ring 简体中文翻译

## 翻译说明
* 进行文本翻译只需要修改item和menu目录下的txt文件
* txt文件中的开头的字母表示：
   * `<` 法环游戏原始英文语言文本，参考用
   * `O` 上一个版本 MOD 中的英文语言文本，参考用
   * `>` MOD中的英文语言文本，参考用
   * `-` 法环游戏原始中文语言文本，参考用
   * `C` 上一个版本 MOD 中的中文语言文本，参考用
   * `=` MOD翻译后的中文语言文本，翻译的时候只需要改这一行，留空表示未翻译，工具处理时会采用英文版的文本

## 统一工具

通用魂游翻译工具位于 `tools/souls-translation-tool`，作为独立 Python 子项目维护。实施计划和本项目的格式约定见 [`TOOL_PLAN.md`](TOOL_PLAN.md)。当前工具已提供 `FMG`、`DCX`、BND4、三方/五方翻译文本处理，以及项目级更新提取和构建。

使用 `uv` 运行命令：

```powershell
uv run --project tools/souls-translation-tool souls-translation-tool --help
uv run --project tools/souls-translation-tool souls-translation-tool fmg unpack <input.fmg> <output.fmg.txt>
uv run --project tools/souls-translation-tool souls-translation-tool fmg pack <input.fmg.txt> <output.fmg>
uv run --project tools/souls-translation-tool souls-translation-tool --config souls-translation.toml dcx unpack <input.msgbnd.dcx> <output-directory>
uv run --project tools/souls-translation-tool souls-translation-tool --config souls-translation.toml dcx pack <input-directory> <output.msgbnd.dcx>
uv run --project tools/souls-translation-tool souls-translation-tool translation generate --game-a <game-a-dir> --game-b <game-b-dir> --mod-a <mod-a-dir> --output <translation-dir>
uv run --project tools/souls-translation-tool souls-translation-tool translation update --game-a <game-a-dir> --game-b <game-b-dir> --previous-mod-a <previous-mod-a-dir> --previous-mod-b <previous-mod-b-dir> --current-mod-a <current-mod-a-dir> --existing <translation-dir> --output <translation-dir>
uv run --project tools/souls-translation-tool souls-translation-tool translation merge --original <translation-dir> --update <update-dir> --output <translation-dir>
uv run --project tools/souls-translation-tool souls-translation-tool --config souls-translation.toml project extract-update
uv run --project tools/souls-translation-tool souls-translation-tool --config souls-translation.toml project build --output <output-dir>
```

FMG 中的 null 槽位会在中间文本格式中保存为 `%null%`，与实际存在但为空的字符串区分。构建时沿用旧版 `fmgcarry` 的兼容规则：普通文本去除尾部空白，纯空白文本原样保留，比较时将空字符串、纯空白字符串和 `[ERROR]` 视为同类空文本。三方和五方对比会分别生成 `removed.json` 与 `null.json`。项目当前使用的 Oodle DLL 路径由根目录的 `souls-translation.toml` 配置，工具不会重新分发该 DLL。

## 重新打包
* 运行 `update_fmg.bat`，根据 `item` 和 `menu` 下的翻译文本更新 `mod/zhoCN` 中的 FMG 文件；也可以直接运行对应的 `translation build` 命令
* 运行 `repack_dcx.bat`，或运行 `uv run --project tools/souls-translation-tool souls-translation-tool --config souls-translation.toml project build --output stage`，生成当前配置中的 `item_dlc02.msgbnd.dcx` 和 `menu_dlc02.msgbnd.dcx`

## 放到 MOD 中测试
* 将构建得到的 `item_dlc02.msgbnd.dcx` 和 `menu_dlc02.msgbnd.dcx` 复制到 Convergence 的 `Convergence\msg\zhoCN` 目录；如果目录不存在则创建该目录
* 发布前需要在游戏内至少检查物品、菜单、对话和教程文本，并分别确认普通字符串、空字符串、null 槽位和 `[ERROR]` 文本的表现

## 游戏更新后的改动文本提取
* 创建一个 `update` 目录
* 把英文版的 `item_dlc02.msgbnd.dcx` 和 `menu_dlc02.msgbnd.dcx` 复制进去
* 运行 `extract_updates.bat`，或运行 `uv run --project tools/souls-translation-tool souls-translation-tool --config souls-translation.toml project extract-update`
* 工具会从 `update` 中配置的 DCX 归档提取语言 A 的 FMG，并在 `update/item` 和 `update/menu` 生成改动过的文本条目
* 可使用 `uv run --project tools/souls-translation-tool souls-translation-tool translation merge --original <translation-dir> --update <update-dir> --output <translation-dir>` 将更新文本合并到现有翻译目录
* MOD A 中缺失的 ID 写入 `removed.json`，MOD A 中的 null ID 写入 `null.json`，二者不会自动删除或覆盖翻译。

## 贡献者
* 2.2.3A版本及以前
  * [KrukaL](https://github.com/KrukaL)
    * 1.2的大量翻译修正以及1.3绝大多数词条的翻译，没有他大家不可能快玩到这个完整的翻译版本
    * 1.4.2之后提供了大量翻译问题的修正
    * 2.0.1之后的部分文本修正和大量翻译用词统一工作
    * 2.1.0的全部翻译工作
    * 2.2.3的部分修正
* 3.0 的讨论、翻译、校对、修正工作 (贡献排名不分先后)
  * [KrukaL](https://github.com/KrukaL)
  * Cinderella小辛
  * [名侦探的锋刃灰原哀](https://github.com/terrsia)
  * 破坏
  * [Lery](https://github.com/pgain2004)
  * 慕笔

## 鸣谢
* [Convergence MOD for Elden Ring](https://www.nexusmods.com/eldenring/mods/3419): 原MOD
* [Yabber+](https://github.com/sekirodubi/YabberPlus): 解包和打包msgbnd.dcx文件
* [fmgcarry](https://github.com/soarqin/fmgcarry): 自制fmg处理和合并工具
