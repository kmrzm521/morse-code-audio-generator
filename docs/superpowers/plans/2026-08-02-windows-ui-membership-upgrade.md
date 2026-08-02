# Windows 界面与会员说明升级实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将数字编码显示改为“长码/短码”，格式显示改为 `MP3/WAV`，完善永久会员获取说明，并生成新的 Windows 正式版。

**Architecture:** 仅修改 Tkinter 显示映射和激活窗口，内部编码值保持不变。通过兼容别名让旧设置继续生效，使用现有 PyInstaller 流程构建单文件程序。

**Tech Stack:** Python 3.13、Tkinter、pytest、PyInstaller、GitHub Releases

## Global Constraints

- 主程序生成音频时保持完全离线。
- 内部数字编码值保持 `long`、`short`。
- 内部输出格式值保持 `mp3`、`wav`。
- 所有者私钥和激活工具不得进入公开发行附件。

---

### Task 1: 显示名称与旧设置兼容

**Files:**
- Modify: `morse_app/gui.py`
- Modify: `tests/test_gui_logic.py`
- Modify: `tests/test_chinese_ui.py`

**Interfaces:**
- Consumes: `NUMBER_STYLE_LABELS`、`OUTPUT_FORMAT_LABELS` 和 `build_generation_request()`。
- Produces: 新显示名称及旧名称到既有内部值的兼容转换。

- [ ] **Step 1: 写入失败测试**

断言显示选项为 `("长码", "短码", "MP3", "WAV")`，并断言旧名称仍映射到原内部值。

- [ ] **Step 2: 运行测试并确认因旧显示名称失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_gui_logic.py tests/test_chinese_ui.py -q`

- [ ] **Step 3: 最小化修改界面映射和默认值**

保留 `long/short/mp3/wav`，增加旧中文名称兼容表。

- [ ] **Step 4: 运行相关测试**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_gui_logic.py tests/test_chinese_ui.py -q`

### Task 2: 永久会员获取说明

**Files:**
- Modify: `morse_app/gui.py`
- Modify: `tests/test_chinese_ui.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: 机器码复制、激活验证和系统浏览器能力。
- Produces: 正确邮箱、三步说明、复制邮箱和打开项目主页按钮。

- [ ] **Step 1: 写入失败测试**

断言主程序包含 `kmrzm520@gmail.com`、GitHub 项目地址和会员获取说明。

- [ ] **Step 2: 运行测试并确认因文案缺失失败**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_chinese_ui.py -q`

- [ ] **Step 3: 调整激活窗口和 README**

增加说明与按钮，只有用户点击时才打开浏览器。

- [ ] **Step 4: 运行完整测试**

Run: `.\.venv\Scripts\python.exe -m pytest -q`

### Task 3: 构建与发行升级版

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`
- Build: `dist/摩斯电码生成器.exe`

**Interfaces:**
- Consumes: 通过测试的源代码和现有 `build.ps1`。
- Produces: Windows 64 位单文件程序和对应 GitHub Release 附件。

- [ ] **Step 1: 将版本号升级为 `6.1.0` 并更新说明**

- [ ] **Step 2: 运行完整测试**

Run: `.\.venv\Scripts\python.exe -m pytest -q`

- [ ] **Step 3: 构建程序并计算 SHA-256**

Run: `powershell -ExecutionPolicy Bypass -File .\build.ps1`

- [ ] **Step 4: 确认公开附件只有主程序**

检查 `dist`，不得上传 `owner-release` 或 `owner-private-key.txt`。

- [ ] **Step 5: 提交、推送并创建 `v6.1.0` 正式版本**

上传 Windows 64 位主程序，发布后从 GitHub 端核对附件摘要。
