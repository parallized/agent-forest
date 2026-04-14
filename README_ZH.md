# Agent Forest 🌲 (代理森林)

[English](README.md) | [中文](README_ZH.md)

**Agent Forest** 是一个并行代理调查编排框架。它利用多个专业化 LLM 代理的力量，提供多维度研究、架构评审、风险发现和产品策略分析。

与单次生成的回答不同，Agent Forest 协调一个由 4 到 32 个代理组成的“森林”，从不同角度探索问题空间，并由中央“综合器”模型（您当前的对话模型）整合结果。

## 🚀 核心特性

- **并行调查**：同时运行多达 32 个代理，快速剖析复杂的研究任务。
- **多元视角**：利用角色库（证据猎人、风险审计师、系统思考者、反向思维者等）确保面面俱到。
- **灵活编排**：支持动态内联代理定义或持久、可重用的预设。
- **严格综合**：在代理报告（外部）和最终综合（本地）之间保持清晰界限，防止“幻觉共识”。
- **兼容 OpenAI**：支持任何遵循 OpenAI 聊天补全标准的 API 提供商。

## 🛠 项目结构

- `agents/`：代理行为和角色管理的逻辑。
- `scripts/`：用于运行和验证森林的命令行工具。
- `assets/`：配置示例和代理预设。
- `references/`：关于配置和载荷架构的详细文档。
- `tests/`：用于验证框架逻辑的测试套件。

## 🚦 开始使用

### 环境要求

- Python 3.8+
- OpenAI 兼容提供商的 API 密钥（如 OpenAI, Anthropic 代理, Grok 等）

### 安装为全局技能

1. 克隆仓库：
   ```bash
   git clone https://github.com/parallized/agent-forest.git
   cd agent-forest
   ```

2. 安装到 Codex、Claude Code，或同时安装：
   ```bash
   ./install.sh
   ```

   只安装单个平台也可以：
   ```bash
   ./install.sh --target codex
   ./install.sh --target claude
   ```

   Windows PowerShell:
   ```powershell
   .\install.ps1
   .\install.ps1 --target codex
   .\install.ps1 --target claude
   ```

3. 设置环境变量：
   ```bash
   export AGENT_FOREST_API_KEY="your-api-key-here"
   ```

4. 修改安装后的配置文件：
   - Codex：`~/.codex/skills/agent-forest/assets/agent-forest.config.json`
   - Claude Code：`~/.claude/skills/agent-forest/assets/agent-forest.config.json`

   如果目标位置已经存在，重新安装时加上 `--force`。

5. 调用方式：
   - Codex：让它自动发现这个 skill，或者直接引用 `$agent-forest`
   - Claude Code：直接用 `/agent-forest`，或让 Claude 在相关任务中自动加载

6. 也可以通过对话或命令直接配置提供商参数：
   ```bash
   python ~/.codex/skills/agent-forest/scripts/agent_forest.py configure \
     --config ~/.codex/skills/agent-forest/assets/agent-forest.config.json \
     --api-base https://ai.huan666.de/v1/chat/completions \
     --model grok-4.20-expert \
     --api-key your-api-key
   ```

## 📖 使用方法

### 验证配置
在运行森林之前，确保您的设置正确：
```bash
python ~/.codex/skills/agent-forest/scripts/agent_forest.py validate-config --config ~/.codex/skills/agent-forest/assets/agent-forest.config.json
```

### 运行研究任务（使用预设）
使用 `research-squad-4` 预设进行均衡的调查：
```bash
python ~/.codex/skills/agent-forest/scripts/agent_forest.py run \
  --config ~/.codex/skills/agent-forest/assets/agent-forest.config.json \
  --payload-file path/to/your-task.json \
  --preset research-squad-4 \
  --pretty
```

### 检查请求（干跑/预览）
验证代理提示词而不实际调用 API：
```bash
python ~/.codex/skills/agent-forest/scripts/agent_forest.py run \
  --config ~/.codex/skills/agent-forest/assets/agent-forest.config.json \
  --payload-file path/to/your-task.json \
  --dry-run \
  --pretty
```

## 🧠 载荷示例 (Payload)

典型的载荷定义了任务和预期的报告结构：

```json
{
  "task": "我们是否应该将核心数据库从 PostgreSQL 迁移到分布式 NoSQL 解决方案？",
  "context": "我们目前处理 10k RPS，数据集大小为 2TB，每月增长 10%。",
  "report_sections": ["执行摘要", "技术可行性", "运营风险", "成本分析"]
}
```

## 📚 文档

更多高级主题，请查看：
- [配置指南](references/configuration.md)
- [载荷架构与示例](references/payload-schema.md)
- [技能参考](SKILL.md)

---

由 Agent Forest 团队倾力打造 🌲
