# 猪猪指针

一个 Windows 桌面小挂件：把一只会动的小猪通过绳子“拴”在鼠标尾巴上。

软件使用透明置顶窗口绘制小猪和绳子，透明区域不会挡住鼠标点击。控制面板里可以调节小猪大小、绳子长度、重量感、动画触发概率、动画播放速度、触发间隔和鼠标绑定点偏移，让它更像一个有物理惯性的小桌宠。

## 功能

- 透明置顶桌面层
- 鼠标穿透，不影响点击
- 启动 / 关闭
- 后台运行到 Windows 系统托盘
- 可滚动设置面板
- 预览小窗口
- 调节 GIF 大小
- 调节绳子长度
- 调节重量感 / 惯性
- 调节动画触发概率
- 调节动画播放速度
- 调节动画触发间隔
- 调节鼠标绑定点横向 / 纵向偏移
- GIF 首尾不对齐时，使用“正放 + 倒放回首帧”避免跳帧
- 自动擦除原 GIF 上方直绳，改用程序绘制的物理绳子

## 运行环境

- Windows
- Python 3.10+
- Pillow
- NumPy
- pystray

## 从源码运行

```powershell
pip install -r requirements.txt
python pig_pointer.py
```

也可以双击：

```text
start_pig_pointer.bat
```

## 使用打包版

已打包的可执行文件在：

```text
dist\PigPointer.exe
```

双击即可运行。

## 自行打包

安装打包依赖：

```powershell
pip install -r requirements-dev.txt
```

然后运行：

```powershell
.\build.ps1
```

打包完成后会生成：

```text
dist\PigPointer.exe
```

## 项目文件

- `pig_pointer.py`：主程序
- `pig_pointer.gif`：小猪动画
- `pig_pointer.ico`：软件图标
- `start_pig_pointer.bat`：源码运行启动脚本
- `build.ps1`：PyInstaller 打包脚本
- `dist/PigPointer.exe`：已打包的 Windows 可执行文件

## 说明

这是一个 Windows 桌面小工具。它使用 Windows layered window 实现逐像素透明和鼠标穿透，因此主要面向 Windows 使用。

关闭面板时如果勾选“关闭面板时继续后台工作”，小猪会继续跟随鼠标，软件图标会留在 Windows 右下角系统托盘。左键点击托盘图标可以恢复面板，右键可以打开菜单、启动/关闭小猪或退出软件。
