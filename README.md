# AI-Promot

AI实时提词器，准确率响应速度优于市面上许多付费提词

## 功能特性
- 🎤 实时语音识别
- 🖥️ 实时滚动提词
- 🎯 高精度语音转文本
- ⚡ 快速响应
- 🔄 持续优化更新

## 环境要求

- Python 3.10
- Conda（推荐）或 Miniconda

## 安装步骤

### 1. 安装 Conda
如果您还没有安装 Conda，请先安装：
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html)（推荐）
- 或 [Anaconda](https://www.anaconda.com/download)

### 2. 创建并激活 Conda 环境
```bash
# 创建名为 myenv 的 Python 3.10 环境
conda create -n myenv python=3.10

# 激活环境
conda activate myenv

### 3. 安装依赖
pip install -r requirements.txt

### 4. 运行应用
conda activate myenv
python funasr_tray_app.py
