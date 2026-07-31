# 全中文、全球模拟呼号与离线永久会员实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有离线摩斯电码生成器改为全中文界面，提供覆盖全球业余无线电实体的标准模拟呼号，并加入普通用户五分钟限制和单机永久会员。

**Architecture:** 用户界面只保存稳定的内部代码，所有显示值通过中文映射转换。全球呼号规则放在独立的版本化数据文件中，由纯函数加载和生成。授权模块负责机器码、爱德华曲线签名和本地授权文件，主程序仅含公钥，私钥只供独立管理工具使用。

**Tech Stack:** Python 3.13、Tkinter、lameenc、cryptography、pytest、PyInstaller。

## Global Constraints

- 软件运行时完全不联网。
- 全球呼号只按规则模拟，不代表真实签发。
- 所有用户可见文案必须为中文；呼号和文件扩展名是技术数据例外。
- 普通用户每次最多五分钟，永久会员无软件时长上限。
- 生产私钥不得提交到 Git，也不得进入主程序发行包。
- 保留 MP3 默认输出和 WAV 可选输出的内部兼容性。

---

### Task 1: 中文显示映射与设置校验

**Files:**
- Modify: `morse_app/settings.py`
- Modify: `morse_app/core.py`
- Modify: `tests/test_settings.py`
- Modify: `tests/test_core.py`

**Interfaces:**
- Produces: `validate_settings(settings: AppSettings, *, is_member: bool = False) -> None`
- Produces: 内部值 `long/short`、`mp3/wav` 保持不变，界面负责中文映射。

- [ ] **Step 1: 写普通用户和会员时长失败测试**

```python
def test_non_member_rejects_more_than_five_minutes():
    with pytest.raises(ValueError, match="永久会员"):
        validate_settings(replace(AppSettings(), duration_seconds=301))

def test_member_has_no_product_duration_limit():
    validate_settings(replace(AppSettings(), duration_seconds=86_400), is_member=True)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_settings.py -v`
Expected: FAIL，因为现有签名没有 `is_member` 且仍限制 3600 秒。

- [ ] **Step 3: 实现最小时长和会员校验并中文化错误信息**

```python
def validate_settings(settings: AppSettings, *, is_member: bool = False) -> None:
    if settings.duration_seconds < 5:
        raise ValueError("生成时长不能少于 5 秒")
    if not is_member and settings.duration_seconds > 300:
        raise ValueError("普通用户每次最多生成 5 分钟，超过后需要永久会员")
```

将 `WPM`、`Hz`、`Farnsworth`、`long`、`short` 从所有用户错误信息中替换为“字/分钟”“赫兹”“间隔降速”“普通数字”“缩短数字”。

- [ ] **Step 4: 运行设置和核心测试**

Run: `pytest tests/test_settings.py tests/test_core.py -v`
Expected: PASS。

- [ ] **Step 5: 提交**

```bash
git add morse_app/settings.py morse_app/core.py tests/test_settings.py tests/test_core.py
git commit -m "feat: add Chinese duration validation"
```

### Task 2: 全球模拟呼号规则数据

**Files:**
- Create: `morse_app/data/global_callsign_rules.json`
- Create: `morse_app/callsign_rules.py`
- Modify: `morse_app/callsigns.py`
- Modify: `tests/test_callsigns.py`

**Interfaces:**
- Produces: `CallsignRule(entity: str, prefixes: tuple[str, ...], digit_mode: str, suffix_lengths: tuple[int, ...])`
- Produces: `load_global_rules() -> dict[str, CallsignRule]`
- Produces: `global_entity_names() -> tuple[str, ...]`
- Produces: `generate_global_callsign(entity: str, rng: random.Random) -> str`

- [ ] **Step 1: 写数据覆盖、可重复和错误处理测试**

```python
def test_global_rules_cover_all_declared_entities():
    names = global_entity_names()
    assert len(names) >= 300
    assert "中国" in names
    assert "美国" in names

def test_every_entity_generates_ascii_callsign():
    for name in global_entity_names():
        value = generate_global_callsign(name, random.Random(7))
        assert re.fullmatch(r"[A-Z0-9/]+", value), (name, value)

def test_seeded_global_callsign_is_repeatable():
    assert generate_global_callsign("日本", random.Random(9)) == generate_global_callsign("日本", random.Random(9))
```

- [ ] **Step 2: 运行呼号测试确认失败**

Run: `pytest tests/test_callsigns.py -v`
Expected: FAIL，因为现有数据只有八个国家。

- [ ] **Step 3: 建立版本化 JSON 数据和严格加载器**

数据顶层包含 `version`、`source_note_zh`、`entities`；每个实体使用中文名称和至少一个合法分配前缀。加载器拒绝空前缀、重复中文名称、非大写字母数字前缀和不支持的后缀长度。数据依据写为国际电联国际呼号序列和业余无线电国家文件，界面不得称其为真实呼号库。

```python
@dataclass(frozen=True, slots=True)
class CallsignRule:
    entity: str
    prefixes: tuple[str, ...]
    digit_mode: str
    suffix_lengths: tuple[int, ...]
```

- [ ] **Step 4: 改造生成器并保留中国专用规则**

当实体为“中国”时继续调用省级规则；其他实体从数据中随机选择前缀、数字和 1 至 3 位后缀。提供“随机全球地区”，由调用方先随机选择实体。删除八国硬编码分支和依赖八国正则的判断。

- [ ] **Step 5: 运行呼号测试**

Run: `pytest tests/test_callsigns.py -v`
Expected: PASS，且全部实体均能生成格式有效的结果。

- [ ] **Step 6: 提交**

```bash
git add morse_app/data/global_callsign_rules.json morse_app/callsign_rules.py morse_app/callsigns.py tests/test_callsigns.py
git commit -m "feat: add global simulated callsign rules"
```

### Task 3: 机器码和数字签名授权核心

**Files:**
- Create: `morse_app/licensing.py`
- Create: `morse_app/public_key.txt`
- Modify: `.gitignore`
- Modify: `requirements.txt`
- Modify: `pyproject.toml`
- Create: `tests/test_licensing.py`

**Interfaces:**
- Produces: `machine_code(raw_id: str | None = None) -> str`
- Produces: `sign_activation(machine_code: str, private_key: bytes) -> str`
- Produces: `verify_activation(code: str, expected_machine_code: str, public_key: bytes) -> bool`
- Produces: `load_saved_activation(path: Path | None = None) -> str`
- Produces: `save_activation(code: str, path: Path | None = None) -> None`

- [ ] **Step 1: 写签名、篡改和跨机器测试**

```python
def test_activation_is_bound_to_machine(ed25519_keys):
    private, public = ed25519_keys
    code = sign_activation("AAAA-BBBB", private)
    assert verify_activation(code, "AAAA-BBBB", public)
    assert not verify_activation(code, "CCCC-DDDD", public)

def test_tampered_activation_is_rejected(ed25519_keys):
    private, public = ed25519_keys
    code = sign_activation("AAAA-BBBB", private)
    assert not verify_activation(code[:-1] + "A", "AAAA-BBBB", public)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_licensing.py -v`
Expected: FAIL，因为授权模块不存在。

- [ ] **Step 3: 实现隐私友好的机器码**

Windows 下读取注册表机器标识，仅在内存中使用原值；使用带应用域前缀的 SHA-256，显示前 20 个十六进制字符并按四位分组。读取失败时抛出中文错误，不随机生成会变化的机器码。

- [ ] **Step 4: 实现爱德华曲线签名和原子保存**

激活载荷固定为 `永久会员|机器码`，使用 URL 安全 Base64 表示载荷和签名。解析失败、签名失败或机器码不匹配统一返回 `False`。授权文件写入 `%APPDATA%/摩斯电码生成器/永久会员授权.txt`，使用临时文件加替换。

- [ ] **Step 5: 增加依赖和私钥忽略规则**

在运行依赖中固定兼容 Python 3.13 的 `cryptography` 版本；`.gitignore` 增加 `owner-private-key.txt` 和 `owner-release/`。提交的 `public_key.txt` 只含公钥。

- [ ] **Step 6: 运行授权测试**

Run: `pytest tests/test_licensing.py -v`
Expected: PASS。

- [ ] **Step 7: 提交**

```bash
git add .gitignore requirements.txt pyproject.toml morse_app/licensing.py morse_app/public_key.txt tests/test_licensing.py
git commit -m "feat: add offline permanent licensing"
```

### Task 4: 独立会员激活码生成工具

**Files:**
- Create: `license_admin.py`
- Create: `morse_app/license_admin_gui.py`
- Create: `tests/test_license_admin.py`
- Create: `license-admin.spec`
- Modify: `build.ps1`

**Interfaces:**
- Consumes: `sign_activation()` from Task 3.
- Produces: `load_owner_private_key(path: Path) -> bytes`
- Produces: 独立程序 `会员激活码生成工具.exe`。

- [ ] **Step 1: 写私钥缺失和激活码生成测试**

```python
def test_admin_requires_external_private_key(tmp_path):
    with pytest.raises(ValueError, match="私钥文件"):
        load_owner_private_key(tmp_path / "owner-private-key.txt")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_license_admin.py -v`
Expected: FAIL，因为管理工具不存在。

- [ ] **Step 3: 实现全中文管理窗口**

窗口只包含机器码输入、生成、复制和状态提示。启动时从可执行文件同目录读取 `owner-private-key.txt`；缺失或无效时禁用生成按钮。工具不联网、不保存客户资料。

- [ ] **Step 4: 增加独立打包入口**

`license-admin.spec` 只包含管理工具代码，不包含到主程序构建。`build.ps1` 分别生成主程序公开发行目录和 `owner-release` 私有目录；私钥由所有者手工放入私有目录，不进入 Git。

- [ ] **Step 5: 运行测试和打包冒烟检查**

Run: `pytest tests/test_license_admin.py tests/test_licensing.py -v`
Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add license_admin.py morse_app/license_admin_gui.py tests/test_license_admin.py license-admin.spec build.ps1
git commit -m "feat: add owner activation tool"
```

### Task 5: 主窗口全中文化和会员流程

**Files:**
- Modify: `morse_app/gui.py`
- Modify: `tests/test_gui_logic.py`
- Create: `tests/test_chinese_ui.py`

**Interfaces:**
- Consumes: `global_entity_names()`、`verify_activation()`、`machine_code()`。
- Produces: `is_current_machine_member() -> bool`
- Produces: 中文显示值到内部值的双向映射。

- [ ] **Step 1: 写中文映射和会员限制测试**

```python
def test_chinese_display_values_map_to_internal_codes(tmp_path):
    values = valid_form_values(tmp_path) | {"number_style": "普通数字", "output_format": "压缩音频"}
    request = build_generation_request(values, random.Random(1), is_member=False)
    assert request.export.number_style == "long"
    assert request.export.output_format == "mp3"

def test_non_member_cannot_build_six_minute_request(tmp_path):
    with pytest.raises(ValueError, match="永久会员"):
        build_generation_request(valid_form_values(tmp_path) | {"duration_seconds": "360"}, random.Random(1), is_member=False)
```

- [ ] **Step 2: 运行界面逻辑测试确认失败**

Run: `pytest tests/test_gui_logic.py tests/test_chinese_ui.py -v`
Expected: FAIL。

- [ ] **Step 3: 中文化全部控件和输出文案**

使用“间隔降速”“字/分钟”“赫兹”“普通数字”“缩短数字”“压缩音频”“波形音频”“生成音频和同步字幕”。文件名使用“每分钟…字”和“…赫兹”。全球呼号提示固定为“按国际前缀及地区格式模拟生成，不代表真实签发”。移除本地真实呼号导入控件和模式。

- [ ] **Step 4: 增加会员状态和激活窗口**

主窗口显示“普通用户”或“永久会员”。激活窗口支持复制机器码、粘贴激活码、保存并即时刷新状态。普通用户超过五分钟时不启动后台线程，并提供打开激活窗口的操作。

- [ ] **Step 5: 增加用户可见英文扫描测试**

测试收集显示映射、窗口常量、错误文案和字幕元数据，拒绝 `WPM|Hz|Farnsworth|long|short|Morse Code Practice`。格式扩展名不在扫描范围。

- [ ] **Step 6: 运行界面逻辑测试**

Run: `pytest tests/test_gui_logic.py tests/test_chinese_ui.py -v`
Expected: PASS。

- [ ] **Step 7: 提交**

```bash
git add morse_app/gui.py tests/test_gui_logic.py tests/test_chinese_ui.py
git commit -m "feat: add Chinese membership interface"
```

### Task 6: 长音频分块导出和中文字幕

**Files:**
- Modify: `morse_app/core.py`
- Modify: `morse_app/content.py`
- Modify: `morse_app/exporters.py`
- Modify: `tests/test_exporters.py`
- Modify: `tests/test_content.py`

**Interfaces:**
- Produces: `iter_pcm_chunks(events, frequency_hz, *, sample_rate=44_100, chunk_seconds=10) -> Iterator[bytes]`
- Produces: `write_wav_chunks(path, chunks, sample_rate=44_100) -> None`
- Produces: `write_mp3_chunks(path, chunks, sample_rate=44_100) -> None`

- [ ] **Step 1: 写分块输出和中文字幕测试**

```python
def test_pcm_chunks_stay_bounded():
    chunks = list(iter_pcm_chunks(long_timeline, 700, chunk_seconds=1))
    assert chunks
    assert max(map(len, chunks)) <= 44_100 * 2

def test_lrc_metadata_is_chinese(tmp_path):
    text = write_and_read_lrc(tmp_path)
    assert "摩斯电码练习" in text
    assert "字/分钟" in text
    assert "Morse Code Practice" not in text
```

- [ ] **Step 2: 运行导出测试确认失败**

Run: `pytest tests/test_exporters.py tests/test_content.py -v`
Expected: FAIL，因为当前实现一次性创建完整 PCM。

- [ ] **Step 3: 实现固定大小 PCM 分块**

分块迭代器按时间窗口渲染，保持音调相位和淡入淡出边界一致。WAV 逐块写帧；lameenc 编码器逐块 `encode()`，最后调用 `flush()`。任何异常都删除临时文件，不覆盖已有输出。

- [ ] **Step 4: 中文化字幕和文件名元数据**

标题改为“摩斯电码练习”，速度值改为“每分钟…字”，模拟呼号标记改为“标准模拟呼号”。LRC 必需的时间戳和扩展名保持技术格式。

- [ ] **Step 5: 运行导出和内容测试**

Run: `pytest tests/test_exporters.py tests/test_content.py -v`
Expected: PASS。

- [ ] **Step 6: 提交**

```bash
git add morse_app/core.py morse_app/content.py morse_app/exporters.py tests/test_exporters.py tests/test_content.py
git commit -m "feat: stream long audio exports"
```

### Task 7: 文档、打包和最终验证

**Files:**
- Modify: `README.md`
- Modify: `morse-generator.spec`
- Modify: `tests/test_package.py`

**Interfaces:**
- Produces: 公开主程序和所有者专用激活工具两个独立产物。

- [ ] **Step 1: 更新全中文使用说明**

说明标准模拟呼号不代表真实签发、普通用户五分钟限制、永久会员激活流程、私钥保管和重新激活规则。删除真实全球呼号库的描述及英文示例列名。

- [ ] **Step 2: 更新主程序打包数据**

确保主程序包含全球规则 JSON 和公钥，不包含 `owner-private-key.txt`、管理工具代码或 `owner-release`。管理工具单独打包。

- [ ] **Step 3: 运行完整测试**

Run: `pytest -q`
Expected: 全部 PASS。

- [ ] **Step 4: 构建两个程序**

Run: `powershell -ExecutionPolicy Bypass -File .\build.ps1`
Expected: 生成 `dist/摩斯电码生成器.exe` 和 `owner-release/会员激活码生成工具.exe`，主程序公开目录中没有私钥。

- [ ] **Step 5: 执行离线冒烟测试**

依次验证普通用户生成五分钟、拒绝六分钟；用管理工具为本机生成激活码；激活后生成超过五分钟；生成中国和至少十个不同地区的模拟呼号；分别输出压缩音频和波形音频；断网状态下重复以上关键流程。

- [ ] **Step 6: 检查工作区和发行内容**

Run: `git status --short && Get-ChildItem -Recurse dist,owner-release`
Expected: 只有预期文档或构建忽略文件；公开发行目录没有任何私钥。

- [ ] **Step 7: 提交**

```bash
git add README.md morse-generator.spec tests/test_package.py
git commit -m "docs: document Chinese offline membership release"
```

