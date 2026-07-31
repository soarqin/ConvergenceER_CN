# 统一翻译工具实施计划

本文档记录统一翻译工具的实施范围、格式约定、阶段目标和验收标准。工具是通用的魂游翻译工具，本仓库作为首个宿主项目提供《艾尔登法环》 Convergence 简体中文翻译配置。

## 1. 目标

统一当前分散在 `Yabber+.exe`、`fmgcarry.exe`、`update_fmg.bat`、`extract_updates.bat`、`repack_dcx.bat` 和 `merge_updates.py` 中的操作，提供一套基于 Python 和 `uv` 的通用魂游翻译命令行工具。Python 项目位于 `tools/souls-translation-tool`，与本仓库的翻译数据分开维护。

工具需要覆盖以下能力：

1. 解包和打包 `dcx` 文件。
2. 读写 `FMG` 文件和 `msgbnd`/BND4 容器。
3. 保留现有翻译文本格式和六种行首符号：`<`、`>`、`-`、`=`、`O`、`C`。
4. 支持三方对比，生成全新的待翻译文本。
5. 支持五方对比，更新已有翻译文本并保留旧版本参考。
6. 保持当前导入规则：只有 `=` 行是语言 B 的正式译文，空的 `=` 行在构建时回退到 MOD 语言 A。
7. 正确区分 FMG 的 null 槽位、存在但为空的字符串，以及包含 `[ERROR]` 的实际文本。

## 2. 技术方案

### 2.1 语言和项目管理

- 使用 Python。
- 使用 `uv` 管理项目、依赖和测试环境。
- 初始支持 Windows，目标运行环境为 Python 3.11 或更高版本。
- 使用固定版本的 `Soulstruct` 作为二进制格式后端，避免直接跟随其要求 Python 3.13 的开发分支。
- GPL 依赖已获接受。

### 2.2 格式后端

使用 `Soulstruct` 处理以下格式：

- `DCX`：自动识别压缩类型，支持当前文件使用的 `DCX_KRAK`，并保留扩展到 `DCX_ZSTD` 等类型的接口。
- `BND4`：读取和写入 `msgbnd` 容器，保留条目 ID、内部路径、标志位和文件顺序所需的信息。
- `FMG`：读取和写入 Elden Ring FMG V2、UTF-16 文本、ID 范围和空字符串。

工具自身实现翻译文本层，不把六符号格式交给外部工具处理。

## 3. 目录和配置

根翻译项目使用 `souls-translation.toml` 配置当前项目的目录和语言；通用工具本身不内置 Convergence 路径：

```toml
[project]
language_a = "engUS"
language_b = "zhoCN"

[paths]
game_a = "origin/engUS"
game_b = "origin/zhoCN"
mod_a = "mod/engUS"
mod_b = "mod/zhoCN"
translation = "."
output = "stage"
```

实现时保留以下现有路径和文件名：

- `item`、`menu`
- `item_dlc02`、`menu_dlc02`
- `item_dlc02.msgbnd.dcx`、`menu_dlc02.msgbnd.dcx`
- `GR\\data\\INTERROOT_win64\\msg\\engUS\\`
- `GR\\data\\INTERROOT_win64\\msg\\zhoCN\\`

语言目录应来自配置，不在代码中固定为英文和简体中文。

## 4. 翻译文本格式

### 4.1 行首符号

翻译源文件使用 `ID:"文本"` 形式的条目，每条参考文本前有一个行首符号：

| 符号 | 含义 |
| --- | --- |
| `<` | 游戏原始文本 A |
| `>` | 当前版本 MOD 文本 A |
| `-` | 游戏原始文本 B |
| `=` | 当前版本 MOD 文本 B，即正式翻译行 |
| `O` | 上一个版本 MOD 文本 A |
| `C` | 上一个版本 MOD 文本 B |

常见条目顺序包括：

```text
< > - =
< O > - C =
< O > C =
> =
```

解析器必须按 ID 建立条目，不能按行号或行首符号的字典序匹配。

### 4.2 文本、转义和空值

- 使用 UTF-8 读取和写入翻译文本。
- 保留 `\\n` 等文本转义，不把翻译文本中的换行误当作新条目。
- `= ID:""` 是合法的空翻译，不能当作缺失行。
- FMG 中 offset 为 `0` 的槽位是 null 槽位，不等同于存在但为空的字符串。
- FMG 中存在且文本长度为 `0` 的条目必须写成实际空字符串，不能写成 null 槽位。
- `[ERROR]` 可能是当前项目用来表示游戏错误文本的实际字符串，不能一律转换为 null。
- 需要在内部模型中使用至少三种状态：缺失、null、存在的字符串；其中存在的字符串可以是空字符串或 `[ERROR]`。

## 5. 命令设计

建议统一命令名称如下：

```text
souls-translation-tool dcx unpack
souls-translation-tool dcx pack

souls-translation-tool fmg unpack
souls-translation-tool fmg pack

souls-translation-tool translation generate
souls-translation-tool translation update
souls-translation-tool translation merge
souls-translation-tool translation build

souls-translation-tool project extract-update
souls-translation-tool project build
```

这些子命令由同一个 CLI 提供；`project extract-update` 通过宿主项目配置完成归档提取和文本对比。

## 6. 三方对比

输入：

```text
游戏原始文本 A
游戏原始文本 B
MOD 文本 A
```

按相同 FMG 文件和 ID 对比：

```text
< ID:"游戏原始文本 A"
> ID:"MOD 文本 A"
- ID:"游戏原始文本 B"
= ID:""
```

规则：

- `MOD A == 游戏原始 A` 的条目不输出。
- MOD 新增 ID 输出。
- `=` 默认输出空字符串，表示待翻译。
- `-` 只作为语言 B 参考，不参与 MOD A 是否变化的判断。
- 缺少的参考文本不伪造空行。
- MOD 删除的 ID 单独写入 `removed.json`，不使用空的 `=` 表示删除。
- 当前 MOD A 中值为 null 的 ID 写入 `null.json`，不把它当作删除 ID。

## 7. 五方对比

输入：

```text
游戏原始文本 A
游戏原始文本 B
上一个版本 MOD 文本 A
上一个版本 MOD 文本 B
本版本 MOD 文本 A
```

变化条目输出为：

```text
< ID:"游戏原始文本 A"
O ID:"上一个版本 MOD 文本 A"
> ID:"本版本 MOD 文本 A"
- ID:"游戏原始文本 B"
C ID:"上一个版本 MOD 文本 B"
= ID:""
```

规则：

- 以 `上一个版本 MOD A` 和 `本版本 MOD A` 的差异判断是否需要更新翻译。
- `<` 和 `-` 使用当前游戏原始文本 A/B。
- `O` 保存旧 MOD A，`>` 保存新 MOD A。
- `C` 保存旧 MOD B。
- 新的 `=` 默认留空，要求重新确认译文。
- 已有输入中的 `O`、`C` 必须原样保留，不能根据当前 `>`、`=` 重新推导覆盖。
- MOD 删除的 ID 写入 `removed.json`，不默认自动删除翻译源条目。
- 当前 MOD A 中值为 null 的 ID 写入 `null.json`，与缺失 ID 区分处理。

## 8. 导入和构建规则

导入翻译文本时只读取 `=` 行：

```text
目标 FMG B = 游戏原始 FMG B

对于 MOD A 相对游戏 A 有变化的 ID：
    如果 = 非空，使用 =
    否则，使用 >

最后应用所有非空的 = 行，包括 MOD A 中不存在或已恢复为游戏原文的 ID。
```

具体规则：

- `<`、`>`、`-`、`O`、`C` 都是参考文本，不直接写入最终 FMG。
- 非空的 `=` 写入语言 B。
- 空的 `=` 回退到当前 `>` 文本，保持现有工具行为。
- 非空的 `=` 不依赖 MOD A 是否变化，始终写入语言 B。
- 未变化的普通游戏条目保留游戏原始语言 B。
- MOD A 中缺失的 ID 不从语言 B 删除，保留游戏原始语言 B 或非空 `=` 提供的译文。
- null 槽位与空字符串保持不同；比较游戏 A 和 MOD A 时，为兼容旧版 `fmgcarry`，空字符串、纯空白字符串和 `[ERROR]` 视为同类空文本。
- 普通文本在构建时去除尾部空白；若文本全部由空白组成，则原样保留。
- 生成 FMG 后必须重新读取生成文件，验证 ID、状态和文本一致。

## 9. 实施阶段

### 阶段 1：项目骨架和格式规格

- 在 `tools/souls-translation-tool` 中创建 `pyproject.toml`、`uv.lock`、`src/` 和 `tests/`。
- 固化六符号文本格式和条目状态模型。
- 建立现有项目样例的 golden fixture。

验收：解析和写回现有样例后，六种行首符号、条目 ID、转义文本和空字符串语义不丢失。

### 阶段 2：FMG、BND4 和 DCX 后端

- 接入固定版本 `Soulstruct`。
- 支持当前 `DCX_KRAK` 文件的解包、重打包和再次读取。
- 支持 BND4 内部 FMG 的查找、替换和写回。
- 正确处理 Oodle DLL 路径；优先使用项目现有工具目录或配置指定路径。

验收：`item_dlc02.msgbnd.dcx` 和 `menu_dlc02.msgbnd.dcx` 可解包、重新打包并再次解包，内部 FMG 条目数量和文本一致。

### 阶段 3：三方和五方对比

- 实现三方对比和全新待翻译文本生成。
- 实现五方对比和已有翻译文本更新。
- 生成文件级、条目级统计、`removed.json` 和 `null.json`。

验收：使用 `origin`、`mod` 和 `update` 的实际样例，结果与预期的 `<`、`>`、`-`、`=`、`O`、`C` 语义一致。

### 阶段 4：导入、合并和构建

- 实现 `=` 行导入。
- 实现空 `=` 回退到 `>`。
- 实现翻译源到 FMG、FMG 到 BND4、BND4 到 DCX 的完整构建。
- 将现有批处理文件改为统一 CLI 的兼容包装器。

验收：生成的语言 B FMG 可以放回 `msgbnd.dcx`，游戏能够读取，且 null 槽位和空字符串保持预期状态。

### 阶段 5：文档和迁移

- 更新 `README.md` 的格式说明和使用流程。
- 将 `merge_updates.py` 改为兼容入口或明确迁移方式。
- 保留 `Yabber+.exe` 和 `fmgcarry.exe` 作为一个版本周期的回退工具。

## 10. 测试计划

至少覆盖以下测试：

- 六种行首符号的解析、写回和合法顺序。
- 多行文本、引号和反斜杠转义。
- null 槽位。
- 存在但为空的 FMG 字符串。
- `[ERROR]` 实际文本。
- 与旧版 `fmgcarry` 一致的空字符串、纯空白字符串和 `[ERROR]` 比较语义。
- 普通文本去除尾部空白，纯空白文本保持原样。
- 空的 `=` 行回退到 `>`。
- 已有 `O`、`C` 不被覆盖。
- `-` 行不会在合并时丢失。
- 三方对比新增、修改、未变化和删除条目。
- 五方对比新增、修改、未变化和删除条目。
- FMG 二进制读写往返。
- DCX KRAK 解包和打包往返。
- BND4 条目替换后路径、ID 和文件数量保持一致。
- `git diff --check`。

建议验证命令：

```powershell
uv run --project tools/souls-translation-tool pytest
uv run --project tools/souls-translation-tool souls-translation-tool --help
uv run --project tools/souls-translation-tool souls-translation-tool --config souls-translation.toml dcx unpack stage\\item_dlc02.msgbnd.dcx <temporary-directory>
uv run --project tools/souls-translation-tool souls-translation-tool --config souls-translation.toml dcx pack <temporary-directory> <temporary-directory>\\item_dlc02.msgbnd.dcx
git diff --check
```

## 11. 已知边界

- 首版目标是当前项目使用的 Elden Ring BND4、FMG V2 和 DCX KRAK；其他 DCX 类型通过统一接口逐步增加。
- MOD 删除条目只生成报告，不自动删除已有翻译。
- 自动翻译不属于工具范围，工具只生成待翻译文本并导入人工译文。
- `update/` 和 `stage/` 不在任务明确要求时自动清理或覆盖。
- 最终发布前需要确认 Oodle DLL 的来源和分发方式；工具不应重新分发游戏 DLL。
- `project extract-update` 已迁移到统一 CLI；它从 `update` 中的 DCX 归档提取语言 A 的 FMG，并生成 `update/item`、`update/menu` 文本。
- `update_fmg.bat`、`extract_updates.bat`、`repack_dcx.bat` 已改为统一 CLI 的兼容包装器；`merge_updates.py` 保留原有两参数入口并转发到 `translation merge`。
- 当前配置只覆盖 `item_dlc02` 和 `menu_dlc02`；README 中的旧版四归档说明已按当前配置修正。
- Oodle DLL 仍由项目环境提供，工具只从宿主项目的 `souls-translation.toml` 加载，不负责重新分发；发布包的授权和来源确认仍属于发布前人工事项。
