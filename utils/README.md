# Utils工具开发者规范

## 📋 概述

`utils/` 目录是项目辅助工具集合，用于提供独立的功能模块，帮助开发者更高效地使用和维护项目。

## 🛠️ 可用工具

### [retry_generator](retry_generator/) - 失败章节重试生成器

自动分析 TTS 生成日志，识别失败章节，生成重试命令。

**快速使用**:
```bash
# 生成重试脚本
python utils/retry_generator/cli.py logs/app.log sh output/retry.sh

# 执行重试
bash output/retry.sh
```

**功能特性**:
- ✅ 自动识别失败章节
- ✅ 智能批次分组
- ✅ 三种输出模式（Shell脚本/纯文本/直接执行）
- ✅ 错误类型过滤
- ✅ 可配置批次大小

**详细文档**: [retry_generator/README.md](retry_generator/README.md)

---

## 🎯 核心定位

### **独立工具定位**
- utils工具 = 独立的辅助功能模块
- 可以访问项目模块，但应保持松耦合
- 优先使用标准库和项目已有的公共模块
- 避免重复造轮子

### **模块化原则**
- 每个工具应该功能单一、职责明确
- 工具之间保持独立，避免相互依赖
- 提供清晰的命令行接口
- 输出格式规范、易于理解

## 🚫 开发禁忌

### **避免过度耦合**
```python
# ❌ 错误示例 - 直接修改核心配置
from config import Config
Config.LOG_LEVEL = "DEBUG"

# ✅ 正确示例 - 读取配置，不修改
from config import config
log_level = config.LOG_LEVEL
```

### **避免硬编码路径**
```python
# ❌ 错误示例 - 硬编码路径
log_file = "F:/web/ga-sprite-birds/logs/app.log"

# ✅ 正确示例 - 使用相对路径
import os
project_root = os.path.dirname(os.path.dirname(__file__))
log_file = os.path.join(project_root, "logs", "app.log")
```

### **避免重复实现**
```python
# ❌ 错误示例 - 重复实现日志解析
def parse_log_line(line):
    # 自己实现复杂的日志解析逻辑
    pass

# ✅ 正确示例 - 使用正则或现有工具
import re
pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \| (\w+) \|'
match = re.match(pattern, line)
```

## ✅ 开发原则

### **1. API优先原则**
所有功能必须通过官方API接口实现：
```python
# 标准API导入模式
from api import get_vector_search_api, get_index_query_api, get_keywords_api
```

### **2. 最小路径原则**
只添加必要的项目路径用于导入API：
```python
# 标准路径设置模式
import sys
import os

project_root = os.path.join(os.path.dirname(__file__), '..', '..', '..')
project_root = os.path.abspath(project_root)
sys.path.insert(0, project_root)

# 导入API（自动处理环境设置）
from api import get_index_query_api
```

### **3. 错误处理原则**
通过API返回的标准格式处理错误：
```python
result = api.search_keywords(keywords)
if result.get("success"):
    data = result["data"]
    # 处理成功结果
else:
    error = result.get("error", {})
    print(f"❌ 操作失败: {error.get('message', '未知错误')}")
```

### **4. 功能独立原则**
每个工具应该是独立的，不依赖其他utils工具：
- 独立的入口脚本
- 独立的功能实现
- 通过API获取所需资源

## 📁 标准目录结构

```
utils/app/your_tool/
├── main.py              # 入口脚本（设置路径，导入API）
├── cli.py               # 命令行接口（主要逻辑）
├── tool_core.py         # 核心功能（基于API）
└── README.md            # 工具说明文档
```

## 📝 开发示例

### **示例1：简单查询工具**

#### `utils/app/simple_query/main.py`
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单查询工具 - 入口脚本
"""

import sys
import os

# 添加项目根目录到路径（仅用于导入API）
project_root = os.path.join(os.path.dirname(__file__), '..', '..', '..')
project_root = os.path.abspath(project_root)
sys.path.insert(0, project_root)

# 导入API会自动处理环境设置
from api import get_index_query_api

from utils.app.simple_query.cli import main

if __name__ == "__main__":
    main()
```

#### `utils/app/simple_query/cli.py`
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单查询工具 - 命令行接口
"""

import sys
from api import get_index_query_api

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python main.py <查询内容>")
        return
    
    query = " ".join(sys.argv[1:])
    
    # 使用官方API
    api = get_index_query_api()
    
    # 执行查询
    result = api.analyze_query(query)
    
    if result.get("success"):
        data = result["data"]
        print(f"✅ 查询成功")
        print(f"📊 找到 {len(data.get('results', []))} 个结果")
        
        for i, item in enumerate(data.get('results', [])[:5], 1):
            print(f"{i}. {item.get('content', '')[:100]}...")
    else:
        error = result.get("error", {})
        print(f"❌ 查询失败: {error.get('message', '未知错误')}")

if __name__ == "__main__":
    main()
```

### **示例2：批量处理工具**

#### `utils/app/batch_processor/main.py`
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量处理工具 - 入口脚本
"""

import sys
import os

# 标准路径设置
project_root = os.path.join(os.path.dirname(__file__), '..', '..', '..')
project_root = os.path.abspath(project_root)
sys.path.insert(0, project_root)

# 导入API（自动环境设置）
from api import get_vector_search_api

from utils.app.batch_processor.cli import main

if __name__ == "__main__":
    main()
```

#### `utils/app/batch_processor/cli.py`
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量处理工具 - 命令行接口
"""

import sys
import json
from typing import List, Dict, Any
from api import get_vector_search_api

def process_queries(queries: List[str]) -> List[Dict[str, Any]]:
    """批量处理查询"""
    api = get_vector_search_api()
    results = []
    
    for i, query in enumerate(queries, 1):
        print(f"🔍 处理查询 {i}/{len(queries)}: {query}")
        
        result = api.search(query, top_k=5, threshold=0.3)
        
        if result.get("success"):
            results.append({
                "query": query,
                "success": True,
                "results": result["data"]["results"]
            })
        else:
            error = result.get("error", {})
            results.append({
                "query": query,
                "success": False,
                "error": error.get("message", "未知错误")
            })
    
    return results

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python main.py <查询1> [查询2] [查询3] ...")
        print("或者: python main.py --file queries.txt")
        return
    
    # 解析参数
    if sys.argv[1] == "--file":
        if len(sys.argv) < 3:
            print("❌ 请指定查询文件")
            return
        
        try:
            with open(sys.argv[2], 'r', encoding='utf-8') as f:
                queries = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"❌ 文件不存在: {sys.argv[2]}")
            return
    else:
        queries = sys.argv[1:]
    
    # 批量处理
    results = process_queries(queries)
    
    # 输出结果
    success_count = sum(1 for r in results if r["success"])
    print(f"\n📊 处理完成: {success_count}/{len(results)} 成功")
    
    # 保存结果
    output_file = "batch_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"💾 结果已保存到: {output_file}")

if __name__ == "__main__":
    main()
```

## 🔧 调试和测试

### **环境检查**
```python
# 检查API环境是否正确设置
from api.common.env_setup import get_environment_info

info = get_environment_info()
print("环境信息:", info)
```

### **API连接测试**
```python
# 测试API连接
from api import get_index_query_api

api = get_index_query_api()
result = api.get_index_info()
print("API状态:", "正常" if result.get("success") else "异常")
```

## 📚 最佳实践

1. **始终通过API访问功能**
2. **使用标准的错误处理模式**
3. **保持工具的独立性和简洁性**
4. **提供清晰的使用说明和示例**
5. **遵循统一的代码风格和命名规范**

## 🚀 开发流程

1. **创建工具目录**: `utils/app/your_tool/`
2. **编写入口脚本**: `main.py`（路径设置 + API导入）
3. **实现核心逻辑**: `cli.py`（基于API的功能实现）
4. **测试功能**: 确保通过API正常工作
5. **编写文档**: `README.md`（使用说明和示例）

遵循这些规范，可以确保开发的工具既符合第三方定位，又能充分利用RAG-R2项目的强大功能。
