# utils/quick — 快速启动

一键同时启动 **Core 引擎 + Control API**（并打开界面）。脚本会：

- 复用已在运行的引擎（不会重复启动）
- API 端口被占用时自动挑选空闲端口
- 就绪后自动打开浏览器
- Ctrl+C 时优雅停止 API，以及由它启动的引擎

| 平台 | 命令 |
|---|---|
| Linux | `bash utils/quick/linux-run.sh` |
| macOS | `./utils/quick/mac-run.command` |
| Windows | 手动两进程：`python -m engine run` + `python -m server run` |

> Windows 的批处理在端口探测和进程回收（优雅停止）上不可靠、也难以自动化验证，
> 因此不提供 `.bat`。Windows 请用两条命令分别启动，或用 NSSM 注册为服务
> （见 `help/INSTALL.md` 的 API 部署一节）。

需要分别运行（不用快速启动）时：

```bash
python -m engine run        # 引擎
python -m server run        # API（--host/--port；端口占用默认自动顺延并警告）
```
