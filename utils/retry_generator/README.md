# Retry Generator - 失败章节重试生成器

## 📋 功能简介

自动分析 TTS 生成日志，识别失败章节，生成重试命令。支持三种输出模式：

1. **Shell 脚本模式** - 生成可执行的 bash 脚本
2. **纯文本模式** - 生成命令列表文本
3. **直接执行模式** - 立即执行重试（需确认）

## 🚀 快速开始

### 基本用法

```bash
# 生成 Shell 脚本（推荐）
python utils/retry_generator/cli.py logs/app.log sh output/retry.sh

# 生成纯文本
python utils/retry_generator/cli.py logs/app.log txt output/retry.txt

# 直接执行重试（危险，需确认）
python utils/retry_generator/cli.py logs/app.log exec
```

### 高级用法

```bash
# 自定义批次大小（每批次10章）
python utils/retry_generator/cli.py logs/app.log sh output/retry.sh --batch-size 10

# 指定输入文件
python utils/retry_generator/cli.py logs/app.log sh output/retry.sh --input books/novel.pdf

# 仅包含网络错误
python utils/retry_generator/cli.py logs/app.log sh output/retry.sh --filter network
```

## 📖 参数说明

### 必需参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `log_file` | 日志文件路径 | `logs/app.log` |
| `output_type` | 输出类型 | `sh` / `txt` / `exec` |
| `output_path` | 输出文件路径 | `output/retry.sh` |

> **注意**: `exec` 模式下 `output_path` 可省略

### 可选参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--batch-size` | 每批次章节数 | `20` |
| `--input` | 输入文件路径 | `debug/ga.pdf` |
| `--filter` | 错误类型过滤 | `all` |

#### 错误类型过滤

- `all` - 所有错误（默认）
- `network` - 仅网络连接错误
- `timeout` - 仅超时错误

## 📝 输出示例

### Shell 脚本模式 (`sh`)

生成的脚本包含：
- 自动错误检测
- 批次执行确认
- 失败后询问是否继续

```bash
#!/bin/bash
# 自动生成的重试脚本
# 生成时间: 2025-11-11 16:00:00
# 失败章节总数: 133
# 批次总数: 7

echo '开始重试失败章节...'

# 批次1：第67-86章（20章）
echo '执行批次 1/7...'
bash cli.sh -i debug/ga.pdf --start 67 --end 86
if [ $? -ne 0 ]; then
    echo '❌ 批次1失败，是否继续？(y/n)'
    read -r response
    if [ "$response" != "y" ]; then exit 1; fi
fi
```

### 纯文本模式 (`txt`)

生成简洁的命令列表：

```
失败章节重试命令列表
生成时间: 2025-11-11 16:00:00
失败章节总数: 133
批次总数: 7

============================================================

批次1：第67-86章（20章）
bash cli.sh -i debug/ga.pdf --start 67 --end 86

批次2：第87-106章（20章）
bash cli.sh -i debug/ga.pdf --start 87 --end 106
```

### 直接执行模式 (`exec`)

交互式执行流程：

```
============================================================
⚠️  直接执行模式
============================================================

📊 即将执行:
   - 批次总数: 7
   - 输入文件: debug/ga.pdf

📋 批次列表:
   1. 第67-86章（20章）
   2. 第87-106章（20章）
   ...

⚠️  警告: 将直接执行重试，无法撤销！
是否继续？(yes/no): 
```

## 🔧 工作原理

### 1. 日志分析

扫描日志文件，识别包含以下错误的行：
- `Cannot connect to host` - 网络连接失败
- `getaddrinfo failed` - DNS 解析失败
- `timeout` / `timed out` - 超时错误
- `TTS 生成失败` - TTS 引擎错误

### 2. 章节提取

从错误行向前查找章节信息：
- 匹配模式: `[67/458]` 提取章节序号
- 去重并排序

### 3. 批次分组

智能分组策略：
- 连续章节合并为一个批次
- 每批次最多 N 章（可配置）
- 间隔小于 3 章的也会合并

### 4. 命令生成

根据输出类型生成：
- Shell 脚本：包含错误处理和交互确认
- 纯文本：简洁的命令列表
- 直接执行：实时执行并显示进度

## 📂 文件结构

```
utils/retry_generator/
├── cli.py              # 命令行入口
├── analyzer.py         # 日志分析器
├── generator.py        # 命令生成器
├── executor.py         # 直接执行器
└── README.md           # 使用文档
```

## 🎯 使用场景

### 场景1：网络不稳定导致批量失败

```bash
# 1. 分析日志，生成重试脚本
python utils/retry_generator/cli.py logs/app.log sh retry.sh

# 2. 检查脚本内容
cat retry.sh

# 3. 执行重试
bash retry.sh
```

### 场景2：快速查看失败章节

```bash
# 生成文本列表
python utils/retry_generator/cli.py logs/app.log txt failed_list.txt

# 查看
cat failed_list.txt
```

### 场景3：立即重试（适合少量失败）

```bash
# 直接执行模式
python utils/retry_generator/cli.py logs/app.log exec
```

## ⚠️ 注意事项

1. **exec 模式风险**
   - 会立即执行重试，无法撤销
   - 建议先用 `sh` 或 `txt` 模式查看
   - 执行前会要求确认

2. **批次大小建议**
   - 网络稳定：20-30 章/批次
   - 网络不稳定：5-10 章/批次
   - 大量失败：建议分多次执行

3. **日志文件要求**
   - 必须包含章节序号信息 `[N/Total]`
   - 必须包含错误信息
   - 建议使用最新的日志文件

## 🐛 故障排除

### 问题1：未识别到失败章节

**原因**: 日志格式不匹配

**解决**:
```bash
# 检查日志是否包含错误信息
grep "失败" logs/app.log

# 检查日志是否包含章节序号
grep "\[.*/.*/\]" logs/app.log
```

### 问题2：生成的批次过多

**原因**: 默认批次大小太小

**解决**:
```bash
# 增加批次大小
python utils/retry_generator/cli.py logs/app.log sh retry.sh --batch-size 50
```

### 问题3：exec 模式执行失败

**原因**: 工作目录不正确

**解决**:
```bash
# 确保在项目根目录执行
cd /path/to/ga-sprite-birds
python utils/retry_generator/cli.py logs/app.log exec
```

## 📚 相关文档

- [项目主文档](../../README.md)
- [CLI 使用说明](../../fcgi-bin/cli.py)
- [配置文件说明](../../.env)

