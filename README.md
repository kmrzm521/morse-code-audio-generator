# 摩斯电码生成器 v6.0（离线版）

这是从旧版 v5.0 重新设计的精简版 Windows 小程序。它不联网，默认生成 MP3，也支持 WAV，并为每个音频生成同名的同步 LRC。

## 主要功能

- 随机字母、数字、字母数字、标点、通联符号和 Q 简语
- 数字长码与短码
- 中国、美国、日本、德国、俄罗斯、英国、加拿大、澳大利亚模拟呼号
- 本地 TXT/CSV 真实呼号表
- 自定义文本
- 5–60 WPM、300–1200 Hz
- 可选 Farnsworth 有效速度
- WAV、MP3 和同步 LRC
- 自动防止覆盖已有文件
- 本地保存上次设置

模拟生成的呼号仅供听抄训练，不代表呼号已经由主管机构正式指配，也不能据此用于发射。

## 安装与运行源码

需要 64 位 Python 3.13。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

运行时不需要网络。MP3 由体积很小的 `lameenc` 在本机直接编码，不需要 FFmpeg。

## 使用方法

1. 选择内容类型。
2. 设置每组字符、时长、WPM 和音调频率。
3. 如需 Farnsworth，勾选后设置低于字符速度的有效 WPM。
4. 选择 MP3 或 WAV，并指定输出目录。
5. 点击“生成音频和 LRC”。

自定义文本会完整生成，不按目标时长裁剪。随机内容按完整字符组追加，最终时长可能比目标多一个完整组。

## 本地真实呼号表

程序不会下载或上传呼号数据。

- TXT：每行一个呼号。
- CSV：需要 `callsign`、`call` 或 `呼号` 列，列名不区分大小写。
- 文件按 UTF-8 或带 BOM 的 UTF-8 读取。
- 程序会转大写、去重，并过滤明显不符合内置国家格式的内容。

CSV 示例：

```csv
callsign,note
BG2GNR,example
JA1ABC,example
```

## 时序说明

点划与间隔遵循 ITU-R M.1677-1：

- 点：1 单位
- 划：3 单位
- 同一字符内：1 单位
- 字符之间：3 单位
- 单词或字符组之间：7 单位

字符速度使用 PARIS 约定，点长为 `1.2 / WPM` 秒。44.1 kHz、16 位、单声道和默认 700 Hz 是本程序的工程参数，不是 ITU 强制参数。

参考：[ITU-R M.1677-1](https://www.itu.int/rec/R-REC-M.1677-1-200910-I/)、[工信部业余无线电台呼号编制要求](https://wap.miit.gov.cn/cms_files/filemanager/1226211233/attach/20238/e3a97cec523441028cc51de62886101c.pdf)。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

## 打包 EXE

先安装开发依赖，再运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

成品位于 `dist\摩斯电码生成器.exe`。打包脚本不会联网或自动安装依赖；缺少依赖时会明确退出。
