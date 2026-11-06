# 扭摆法测转动惯量 · 双模式实验助教

一个面向大学物理实验的 Gradio 教学程序：学生可以用**真实实验模式**记录自己的器材参数和测量数据，也可以用**虚拟实验模式**点击生成周期数据；程序负责不确定度、有效数字、图像和本地核对，AI 负责解释检查结果、批改概念题和起草实验报告。

## 功能

- **真实 / 虚拟双模式**：两种模式的数据分开保存，切换模式不会混用。
- **阶段0 器材参数**：参数可随时修改、追加；每次保存生成新版本，旧版本可载入并采用。
- **阶段1 标定**：空盘和加圆柱的总时间，不限组数；学生填 \(I_1\)、\(K\)、\(I_0\)。
- **阶段2 规则刚体**：圆筒、球体、细杆的 \(I_{\text{实验}}\)、\(I_{\text{几何}}\) 和百分偏差。
- **阶段3 平行轴**：细杆、五个对称距离、四组不对称；学生填 \(I_{\text{总}}\)、斜率和截距。
- **阶段4 图表与报告**：生成阶段2/3图表；AI 按标准实验报告结构起草报告。
- **不确定度**：A/B 类、合成、传播、有效数字和 \(k=2\) 扩展不确定度由本地程序计算。
- **本地核对 + AI 解释分离**：「核对结果（本地）」立即出结果；需要时再点「请 AI 解释」。
- **回答批改**：阶段2/3 概念题可点「请 AI 批改回答」，逐题给出判断和补充提示。
- **演示数据**：开始页「载入完整演示数据」会填好参数、周期、学生计算和回答，方便只验收按钮和图表。
- **记录**：会话 JSON 自动保存到 `records/`，不进入 Git。

## 项目结构

```text
app.py                 Gradio 事件、会话、阶段视图和演示数据
ui.py                  页面布局、控件和事件绑定
experiment.py          模式、阶段、阶段0参数版本、虚拟器材参数
stages.py              阶段1～3 测量组、结果表、检查、作废和问题
uncertainty.py         A/B 类不确定度、传播、有效数字、线性回归
charts.py              阶段2/3/4 图表
tutor.py               AI 助教、检查解释、回答批改、实验报告草稿
tasks.py               旧版教学任务与工具
torsion.py             扭摆/周期/器材计算
lab_records.py         旧版虚拟与实验室记录
session_store.py       会话 JSON 保存与事件
visuals.py             页面视觉组件
knowledge/             教学资料
tests/smoke_check.py   回归测试
SKILL.md               AI 助教教学约定
操作说明.md            学生/教师使用说明
双模式阶段化方案.md      设计与实施记录
requirements.txt       Python 依赖
启动.bat               Windows 启动脚本
```

## 环境要求

- Windows 10/11（其他系统也可，启动脚本需自己调整）
- Python 3.12（项目在 3.12 下开发）
- Git（上传 GitHub 用）

## 安装

在项目目录打开 PowerShell：

```powershell
cd D:\single_slit_tutor\single_slit_tutor
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

如果 PowerShell 阻止激活脚本，可以改用：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

## 配置 AI（可选）

不配置密钥时，测量、数据记录、本地核对和图表仍可用；AI 解释、回答批改和报告草稿会提示未配置。

推荐用环境变量，不要把密钥写进代码：

```powershell
$env:TUTOR_MODEL = "deepseek-chat"
$env:OPENAI_API_KEY = "你的密钥"
# 如使用兼容 OpenAI 协议的第三方地址：
$env:OPENAI_BASE_URL = "https://你的接口地址/v1"
```

也可以在项目根目录创建 `填写密钥.txt`，程序启动时会读取；该文件已被 `.gitignore` 排除，**不要提交到 GitHub**。具体格式见 `app.py` 的 `load_local_config()` 或现有本地文件。

> 注意：`填写密钥.txt`、`records/`、`.env` 和 `backup_*/` 都不应上传。若曾经提交过密钥，请立刻在服务商处吊销/轮换密钥，并清理 Git 历史。

## 运行

```powershell
.\.venv\Scripts\python.exe app.py
```

浏览器打开：

```text
http://127.0.0.1:7860
```

Windows 也可以双击 `启动.bat`。如果 7860 已被占用，先关闭旧进程，再启动。

## 测试

```powershell
$env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe tests\smoke_check.py
```

测试覆盖旧版周期/核对/记录、阶段0参数版本、阶段1～3计算检查、图表、虚拟数据、回答反馈入口、AI 模拟调用和 Gradio HTTP 启动。

## 数据与隐私

- `records/<学号>/session_*.json` 保存本地会话；不会自动上传。
- 发给模型的上下文不包含学号、密钥和记录路径；但包含当前阶段数据、学生填写结果和回答。
- 如果需要公开演示，建议使用 `000000` 演示会话或脱敏数据。
- 公开仓库时请先确认学生数据、截图和密钥均未提交。

## 已知限制

- 多个测量组默认取平均；如需指定某一组作为采用值，目前只能作废其他组后重新添加。
- 暂未提供 CSV/JSON 导出按钮；会话 JSON 仍自动保存。
- AI 输出依赖所配置的模型；首次使用建议先点「载入完整演示数据」再逐个按钮验收。
- 图表使用 Matplotlib 数学排版显示上下标，若本机缺少中文字体，中文标签可能显示异常。

## 许可证

当前未附带开源许可证。若计划公开仓库，请根据使用范围选择 MIT、Apache-2.0 或其他许可证后再添加 `LICENSE` 文件。
