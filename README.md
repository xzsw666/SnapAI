# SnapAI v0.1

SnapAI 是一个 Windows 桌面 OCR 工具，能截取屏幕上**任何不可复制的文字**（右键菜单、错误弹窗、图片文字等）并自动写入剪贴板。

**Ctrl+Shift+X → 冻结屏幕 → 框选 → OCR → 自动复制 → Ctrl+V**

## 当前功能

- **全局热键** — Ctrl+Shift+X 一键触发
- **Capture First** — 热键触发瞬间立即截图，右键菜单不会消失
- **冻结快照背景** — 框选时看到的是按下热键瞬间的屏幕冻结画面
- **四方向框选** — 支持跨屏选择（双屏异 DPI 已验证）
- **Windows 原生 OCR** — 中文、英文、中英混合均可识别，完全本地运行
- **自动剪贴板** — OCR 结果自动复制，直接 Ctrl+V 粘贴
- **ESC 取消** — 随时取消，程序不退出
- **防重复触发** — 框选期间重复热键自动忽略

## 架构

`
Ctrl+Shift+X (keyboard 库, 后台线程)
    ↓
app.py (Qt 主线程编排)
    ↓
screenshot.py → mss.grab() 全虚拟桌面快照
    ↓
selector.py → 冻结快照背景 + Win32 鼠标轮询 + 四矩形遮罩
    ↓
screenshot.py → crop_from_snapshot() (不二次截图)
    ↓
ocr.py → Windows.Media.Ocr 本地识别
    ↓
QClipboard → 系统剪贴板
`

## 项目结构

`
SnapAI/
├── app.py              # 入口，流程编排
├── shortcut.py         # 全局热键 (keyboard 库)
├── selector.py         # 屏幕区域选择器 (每屏独立 Overlay + Win32 轮询)
├── screenshot.py       # mss 截图 + 坐标映射 (Capture-First)
├── ocr.py              # Windows 原生 OCR (BMP 内存流)
├── config.py           # 配置占位
├── requirements.txt    # Python 依赖
├── SnapAI.spec         # PyInstaller 打包配置
├── .env.example        # 环境变量模板
├── .gitignore
├── LICENSE
├── docs/
│   ├── PRD.md          # 产品需求文档
│   ├── ARCHITECTURE.md # 架构决策记录
│   ├── BUILD.md        # 打包说明
│   ├── KNOWN_ISSUES.md # 已知问题
│   └── AI_PRODUCTIVITY_CASE.md # AI 辅助开发案例
└── tests/
    ├── ocr_probe.py    # OCR 验证脚本
    ├── ocr_probe.ps1   # OCR PowerShell 探针
    ├── snapshot_probe.py    # Capture-First 架构验证
    └── multimonitor_selector_probe.py  # 多屏选择器诊断
`

## 快速开始

1. 创建虚拟环境:
   `
   python -m venv .venv
   .venv\Scripts\activate
   `

2. 安装依赖:
   `
   pip install -r requirements.txt
   `

3. 运行:
   `
   .venv\Scripts\python.exe app.py
   `

4. 按 **Ctrl+Shift+X**，框选需要识别的屏幕区域
5. 去任意地方 **Ctrl+V** 粘贴

## 已知限制

- **Windows 专用** — Windows.Media.Ocr 不可跨平台
- **需要 OCR 语言包** — 在 Windows 设置 → 语言中安装对应 OCR 支持
- **Shell Flyout** — 开始菜单、Win+A 通知面板、日历弹出层等 Shell UI 可能覆盖选择器遮罩
- **OCR 准确度** — Windows 原生 OCR 约 75%：l/1、O/0 可能混淆，小字号降低准确率
- **不保存截图** — 截图仅在内存中存在，处理完成后丢弃

详见 docs/KNOWN_ISSUES.md。

## 隐私

所有文字识别在本地完成：
- 截图不会发送到任何外部服务
- 截图不会保存到磁盘
- 无需联网

## 开发历程

v0.1 的核心工程挑战是从「先选后截」(Select → Capture) 切换为「先截后选」(Capture → Select)。旧流程在激活选择器时会导致 Windows 右键菜单瞬态 UI 消失，最终截图上只有空白桌面。新流程在热键触发后立即调用 mss.grab() 冻结整个虚拟桌面，再让用户从冻结快照中框选区域。

详见 docs/ARCHITECTURE.md。

## 许可

MIT License. 详见 LICENSE。
