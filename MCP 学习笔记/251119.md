vscode中调试应该在虚拟环境中运行的python

### 第一步：安装必要的 VS Code 扩展

确保你已经安装了 Microsoft 官方的 **Python 扩展**。这是在 VS Code 中进行所有 Python 开发的基础。

### 第二步：选择正确的 Python 解释器（最关键的一步）

VS Code 需要知道它应该用哪个 `python` 可执行文件来运行和调试你的代码。

1. **打开命令面板**：
    - 快捷键：`Ctrl + Shift + P` (Windows/Linux) 或 `Cmd + Shift + P` (macOS)。
2. **搜索并选择命令**：
    - 在弹出的输入框中，输入 `Python: Select Interpreter` (通常打 `interpreter` 就能看到)。
    - 点击该命令。
3. **选择你的虚拟环境**：
    - VS Code 会弹出一个列表，列出它找到的所有 Python 解释器。
    - 它通常能自动检测到你项目文件夹中的 `.venv` 虚拟环境。它会显示为 `./.venv/bin/python` (macOS/Linux) 或 `.\.venv\Scripts\python.exe` (Windows)。
    - **选择这个带有 `.venv` 路径的解释器。** 它旁边通常会有一个星号 ⭐，表示推荐。
4. **确认选择**：
    - 选择后，观察 VS Code 窗口的右下角。它现在应该会显示你刚刚选择的虚拟环境的 Python 版本。这表明 VS Code 已经成功切换。

**如果 VS Code 没有自动找到怎么办？**

- 在解释器列表中，选择 `+ Enter interpreter path...`。
- 然后手动浏览到你的虚拟环境文件夹，选择里面的 Python 可执行文件：
    - **macOS/Linux**: `your-project-folder/.venv/bin/python`
    - **Windows**: `your-project-folder\.venv\Scripts\python.exe`

### 第三步：设置断点并开始调试

现在 VS Code 已经配置好了，调试过程就和普通文件一样了。

1. **打开你的 Python 文件**：例如 `main.py`。
2. **设置断点**：在你想要暂停代码执行的行号左侧，**单击鼠标**。一个红点会出现，这就是断点。
3. **启动调试器**：
    - **最简单的方式**：直接按 `F5` 键。
    - **或者**：点击左侧活动栏的 "运行和调试" 图标 (一个带 bug 的播放按钮)。
    - 然后点击顶部的绿色 "运行和调试" 按钮。
4. **选择调试配置**：
    - 第一次运行时，VS Code 会询问你如何调试。选择 **"Python File"**。

### 第四步：进行调试

一旦调试开始，你会看到：

- **代码执行在你的断点处暂停**，该行会被高亮。
- 顶部出现一个**调试工具栏**，包含继续（`F5`）、单步跳过（`F10`）、单步调试（`F11`）、跳出（`Shift+F11`）等按钮。
- 左侧的 "运行和调试" 视图会显示**变量的当前值**、**调用堆栈**等信息。