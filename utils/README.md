# Utils 工具开发者规范

## 📋 概述

`utils/` 目录是项目辅助工具集合，用于提供独立的功能模块，帮助开发者更高效地使用和维护项目。

## 🎯 核心定位

### **独立工具定位**
- utils 工具 = 独立的辅助功能模块
- 可以访问项目模块，但应保持松耦合
- 优先使用标准库和项目已有的公共模块
- 避免重复造轮子

### **模块化原则**
- 每个工具功能单一、职责明确
- 工具之间保持独立，避免相互依赖
- 提供清晰的命令行接口
- 输出格式规范、易于理解

## 🚫 开发禁忌

### **避免过度耦合**
```python
# ❌ 错误 - 直接修改核心配置
import config
config.LOG_LEVEL = "DEBUG"

# ✅ 正确 - 只读取配置
import config
log_level = config.LOG_LEVEL
```

### **避免硬编码路径**
```python
# ❌ 错误 - 硬编码绝对路径
log_file = "F:/web/ga-sprite-birds/logs/app.log"

# ✅ 正确 - 使用相对路径
from pathlib import Path
project_root = Path(__file__).parent.parent
log_file = project_root / "logs" / "app.log"
```

### **避免重复实现**
```python
# ❌ 错误 - 重复实现已有功能
def parse_log_line(line):
    # 自己实现复杂的日志解析
    pass

# ✅ 正确 - 使用标准库
import re
pattern = r'\[(\d+)/\d+\]'
match = re.search(pattern, line)
```

## ✅ 开发原则

### **1. 配置优先原则**
从项目配置模块读取配置，不硬编码：
```python
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import config

log_file = config.LOG_FILE
output_path = config.OUTPUT_BASE_PATH
```

### **2. 功能独立原则**
每个工具独立，不依赖其他 utils 工具：
```python
# ✅ 正确 - 独立的功能模块
utils/retry_generator/
├── cli.py              # 命令行入口
├── analyzer.py         # 日志分析
├── generator.py        # 命令生成
└── executor.py         # 命令执行

# ❌ 错误 - 依赖其他工具
from utils.other_tool import some_function
```

### **3. 代码精简原则**
代码直接、精简，无冗余注释：
```python
# ✅ 正确 - 代码即文档
def analyze(self, error_filter='all'):
    failed_chapters = set()
    with open(self.log_file, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if self._is_error_line(line, error_filter):
                chapter_num = self._find_chapter_number(lines, i)
                if chapter_num:
                    failed_chapters.add(chapter_num)
    return sorted(list(failed_chapters))

# ❌ 错误 - 过多注释
def analyze(self, error_filter='all'):
    # 创建一个集合用于存储失败的章节
    failed_chapters = set()
    # 打开日志文件进行读取
    with open(self.log_file, 'r', encoding='utf-8') as f:
        # 遍历每一行
        for i, line in enumerate(f):
            # 检查是否是错误行
            if self._is_error_line(line, error_filter):
                # 查找章节号
                chapter_num = self._find_chapter_number(lines, i)
                # 如果找到了章节号
                if chapter_num:
                    # 添加到集合中
                    failed_chapters.add(chapter_num)
    # 返回排序后的列表
    return sorted(list(failed_chapters))
```

### **4. 错误处理原则**
清晰的错误提示，不隐藏异常：
```python
# ✅ 正确 - 明确的错误处理
if not os.path.exists(log_file):
    print(f"❌ 错误: 日志文件不存在: {log_file}")
    sys.exit(1)

# ❌ 错误 - 隐藏异常
try:
    with open(log_file) as f:
        pass
except:
    pass
```

## 📁 标准目录结构

```
utils/your_tool/
├── __init__.py          # 包初始化
├── cli.py               # 命令行入口
├── analyzer.py          # 核心功能模块1
├── generator.py         # 核心功能模块2
└── README.md            # 工具说明文档
```

## 📝 开发示例

### **示例：日志分析工具**

#### `utils/log_analyzer/cli.py`
```python
#!/usr/bin/env python3
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import config
from utils.log_analyzer.analyzer import LogAnalyzer

def main():
    if len(sys.argv) < 2:
        print("用法: python utils/log_analyzer/cli.py <日志文件>")
        sys.exit(1)

    log_file = sys.argv[1]

    if not Path(log_file).exists():
        print(f"❌ 错误: 日志文件不存在: {log_file}")
        sys.exit(1)

    analyzer = LogAnalyzer(log_file)
    failed_chapters = analyzer.analyze()

    print(f"📊 分析完成:")
    print(f"   - 失败章节总数: {len(failed_chapters)}")

if __name__ == "__main__":
    main()
```

#### `utils/log_analyzer/analyzer.py`
```python
import re
from typing import List, Set

class LogAnalyzer:
    def __init__(self, log_file: str):
        self.log_file = log_file
        self.error_pattern = r'ERROR.*TTS 生成失败'
        self.chapter_pattern = r'\[(\d+)/\d+\]'

    def analyze(self) -> List[int]:
        failed_chapters: Set[int] = set()

        with open(self.log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            if re.search(self.error_pattern, line):
                chapter_num = self._find_chapter_number(lines, i)
                if chapter_num:
                    failed_chapters.add(chapter_num)

        return sorted(list(failed_chapters))

    def _find_chapter_number(self, lines: List[str], error_index: int) -> int:
        start = max(0, error_index - 10)
        for i in range(error_index, start - 1, -1):
            match = re.search(self.chapter_pattern, lines[i])
            if match:
                return int(match.group(1))
        return None
```

## 📚 最佳实践

1. **从 config 模块读取配置**
2. **使用 pathlib 处理路径**
3. **保持代码精简直接**
4. **清晰的错误提示**
5. **工具之间保持独立**

## 🚀 开发流程

1. **创建工具目录**: `utils/your_tool/`
2. **编写核心模块**: 实现主要功能
3. **编写 CLI 入口**: 提供命令行接口
4. **测试功能**: 确保正常工作
5. **编写文档**: README.md（可选）
