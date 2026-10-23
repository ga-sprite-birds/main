# 角色分析工具

使用 LLM 从小说章节中自动提取角色信息，支持**智能分析**和**混合模式**两种方式。

---

## 📖 功能背景

在小说转语音的过程中，为了实现**多角色配音**，需要：

1. **识别角色**：从小说中提取所有出现的角色
2. **分析别名**：识别同一角色的不同称呼（如"张三"、"小张"、"张公子"）
3. **性格分析**：提取角色性格特征，用于后续情绪化配音
4. **音色分配**：为每个角色分配合适的 TTS 音色

本工具提供两种分析模式，满足不同场景的需求。

---

## 🎯 两种分析模式

### 智能分析模式（Auto Mode）

**工作原理**：
- LLM 逐章分析小说内容
- 自动发现所有出现的角色
- 自动识别别名并尝试合并重复角色
- 自动提取性格标签
- **✨ 分析完成后，自动使用 LLM 检测并合并重复角色**

**特点**：
- ✅ **优点**：全自动，无需人工干预，快速方便，自动合并重复角色
- ❌ **缺点**：LLM 合并可能不完美，建议人工检查
- 🎯 **适用场景**：快速测试、探索性分析、快速原型

---

### 混合模式（Hybrid Mode）

**工作原理**：
- 用户提供角色列表文件（指定角色名和性别）
- LLM 为每个指定角色分析别名和性格
- 避免重复角色问题

**特点**：
- ✅ **优点**：精确控制，避免重复角色，别名更准确
- ❌ **缺点**：需要手动创建角色列表文件
- 🎯 **适用场景**：正式生产、需要精确控制的场景

---

## ⚙️ 核心功能

- ✅ 自动拆分章节
- ✅ 使用 LLM 分析每章的角色
- ✅ 识别角色别名（如"张三"、"小张"、"张公子"）
- ✅ 识别角色性别（male/female/unknown/narrator）
- ✅ 提取角色性格标签（如"热血"、"冷静"、"善良"）
- ✅ 统计角色出现次数和章节范围
- ✅ **自动合并重复角色（智能分析模式）**
- ✅ 自动分配 TTS 音色
- ✅ 支持两种分析模式（智能分析/混合模式）

---

## 🚀 使用方法

### 方式 1：智能分析模式

**适用场景**：快速测试、探索性分析

```bash
# 分析整本小说
bash cli.sh -i input.txt --analyze-characters

# 分析指定章节范围
bash cli.sh -i input.txt --analyze-characters --start 1 --end 10
```

**输出示例**：
```
============================================================
角色分析模式：智能分析
============================================================

正在初始化 LLM 管理器...
✓ LLM 管理器初始化成功

开始分析角色...
分析章节 1: 第一章
  → 识别到 5 个角色: 角色A, 角色B, 角色C, 角色E, 旁白
分析章节 2: 第二章
  → 识别到 3 个角色: 角色A, 角色B, 角色D

✓ 共识别 15 个角色

正在检查并合并重复角色...
开始分析重复角色...
发现 2 组重复角色，开始合并...
  合并: A → 角色A
    原因: 都是指同一个人，角色A是完整名字
  合并: 父亲 → 角色B
    原因: 都是指角色A的父亲
✓ 合并完成：15 个角色 → 13 个角色

为角色分配音色...
✓ 角色配音模板已保存: cache/role/example_book_characters.json
```

---

### 方式 2：混合模式

**适用场景**：正式生产、需要精确控制的场景

#### 步骤 1：创建角色列表文件

创建一个文本文件（如 `characters.txt`），每行一个角色名：

```txt
# 角色列表示例
# 格式：角色名 [性别]
# 性别可选值：male, female, unknown, narrator

# 主要角色
角色A male
角色B male
角色C male

# 配角
角色E male

# 特殊角色
旁白 narrator
其他 unknown
```

**格式说明**：
- ✅ 每行一个角色名
- ✅ 可选：在角色名后添加性别（`male`, `female`, `unknown`, `narrator`）
- ✅ 支持 `#` 开头的注释行
- ✅ 支持空行

**示例文件**：参考 `debug/characters_example.txt`

---

#### 步骤 2：运行混合模式分析

```bash
bash cli.sh -i input.txt \
  --analyze-characters \
  --character-list characters.txt \
  --start 1 \
  --end 10
```

**输出示例**：
```
============================================================
角色分析模式：混合模式
============================================================

✓ 从角色列表文件读取 7 个角色: 角色A, 角色B, 角色C, 角色E, 旁白, 其他

开始分析角色...
分析章节 1: 第一章
  → 角色A: 别名 ['A', '小A']
  → 角色B: 别名 ['父亲', 'B']
  → 角色C: 别名 ['C']
分析章节 2: 第二章
  → 角色A: 别名 ['小A']
  → 角色E: 别名 ['E']

✓ 共识别 7 个角色

为角色分配音色...
✓ 角色配音模板已保存: cache/role/example_book_characters.json
```

---

#### 步骤 3：检查生成的模板

```bash
cat cache/role/example_book_characters.json
```

---

#### 步骤 4：生成多角色配音

```bash
bash cli.sh -i input.txt --multi-voice
```

---

## 📊 两种模式对比

| 特性 | 智能分析模式 | 混合模式 |
|------|------------|---------|
| **角色发现** | LLM 自动发现所有角色 | 用户指定角色列表 |
| **别名分析** | LLM 自动识别并合并 | LLM 为指定角色找别名 |
| **性格分析** | LLM 自动提取 | LLM 为指定角色提取 |
| **重复角色处理** | ✅ 自动检测并合并 | ✅ 用户指定，无重复 |
| **优点** | ✅ 全自动，自动合并重复 | ✅ 精确控制，完全避免重复 |
| **缺点** | ❌ LLM 合并可能不完美 | ❌ 需要手动创建角色列表 |
| **适用场景** | 快速测试、探索性分析 | 正式生产、精确控制 |

---

### 💡 建议工作流程

1. **第一步**：用**智能分析模式**快速生成模板
   ```bash
   bash cli.sh -i input.txt --analyze-characters --start 1 --end 5
   ```

2. **第二步**：检查模板，发现重复角色或问题
   ```bash
   cat cache/role/example_book_characters.json
   ```

3. **第三步**：创建角色列表文件，去除重复
   ```bash
   # 创建 characters.txt，只保留正确的角色名
   ```

4. **第四步**：用**混合模式**重新分析，生成精确模板
   ```bash
   bash cli.sh -i input.txt --analyze-characters --character-list characters.txt
   ```

5. **第五步**：生成多角色配音
   ```bash
   bash cli.sh -i input.txt --multi-voice
   ```

---

## 📄 输出格式

生成的角色配音模板文件（`cache/role/[文件名]_characters.json`）：

```json
{
  "novel_id": "example_book",
  "novel_title": "示例书名",
  "total_characters": 5,
  "characters": [
    {
      "name": "角色A",
      "aliases": ["A", "小A", "小A"],
      "gender": "male",
      "voice": "zh-CN-YunxiNeural",
      "description": "",
      "personality": ["善良", "勇敢", "热血"],
      "appearance_count": 45,
      "first_chapter": 1,
      "last_chapter": 20
    },
    {
      "name": "角色B",
      "aliases": ["父亲", "B"],
      "gender": "male",
      "voice": "zh-CN-YunjianNeural",
      "description": "角色A的父亲",
      "personality": ["严厉", "关心", "传统"],
      "appearance_count": 32,
      "first_chapter": 1,
      "last_chapter": 18
    }
  ],
  "narrator": {
    "name": "旁白",
    "voice": "zh-CN-XiaoxiaoNeural",
    "personality": ["客观", "平静"]
  }
}
```

---

## 📝 字段说明

#### `personality`（性格标签）

结构化标签数组，从预定义标签库中选择：

```json
"personality": ["善良", "勇敢", "热血"]
```

**用途**：
- 描述角色的性格特征
- 将来做情绪配音时，可以根据标签调整 TTS 参数（如语速、音调、情绪强度）

**预定义标签库**（`config/__init__.py`）：

```python
PERSONALITY_TAGS = {
    "性格": ["热血", "冷静", "冲动", "理智", "善良", ...],
    "说话": ["直接", "委婉", "大声", "轻声", ...],
    "情绪": ["激动", "平静", "易怒", "温和", ...],
    "角色": ["长辈", "晚辈", "领导", "下属", ...],
    "其他": ["传统", "现代", "固执", "灵活", ...]
}
```

**示例**：
```python
# 对话：角色A说："我一定要救他！"
# 角色性格：["热血", "勇敢", "善良"]
# → TTS 参数调整：语速 +10%，音调 +5%，情绪强度 +20%
```

---

## ⚙️ 配置

工具使用项目的配置（`.env` 文件）：

### LLM 配置

```bash
# LLM 模式（local/api）
LLM_MODE=api

# API 配置
LLM_API_KEY=your_api_key
LLM_API_MODEL=deepseek-chat
LLM_API_BASE_URL=https://api.deepseek.com
```

### 角色分析配置

```bash
# 是否启用多角色配音（true/false）
ENABLE_MULTI_VOICE=false

# 角色分析模式（auto/hybrid）
CHARACTER_ANALYSIS_MODE=auto

# 角色数据缓存目录
CHARACTER_CACHE_DIR=./cache/role

# 发送给 LLM 的最大内容长度
CHARACTER_MAX_CONTENT_LENGTH=3000
```

**⚠️ 注意**：
- ✅ 命令行参数 `--character-list` 会自动启用混合模式，无需修改配置文件
- ✅ 命令行参数 `--multi-voice` 会覆盖配置文件的 `ENABLE_MULTI_VOICE`

### 章节解析配置

```bash
# 章节识别正则表达式
CHAPTER_REGEX_PATTERNS=["^第[0-9一二三四五六七八九十百千]+[章回节].*$"]

# 最小章节长度
CHAPTER_MIN_LENGTH=100

# 是否保留章节标题
CHAPTER_KEEP_TITLE=true
```

---

## ❓ 常见问题

### Q1：混合模式和智能分析模式哪个更好？

**答**：根据使用场景选择：

| 场景 | 推荐模式 | 原因 |
|------|---------|------|
| 快速测试 | 智能分析模式 | 全自动，无需人工干预 |
| 探索性分析 | 智能分析模式 | 快速了解小说中的角色 |
| 正式生产 | 混合模式 | 精确控制，避免重复角色 |
| 需要精确控制 | 混合模式 | 用户指定角色列表 |

**💡 建议工作流程**：
1. 先用**智能分析模式**快速生成模板
2. 检查模板，发现重复角色
3. 创建角色列表文件，去除重复
4. 用**混合模式**重新分析，生成精确模板

---

### Q2：如何知道应该指定哪些角色？

**答**：按以下步骤操作：

1. **第一步**：用智能分析模式分析一遍
   ```bash
   bash cli.sh -i input.txt --analyze-characters --start 1 --end 5
   ```

2. **第二步**：查看生成的模板，找出主要角色
   ```bash
   cat cache/role/example_book_characters.json
   ```

3. **第三步**：手动去重，创建角色列表文件
   ```bash
   # 创建 characters.txt
   角色A male
   角色B male
   角色C male
   ```

4. **第四步**：用混合模式重新分析
   ```bash
   bash cli.sh -i input.txt --analyze-characters --character-list characters.txt
   ```

---

### Q3：智能分析模式的自动合并功能如何工作？

**答**：

智能分析模式在完成所有章节分析后，会自动执行以下步骤：

1. **检测重复角色**：
   - LLM 分析所有识别到的角色
   - 识别可能是同一个人的角色（如"A"和"角色A"）

2. **自动合并**：
   - 选择最完整的名字作为主名称
   - 合并别名、性格标签、出现次数等信息
   - 删除重复的角色

3. **输出结果**：
   - 显示合并的详细信息
   - 保存合并后的模板

**示例**：
```
正在检查并合并重复角色...
开始分析重复角色...
发现 2 组重复角色，开始合并...
  合并: A → 角色A
    原因: 都是指同一个人，角色A是完整名字
  合并: 父亲 → 角色B
    原因: 都是指角色A的父亲
✓ 合并完成：15 个角色 → 13 个角色
```

**注意**：
- ✅ 自动合并功能会大大减少重复角色
- ⚠️ LLM 合并可能不完美，建议人工检查生成的模板
- 💡 如需完全精确控制，建议使用混合模式

---

---

### Q4：混合模式会检测遗漏的角色吗？

**答**：

目前版本暂不支持。未来版本会添加此功能：

**计划功能**：
- ✅ LLM 分析时会检测是否有重要角色被遗漏
- ✅ 将遗漏的角色保存到建议文件（如 `cache/role/[文件名]_suggested_characters.txt`）
- ✅ 用户可以手动添加到角色列表

**当前解决方案**：
- 先用智能分析模式分析一遍
- 查看生成的模板，找出所有角色
- 手动创建角色列表文件

---

### Q5：`personality` 字段有什么用？

**答**：

`personality` 字段用于描述角色的性格特征，将来可以用于**情绪化配音**。

**示例**：
```python
# 对话：角色A说："我一定要救他！"
# 角色性格：["热血", "勇敢", "善良"]

# TTS 参数调整：
# - 语速：+10%（热血角色说话更快）
# - 音调：+5%（情绪激动）
# - 情绪强度：+20%（勇敢、坚定）
```

**当前状态**：
- ✅ 已实现：提取性格标签
- ⏳ 未实现：根据性格调整 TTS 参数（未来版本）

---

## 📚 完整示例

### 示例 1：智能分析模式（快速测试）

```bash
# 步骤 1：分析角色
bash cli.sh -i input.txt --analyze-characters --start 1 --end 5

# 步骤 2：检查生成的模板
cat cache/role/example_book_characters.json

# 步骤 3：生成多角色配音
bash cli.sh -i input.txt --multi-voice --start 1 --end 5
```

**✅ 优点**：
- 全自动，无需人工干预
- 快速生成模板
- 自动检测并合并重复角色

**⚠️ 注意**：
- LLM 自动合并可能不完美，建议检查生成的模板

---

### 示例 2：混合模式（正式生产）

```bash
# 步骤 1：创建角色列表
cat > characters.txt << EOF
# 主要角色
角色A male
角色B male
角色C male
角色E male

# 特殊角色
旁白 narrator
其他 unknown
EOF

# 步骤 2：运行混合模式分析
bash cli.sh -i input.txt \
  --analyze-characters \
  --character-list characters.txt

# 步骤 3：检查生成的模板
cat cache/role/example_book_characters.json

# 步骤 4：生成多角色配音
bash cli.sh -i input.txt --multi-voice
```

**✅ 优点**：
- 无重复角色
- 别名更准确
- 性格标签更精确

**❌ 缺点**：
- 需要手动创建角色列表文件

---

## 🎯 总结

角色分析工具提供了两种模式，满足不同场景的需求：

| 模式 | 特点 | 适用场景 |
|------|------|---------|
| **智能分析模式** | 快速、自动 | 探索和测试 |
| **混合模式** | 精确、可控 | 正式生产 |

---

### 💡 推荐工作流程

```
1. 智能分析 → 快速生成模板
   ↓
2. 检查模板 → 发现重复角色
   ↓
3. 创建角色列表 → 去除重复
   ↓
4. 混合模式 → 生成精确模板
   ↓
5. 生成音频 → 多角色配音
```

---

### 🚀 快速开始

```bash
# 1. 智能分析模式（快速测试）
bash cli.sh -i input.txt --analyze-characters --start 1 --end 5

# 2. 混合模式（正式生产）
bash cli.sh -i input.txt --analyze-characters --character-list characters.txt

# 3. 生成多角色配音
bash cli.sh -i input.txt --multi-voice
```

---

祝您使用愉快！🎉

