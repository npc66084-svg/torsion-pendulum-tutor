# 扭摆法测转动惯量 · 双模式实验助教

[![tests](https://github.com/npc66084-svg/torsion-pendulum-tutor/actions/workflows/ci.yml/badge.svg)](https://github.com/npc66084-svg/torsion-pendulum-tutor/actions/workflows/ci.yml)

一个面向大学物理实验的 Gradio 教学程序：学生可以用**真实实验模式**记录自己的器材参数和测量数据，也可以用**虚拟实验模式**点击生成周期数据；程序负责不确定度、有效数字、图像和本地核对，AI 负责解释检查结果、批改概念题和起草实验报告。

## 文档导航

| 文档 | 作用 |
|---|---|
| [文档索引](docs/README.md) | 按角色选择入口 |
| [使用说明](docs/使用说明.md) | 单机版教师准备、学生操作、各阶段按钮和记录说明 |
| [设计说明](docs/设计说明.md) | 单机版模块架构、数据模型、阶段流程、不确定度和 AI 边界 |
| [开发记录](docs/开发记录.md) | 单机版实施批次、关键修复和测试 |
| [部署与维护](docs/部署与维护.md) | 安装、密钥配置、启动、测试、Git/GitHub 和常见故障 |
| [局域网试点规划](docs/局域网试点规划.md) | 试点的目标、指标、计划、隔离要求和交接约束 |
| [局域网开发记录](docs/局域网开发记录.md) | 试点分支按时间记录的做法和验证 |
| [多会话改造记录](docs/多会话改造记录.md) | 试点当前实现、运行、回滚、验收修复和已知限制 |
| [试点运行手册](docs/试点运行手册.md) | 组网、配置、启动、学生接入、防火墙、备份和排错 |
| [试点反馈表](docs/试点反馈表.md) | 每次课后填写 |

AI 教学约定见 [SKILL.md](SKILL.md)，教学知识库见 [knowledge/torsion_pendulum.md](knowledge/torsion_pendulum.md)。

## 局域网试点（lan-pilot 分支）

`main` 是单机版；`lan-pilot` 分支增加「一台主机、多个学生通过局域网访问」的能力：

- 课程码 + 教师名单 + 可选个人识别码，登录失败限速
- 每个浏览器一份会话，刷新可恢复
- 同一学号重复登录会踢掉旧窗口，并提示原因
- AI 调用进线程池，按学生限制每分钟次数和每天报告草稿次数
- 单机模式完全不受影响：不设环境变量时仍是 `127.0.0.1:7860`、单会话、无课程码

快速开始：

```powershell
Copy-Item .\试点配置.example.txt .\试点配置.txt
# 编辑 试点配置.txt：COURSE_CODE、ROSTER_FILE
# 按 docs/名单示例.csv 准备 名单.csv（UTF-8）
.\启动试点.bat
```

学生浏览器打开 `http://<主机IP>:7862/`。组网、防火墙、固定 IP 和教室注意事项见[试点运行手册](docs/试点运行手册.md)。

## 功能概览

- **全屏开始页**：原理速览、学号登录和演示入口；上方不放大段说明，帮助入口收进右下角浮窗。
- **真实 / 虚拟双模式**：两种模式的数据分开保存，切换模式不会混用。
- **阶段0 器材参数**：参数可随时修改、追加；每次保存生成新版本，旧版本可载入并采用。
- **阶段1 标定**：空盘和加圆柱的总时间，不限组数；学生填 \(I_1\)、\(K\)、\(I_0\)。
- **阶段2 规则刚体**：圆筒、球体、细杆的 \(I_{\text{实验}}\)、\(I_{\text{几何}}\) 和百分偏差。
- **阶段3 平行轴**：细杆、五个对称距离、四组不对称；学生填 \(I_{\text{总}}\)、斜率和截距。
- **阶段4 图表与报告**：先「生成图表」，再「生成实验报告草稿」；AI 按标准实验报告结构起草报告；可导出原始数据 CSV 和 Word 报告（.docx）。
- **不确定度**：A/B 类、合成、传播和有效数字由本地程序计算，界面给出合成标准不确定度 \(u_c\)（k=1）；报告若要求扩展不确定度，取 \(U=2u_c\)。
- **本地核对 + AI 解释分离**：「核对结果（本地）」立即出结果；需要时再点「请 AI 解释」。
- **回答批改**：阶段2/3 概念题可点「请 AI 批改回答」，逐题给出判断和补充提示。
- **演示数据**：开始页「载入完整演示数据」会填好参数、周期、学生计算和回答，方便只验收按钮和图表。
- **悬浮帮助窗**：同一个可缩放浮窗里有三个标签——3 分钟上手、实验原理、问助教；开始页也能打开上手和原理。四边或四角可拖动调整窗口大小；AI 检查、回答批改和报告草稿分别显示为独立消息。
- **记录**：会话 JSON 自动保存到 `records/`，不进入 Git。

## 快速开始

```powershell
cd <项目目录>
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

代码不依赖本地目录名；GitHub 仓库为 `torsion-pendulum-tutor`。

浏览器打开 `http://127.0.0.1:7860`。Windows 也可以双击 `启动.bat`。

不配置 AI 密钥时，测量、记录、本地核对和图表仍可用；AI 解释、回答批改和报告草稿会提示未配置。配置方法见[部署与维护](docs/部署与维护.md)。

## 项目结构

```text
app.py                 Gradio 事件、会话、阶段视图和演示数据
ui.py                  页面布局、控件和事件绑定
experiment.py          模式、阶段、阶段0参数版本、虚拟器材参数
stages.py              阶段1～3 测量组、结果表、检查、作废和问题
uncertainty.py         A/B 类不确定度、传播、有效数字、线性回归
charts.py              阶段2/3/4 图表（误差棒、残差）
report_docx.py         导出 Word 实验报告（表格 + 图）
tutor.py               AI 助教、检查解释、回答批改、实验报告草稿
tasks.py               旧版教学任务与工具
torsion.py             扭摆/周期/器材计算
lab_records.py         旧版虚拟与实验室记录
session_store.py       会话 JSON 保存与事件
session_registry.py    试点浏览器 token、会话注册表和恢复
pilot_auth.py          试点课程码、名单、识别码和登录限速
pilot_ai.py            试点 AI 线程池和限额
scripts/               试点健康检查、备份脚本
visuals.py             页面视觉组件
knowledge/             教学资料
tests/smoke_check.py   端到端回归测试（单机/试点两种模式）
tests/test_uncertainty.py    单元测试（不确定度、标定、回归、出图）
tests/test_pilot_sessions.py  试点多会话、认证和恢复测试
tests/test_pilot_ai.py       试点 AI 线程池和限流测试
tests/test_pilot_ops.py      健康检查和备份脚本测试
SKILL.md               AI 助教教学约定
docs/                  整合后的项目文档
pyproject.toml         pytest/ruff 配置
requirements.txt       Python 依赖
requirements-dev.txt   测试依赖（pytest）
requirements-lock.txt  本机验证过的完整版本（可选，便于复现）
.github/workflows/     CI：单元测试 + 单机/试点冒烟测试
LICENSE                MIT
启动.bat               单机版启动脚本
启动试点.bat / .ps1     局域网试点启动脚本
试点配置.example.txt     试点配置模板（复制为 试点配置.txt）
```

## 测试

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest tests\test_uncertainty.py tests\test_pilot_sessions.py tests\test_pilot_ai.py tests\test_pilot_ops.py -q
.\.venv\Scripts\python.exe tests\smoke_check.py
```

试点模式另跑一次，需要测试课程码和名单：

```powershell
$env:PILOT_MODE="1"; $env:COURSE_CODE="TEST2026"; $env:ROSTER_FILE="docs\名单示例.csv"
.\.venv\Scripts\python.exe tests\smoke_check.py
```

CI 配置在 `.github/workflows/ci.yml`，单机冒烟和试点冒烟都会跑。

## 数据与隐私

- `records/<学号>/session_*.json` 保存本地会话；不会自动上传。
- 发给模型的上下文不包含学号、密钥和记录路径；但包含当前阶段数据、学生填写结果和回答。
- `填写密钥.txt`、`records/`、`.env`、`.venv/`、`backup_*/`、`试点配置.txt`、`名单.csv` 和本地截图均在 `.gitignore` 中。
- 公网仓库前请确认学生数据、课程码、名单和密钥均未提交；若曾提交密钥，请立刻吊销/轮换并清理历史。

## 状态

- 单机版覆盖真实/虚拟模式、阶段0～4、不确定度、AI 检查/回答批改/报告草稿、演示数据、CSV/Word 导出和可缩放帮助浮窗。
- `lan-pilot` 分支已具备局域网试点的多会话、课程码/名单、AI 限流、刷新恢复和踢旧窗口，等待教室试点。
- 已知限制见[多会话改造记录](docs/多会话改造记录.md)。

## 版权与许可

© 2026 复旦大学物理系（Department of Physics, Fudan University）。本项目用于物理实验教学。

代码以 MIT 许可证发布，见 [LICENSE](LICENSE)。
