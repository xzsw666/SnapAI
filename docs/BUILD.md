# SnapAI 打包说明 (PyInstaller)

## 前提条件

- Windows 10/11
- Python 3.12+
- PyInstaller >= 6.0

## 打包命令

```powershell
pyinstaller --onefile --windowed --name SnapAI app.py
```

或使用项目中的 `SnapAI.spec`：

```powershell
pyinstaller SnapAI.spec
```

## 已知打包问题

### Conda 环境缺失 ffi.dll

如果使用 Conda 管理的 Python 环境，打包后的 exe 可能因缺少 `ffi.dll` / `ffi-7.dll` / `ffi-8.dll` 而无法运行。

**原因**：`winrt-runtime` 依赖 `cffi`，Conda 分发的 Python 可能缺少这些 DLL。

**解决方案**：

1. **推荐**：使用非 Conda Python（如 python.org 官方分发）创建虚拟环境
2. **或**：手动将 Conda 环境中的 ffi DLL 复制到 dist 目录
3. **或**：修改 `SnapAI.spec`，在 `binaries` 中添加 ffi DLL

### 路径说明

以下路径因机器而异：

- Python 路径：`.venv\Scripts\python.exe`
- 打包输出：`dist\SnapAI.exe`

## 开发模式运行

```powershell
.venv\Scripts\python.exe app.py
```

## 依赖清单

```
PySide6
keyboard
mss
winrt-runtime
winrt-Windows.Media.Ocr
winrt-Windows.Graphics.Imaging
winrt-Windows.Storage.Streams
```
