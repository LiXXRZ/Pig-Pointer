# 贡献指南

谢谢你愿意改进猪猪指针。

## 本地开发

```powershell
pip install -r requirements.txt
python pig_pointer.py
```

## 打包验证

```powershell
pip install -r requirements-dev.txt
.\build.ps1
```

打包结果会生成到：

```text
dist\PigPointer.exe
```

## 提交前检查

建议至少运行：

```powershell
python -m py_compile pig_pointer.py
```

如果改动了打包逻辑，也请重新运行：

```powershell
.\build.ps1
```

## 代码风格

- 尽量保持单文件结构清晰，避免无关重构。
- UI 文案使用中文。
- 新增设置项时，需要考虑旧版 `settings.json` 的兼容读取。
- 涉及透明层、鼠标隐藏、托盘退出等行为时，优先保证异常退出后系统鼠标能恢复。
