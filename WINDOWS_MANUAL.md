# Document Sanitizer — Windows 安装与使用手册

## 目录

1. [系统要求](#1-系统要求)
2. [安装步骤](#2-安装步骤)
3. [启动程序](#3-启动程序)
4. [使用指南](#4-使用指南)
5. [常见问题](#5-常见问题)

---

## 1. 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10 / 11（64 位） |
| Python | 3.10 或更高版本 |
| 浏览器 | 任意现代浏览器（Chrome / Edge / Firefox） |
| 磁盘空间 | 约 200MB（含依赖） |

---

## 2. 安装步骤

### 2.1 安装 Python

1. 打开浏览器，访问 [https://www.python.org/downloads/](https://www.python.org/downloads/)
2. 下载 Windows 最新稳定版（3.10+）
3. 运行安装程序，**务必勾选 `Add Python to PATH`**，然后点击 `Install Now`

   > ⚠️ 如果漏掉这一步，命令行将无法识别 `python` 命令。

4. 安装完成后，按 `Win + R`，输入 `cmd`，打开命令提示符，输入：
   ```
   python --version
   ```
   应显示 `Python 3.10.x` 或更高版本。

### 2.2 下载项目

**方式一：使用 Git（推荐）**

```bash
# 安装 Git（如果尚未安装）：访问 https://git-scm.com/download/win
git clone https://github.com/YOUR_USERNAME/doc-sanitizer.git
cd doc-sanitizer
```

**方式二：下载 ZIP 包**

1. 访问项目 GitHub 页面
2. 点击绿色 `Code` 按钮 → `Download ZIP`
3. 解压到目标目录，例如 `C:\doc-sanitizer`
4. 打开命令提示符，切换到解压后的目录：
   ```
   cd C:\doc-sanitizer
   ```

### 2.3 安装依赖

在命令提示符中运行：

```bash
pip install -r requirements.txt
```

这将自动安装以下依赖：

| 包名 | 用途 |
|------|------|
| Flask | Web 服务框架 |
| python-docx | Word 文档处理 |
| PyMuPDF | PDF 文档处理 |
| reportlab | PDF 生成 |
| pytest | 测试框架 |

> 💡 如果下载缓慢，可使用清华镜像源：
> ```
> pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
> ```

---

## 3. 启动程序

### 3.1 启动 Flask 服务

在命令提示符中，进入项目目录后运行：

```bash
python app.py
```

成功后将看到类似输出：

```
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on http://127.0.0.1:5000
```

### 3.2 打开浏览器

在浏览器地址栏输入：

```
http://localhost:5000
```

即可看到程序界面。

### 3.3 停止服务

在命令提示符窗口按 `Ctrl + C` 即可停止服务。

### 3.4 创建桌面快捷启动（可选）

1. 在桌面右键 → `新建` → `快捷方式`
2. 位置填写：
   ```
   cmd /k "cd C:\doc-sanitizer && python app.py"
   ```
3. 命名为 `Document Sanitizer`
4. 双击快捷方式即可一键启动

---

## 4. 使用指南

### 4.1 界面概览

打开 `http://localhost:5000` 后，界面分为左右两个面板：

```
┌──────────────────────────────────────────────────────────┐
│               Document Sanitizer                         │
├────────────────────┬─────────────────────────────────────┤
│  敏感词管理面板     │      上传与处理面板                 │
│  ┌──────────────┐  │  ┌──────────────────────────────┐   │
│  │ 敏感词  替换   │  │  [拖拽文件到这里]              │   │
│  │              │  │  │  或 选择文件 (.docx/.txt/.pdf) │   │
│  │  [添加按钮]   │  │  │                              │   │
│  │              │  │  │  [处理文档]                  │   │
│  └──────────────┘  │  │                              │   │
│  [清空][导入][导出]│  │  [审计结果 / 下载链接]        │   │
└────────────────────┴─────────────────────────────────────┘
```

### 4.2 添加敏感词

1. 在左侧面板的 `敏感词` 输入框中输入需要替换的词（如 `中国移动`）
2. 在 `替换` 输入框中输入替换后的内容（如 `**运营商A**`）
3. 点击 `Add` 按钮

重复以上步骤添加更多敏感词。

### 4.3 编辑敏感词

直接在表格中修改对应输入框的内容，修改完成后按回车或点击表格外任意位置即可自动保存。

### 4.4 删除敏感词

点击对应行右侧的 `×` 按钮即可删除。

### 4.5 批量导入 / 导出

**导出**：点击 `Export` 按钮，将下载一个 `sensitive_words.json` 文件，格式如下：

```json
{
  "中国移动": "**运营商A**",
  "中国联通": "**运营商B**",
  "中国电信": "**运营商C**"
}
```

**导入**：点击 `Import` 按钮，选择 JSON 文件即可批量导入。

**清空**：点击 `Clear All` 按钮，确认后清除所有敏感词。

### 4.6 处理文档

1. 确保已配置至少一条敏感词
2. 在右侧面板中：
   - **拖拽上传**：将文件拖到虚线框内
   - **点击上传**：点击 `选择文件` 按钮选择 `.docx`、`.txt` 或 `.pdf` 文件
3. 点击 `Process Document` 按钮
4. 等待处理完成后：
   - **审计通过**：显示绿色 `✅ Audit passed: no sensitive words remaining.`
   - **审计未通过**：显示黄色警告，列出残留的敏感词及上下文
5. 点击 `Download Processed Document` 下载处理后的文档

### 4.7 Word 文档的修订模式

处理后的 `.docx` 文档在 Microsoft Word 中打开时：

- **原文敏感词**：显示为删除状态（带删除线）
- **替换后的文字**：显示为插入状态（黄色高亮）
- 在 Word 顶部 `审阅` 选项卡中，可以：
  - `接受所有修订` → 确认所有替换
  - `拒绝所有修订` → 恢复原文
  - `显示标记` → 查看修改痕迹

> ⚠️ 确保在 Word 中开启 `审阅` → `修订` 模式，才能正确看到所有替换结果。

### 4.8 审计下载

点击 `Download Audit Report` 可下载 JSON 格式的审计报告，包含审计结果、匹配次数和残留词上下文。

---

## 5. 常见问题

### Q1: 启动时报错 `ModuleNotFoundError`

```
ModuleNotFoundError: No module named 'flask'
```

**原因**：依赖未安装。

**解决**：运行 `pip install -r requirements.txt`。

### Q2: `python` 命令找不到

**原因**：Python 未添加到系统 PATH。

**解决**：重新运行 Python 安装程序，勾选 `Add Python to PATH`。或者在命令行中使用完整路径：
```
C:\Users\你的用户名\AppData\Local\Programs\Python\Python313\python.exe app.py
```

### Q3: 处理 PDF 后格式丢失

**原因**：PDF 是固定格式文档，重建时仅保留文本内容，不保留原始排版、字体、图片等复杂格式。

**建议**：对于需要保留格式的 PDF，建议先转为 Word 文档再处理。

### Q4: Word 打开后看不到替换效果

**原因**：修订显示被设置为 `无标记`。

**解决**：在 Word 中点击顶部菜单 `审阅` → 在 `跟踪更改` 区域将显示模式改为 `所有标记`，即可看到所有替换痕迹。

### Q5: 如何修改服务器端口？

编辑 `app.py` 文件最后一行：

```python
app.run(debug=True, port=5000)  # 将 5000 改为你需要的端口
```

### Q6: 上传文件大小限制

当前限制为 **50MB**。如需修改，编辑 `app.py` 中的以下行：

```python
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
```

### Q7: 敏感词数据存在哪里？

数据存储在项目目录下的 `sensitive_words.db` SQLite 数据库文件中。可通过导出功能备份，或复制该文件到其他机器使用。

---

## 技术支持

如有问题，请在 GitHub 项目页面提交 [Issue](https://github.com/YOUR_USERNAME/doc-sanitizer/issues)。
