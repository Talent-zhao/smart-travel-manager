# Tesseract OCR 安装指南

## 问题说明
身份证识别功能需要 Tesseract OCR 引擎。如果出现以下错误：
```
tesseract is not installed or it's not in your PATH
```
说明需要安装 Tesseract OCR。

## Windows 安装方法

### 方法1：使用安装程序（推荐）

1. **下载 Tesseract OCR**
   - 访问：https://github.com/UB-Mannheim/tesseract/wiki
   - 下载最新版本的 Windows 安装程序（例如：`tesseract-ocr-w64-setup-5.x.x.exe`）

2. **安装**
   - 运行下载的安装程序
   - 安装时**务必勾选**"Add to PATH"选项
   - 或者记住安装路径（默认通常是 `C:\Program Files\Tesseract-OCR`）

3. **配置环境变量（如果安装时未自动添加）**
   - 右键"此电脑" → "属性" → "高级系统设置" → "环境变量"
   - 在"系统变量"中找到 `Path`，点击"编辑"
   - 添加 Tesseract 安装路径（例如：`C:\Program Files\Tesseract-OCR`）
   - 点击"确定"保存

4. **验证安装**
   - 打开命令提示符（CMD）或 PowerShell
   - 运行：`tesseract --version`
   - 如果显示版本号，说明安装成功

### 方法2：使用 Chocolatey（如果已安装）

```powershell
choco install tesseract
```

### 方法3：使用 Scoop（如果已安装）

```powershell
scoop install tesseract
```

## Linux 安装方法

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

### CentOS/RHEL
```bash
sudo yum install tesseract
```

### 验证安装
```bash
tesseract --version
```

## macOS 安装方法

### 使用 Homebrew
```bash
brew install tesseract
```

### 验证安装
```bash
tesseract --version
```

## 安装中文语言包（可选，提高中文识别准确率）

### Windows
- 安装程序通常已包含中文语言包
- 如果没有，可以从 https://github.com/tesseract-ocr/tessdata 下载 `chi_sim.traineddata` 和 `chi_tra.traineddata`
- 放到 Tesseract 安装目录的 `tessdata` 文件夹中

### Linux
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr-chi-sim tesseract-ocr-chi-tra
```

### macOS
```bash
brew install tesseract-lang
```

## 验证 Python 环境

安装完成后，重启 Django 开发服务器，然后检查：

```python
import pytesseract
pytesseract.get_tesseract_version()
```

如果成功显示版本号，说明配置正确。

## 常见问题

### 1. 安装后仍然提示找不到 Tesseract
- **解决方法**：重启计算机，或重启 IDE/终端
- 检查环境变量 PATH 是否正确配置
- 在 Python 代码中手动指定路径：
  ```python
  import pytesseract
  pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
  ```

### 2. 识别准确率低
- 确保图片清晰、光线充足
- 确保身份证号码区域完整可见
- 尝试安装中文语言包

### 3. 权限问题
- 确保 Tesseract 安装目录有读取权限
- 确保临时文件目录有写入权限

## 测试安装

运行以下命令测试：
```bash
python -c "import pytesseract; print(pytesseract.get_tesseract_version())"
```

如果显示版本号，说明安装成功！

