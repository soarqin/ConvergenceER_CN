# Souls Translation Tool

用于魂系列游戏文本翻译流程的通用 Python 命令行工具，提供 FMG、BND4、DCX 和翻译文本处理能力。具体游戏或 MOD 的目录、语言和归档名称由宿主项目配置，不写入工具代码。

## 开发

```powershell
uv run pytest
uv run souls-translation-tool --help
```

## 宿主项目调用

在宿主项目根目录运行：

```powershell
uv run --project tools/souls-translation-tool souls-translation-tool --config souls-translation.toml project build
```

配置文件负责提供语言目录、翻译目录、输出目录、归档名称和 Oodle DLL 路径。Oodle DLL 不属于该 Python 项目的分发内容。
