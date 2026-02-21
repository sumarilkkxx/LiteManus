# LiteManus
<p align="center"><b>仿 Manus 逻辑的轻量级 Agent 框架</b></p>
<p align="center">
  <a href="README.md">English</a> | <a href="README_zh.md">简体中文</a>
</p>

## 📌 项目介绍
**LiteManus** 是一个基于 **LangGraph** 与 **LangChain** 构建的轻量级智能体（Agent）框架。  
它能够将用户请求转化为可执行的行动计划，通过工具调用（tool-calling）逐步执行任务，并基于执行过程中的实时观察结果迭代更新策略，最终生成一份完整的 **Markdown 报告（`workspace/report.md`）**，并在报告中嵌入执行过程中生成的分析图片。

---

## ✨ 主要特性

- **规划 → 执行 → 观察 → 再规划** 的闭环流程（LangGraph 状态机驱动）
- **工具调用执行**：运行 shell 命令、读写文件、生成图表/图片等
- **Workspace 统一管理产物**：所有中间文件与可视化结果均输出到 `workspace/`
- **最终 Markdown 报告生成**：输出 `workspace/report.md`，并用 Markdown 语法嵌入图片

---

## 🏗 架构与工作流程

本项目实现了一个 LangGraph 状态机工作流：

<p align="center">
  <img src="image.png" alt="架构图" width="300" />
</p>

### 节点职责说明

#### `create_planner_node`
- 以结构化 JSON（目标 Goal + 步骤 Steps）的形式生成初始计划。
- 每个步骤包含：
  - 可执行描述（要做什么）
  - 预期输出（应该产生什么结果/文件）
  - 验证方式（如何判断该步完成）

#### `execute_node`
- 执行当前待处理的步骤。
- 通过工具完成：
  - 运行 shell 命令
  - 在 `workspace/` 下创建/修改文件
- 产生 **observations（观察结果）**，例如：
  - 执行结果与关键指标
  - 生成的文件名/路径
  - 生成的图片（如 `.png` 图表）

#### `update_planner_node`
- 根据最新 observations 对计划进行迭代更新。
- 可能的调整包括：
  - 细化剩余步骤
  - 补充遗漏步骤
  - 删除不必要步骤
  - 重新排序执行顺序

#### `all_completed`
- 判断是否所有步骤都已完成：
  - **NO** → 回到 `execute_node` 继续执行
  - **YES** → 进入 `report_node` 生成报告

#### `report_node`
- 将最终结果汇总为 **Markdown** 报告。
- 写入 `workspace/report.md`。
- 使用标准 Markdown 语法嵌入图片：
  - `![标题](path/to/image.png)`

---

## 🚀 安装

### 1）创建并激活虚拟环境（推荐）

**PowerShell（Windows）：**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**bash/zsh（macOS/Linux）：**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2）安装依赖

```bash
pip install -r requirements.txt
```

---

## 🛠 运行

### 1）配置环境变量

LiteManus 使用 **ChatOpenAI**，通过环境变量读取配置。

#### 必填

- `API_KEY`：你的 LLM 服务商 Key

#### 可选

- `BASE_URL`：默认 `https://api.getgoapi.com/v1`
- `WORKSPACE_DIR`：默认 `<project_root>/workspace`

##### PowerShell（Windows）

```powershell
$env:API_KEY="YOUR_KEY_HERE"
$env:BASE_URL="https://api.getgoapi.com/v1"   # 可选
$env:WORKSPACE_DIR="$pwd\workspace"          # 可选
```

##### bash / zsh（Linux/macOS）

```bash
export API_KEY="YOUR_KEY_HERE"
export BASE_URL="https://api.getgoapi.com/v1"   # 可选
export WORKSPACE_DIR="$(pwd)/workspace"         # 可选
```

> 小提示：如果你希望这些变量在每次打开终端后都自动生效，可以将其写入 shell 配置文件（如 PowerShell Profile、`~/.zshrc`、`~/.bashrc`）。

### 2）运行智能体

执行工作流（主入口通常在 `graph.py` 中）：

```bash
python graph.py
```

---

## 📦 输出说明

所有生成产物（中间文件、图表、图片等）默认写入：

- `workspace/`

最终报告文件：

- `workspace/report.md`

打开 `workspace/report.md` 即可同时查看文本结果与嵌入的可视化图片（例如执行过程中保存的 `.png` 图表）。

---

## 🖼 报告中嵌入图片示例

如果在运行过程中生成图片 `workspace/figures/plot.png`，则报告可写入：

```md
![实验图表](figures/plot.png)
```

---

## 🧯 常见问题排查（Troubleshooting）

- **提示 `API_KEY` 未设置 / 鉴权失败**
  - 确保在当前终端会话中已正确设置 `API_KEY` 后再运行。
- **找不到 workspace 目录 / 写入失败**
  - 确认 `workspace/` 存在，或将 `WORKSPACE_DIR` 指向一个有效目录。
- **依赖安装报错**
  - 建议使用全新虚拟环境后重新执行 `pip install -r requirements.txt`。

