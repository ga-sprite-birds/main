# 角色分析工具

使用 LLM 从小说章节中自动提取角色信息。

## 功能

- 自动拆分章节
- 使用 LLM 分析每章的角色
- 识别角色别名
- 识别角色性别
- 统计角色出现次数和章节范围

## 使用方法

```bash
# 分析整本小说
python ga_birds/character_analyzer/cli.py debug/ga.pdf

# 分析指定章节范围
python ga_birds/character_analyzer/cli.py debug/择天记.txt --start 1 --end 10

# 指定输出路径
python ga_birds/character_analyzer/cli.py debug/ga.pdf --output my_characters.json
```

## 输出格式

```json
{
  "novel_id": "ga",
  "novel_title": "ga",
  "total_characters": 3,
  "characters": [
    {
      "name": "陈长生",
      "aliases": ["长生", "陈某"],
      "gender": "male",
      "appearance_count": 15,
      "first_chapter": 1,
      "last_chapter": 10
    }
  ]
}
```

## 配置

工具使用项目的配置（`.env` 文件）：

### LLM 配置
- `LLM_MODE`: local 或 api
- `LLM_API_KEY`: API 密钥（如果使用 API 模式）
- `LLM_API_MODEL`: 模型名称（如 deepseek-chat）

### 角色分析配置
- `ENABLE_MULTI_VOICE`: 是否启用多角色配音（默认: false）
- `CHARACTER_CACHE_DIR`: 角色数据缓存目录（默认: ./cache/role）
- `CHARACTER_MAX_CONTENT_LENGTH`: 发送给 LLM 的最大内容长度（默认: 3000）

### 章节解析配置
- `CHAPTER_REGEX_PATTERNS`: 章节识别正则表达式
- `CHAPTER_MIN_LENGTH`: 最小章节长度
- `CHAPTER_KEEP_TITLE`: 是否保留章节标题

