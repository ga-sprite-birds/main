# Contributing to GA Sprite Birds

感谢你对 `GA Sprite Birds` 的关注。本文档说明如何提交问题、贡献代码，以及贡献被合并时适用的授权规则。

## 项目信息

- 作者：`adam`
- 邮箱：`dev@ebf.hk`
- 官网：<http://ebf.cc>
- GitHub 源码：<https://github.com/tiger-sprite/ga-sprite-birds>

## 1. 贡献方式

欢迎以下类型的贡献：

- Bug 反馈与复现步骤
- 文档修正与示例补充
- 单元测试与集成测试改进
- CLI / API / 核心模块功能修复
- 新平台接入、自部署体验优化、开发者体验优化

如果你准备做较大的变更，建议先创建 issue 说明目标、范围和设计思路，避免和项目路线冲突。

## 2. 开始之前

建议先阅读以下文档：

- `help/README.md`
- `help/INSTALL.md`
- `help/development-guide.md`
- `tests/README.md`

本项目当前以 Python 为主，包含：

- CLI 入口：`fcgi-bin/cli.py`
- API 入口：`fcgi-bin/api.py`
- 核心模块：`ga_birds/`
- 测试：`tests/`

## 3. 开发环境

推荐使用 Python `3.10+`。

基础安装流程：

```bash
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

如果你使用 Conda 或其他环境管理方式，也可以按 `help/INSTALL.md` 中的说明配置。

## 4. 开发原则

提交修改时，请尽量遵循以下原则：

- 保持改动聚焦，不把多个无关问题混在同一个 PR 中
- 优先修复根因，而不是只做表面补丁
- 尽量复用现有模块职责边界，不随意打破目录分层
- 新功能或修复如果存在回归风险，优先补测试
- 不要提交密钥、令牌、账号、真实敏感文本或其他秘密信息
- 避免无必要的大规模格式化，减少 review 噪音

## 5. 代码风格

请尽量与现有代码风格保持一致：

- Python 文件使用小写加下划线命名
- 类名使用大驼峰
- 函数名使用小写加下划线
- API 参数保持下划线风格
- CLI 长参数保持连字符风格
- 导入顺序、模块边界、命名规范可参考 `help/development-guide.md`

如果你引入了不直观的业务逻辑，请补充简洁注释，解释“为什么这样做”。

## 6. 测试要求

提交前，建议至少完成与你改动直接相关的测试。

常用命令：

```bash
# 单元测试
pytest tests/unit -v

# 运行特定测试文件
pytest tests/unit/test_upload.py -v

# 集成测试（需要先启动 API）
pytest tests/integration -v
```

如果你的改动影响以下内容，请特别注意验证：

- 上传、解析、生成等 API 流程
- CLI 参数兼容性
- 多语言文案
- 文件路径、输出目录、缓存行为
- LLM / TTS 相关配置回退逻辑

## 7. Pull Request 建议

PR 描述建议尽量包含：

- 变更背景
- 变更内容
- 为什么这样改
- 测试方式
- 是否有兼容性影响

推荐使用小而清晰的 PR，这会明显降低 review 成本。

## 8. Issue 反馈建议

提交 issue 时，建议尽量提供：

- 运行环境（OS、Python 版本）
- 启动方式（CLI / API）
- 输入类型（txt / pdf）
- 错误日志或堆栈
- 最小可复现步骤
- 期望结果与实际结果

如果问题和第三方服务有关，也请说明：

- 使用的是本地 LLM 还是 API 模式
- 使用的是哪种 TTS 引擎
- 是否配置了代理或特殊网络环境

## 9. 贡献授权规则

本项目采用 `Apache License 2.0` 开源。

除非你明确声明相反并事先与维护者达成书面约定，否则你有意提交到本项目、希望被纳入代码库的任何贡献，都将默认按 `Apache-2.0` 授权并分发。

提交贡献即表示你确认：

- 你有权提交该贡献
- 该贡献不会侵犯你所知的第三方权利
- 你同意该贡献作为本项目的一部分，以 `Apache-2.0` 许可证发布

如果你代表公司或组织提交代码，请先确认你有相应授权。

## 10. 关于未来授权调整

项目维护者可能会在未来为新版本调整发布策略、仓库结构、商业化方式或附属项目的授权安排。

但除非另有明确书面协议，已按 `Apache-2.0` 合法发布的代码版本，其既有授权不会被追溯撤销。

如果项目未来引入单独的贡献者许可协议（CLA）或开发者证书流程（DCO），会在仓库文档中明确说明。

## 11. 行为预期

请保持专业、尊重和建设性的沟通方式。对问题、设计分歧和代码 review 的讨论，优先聚焦事实、复现、影响和改进方案。

---

**作者**：`adam`  
**邮箱**：`dev@ebf.hk`  
**官网**：<http://ebf.cc>  
**GitHub 源码**：<https://github.com/tiger-sprite/ga-sprite-birds>  
**更新时间**：2026-07-09

---

感谢你的贡献。
