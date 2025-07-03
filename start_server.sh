#!/bin/bash

# Arduino 烧录器启动脚本

# 设置默认参数
HOST="0.0.0.0"
PORT="5000"
PYTHON_CMD="python3"

# 检查 Python 是否可用
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "错误: Python3 未找到，请先安装 Python3"
    exit 1
fi

# 检查依赖是否安装
if ! $PYTHON_CMD -c "import flask" &> /dev/null; then
    echo "警告: Flask 未安装，正在安装依赖..."
    pip3 install -r requirements.txt
fi

# 检查 avrdude 是否可用
if ! command -v avrdude &> /dev/null; then
    echo "警告: avrdude 未找到，请安装 avrdude"
    echo "Ubuntu/Debian: sudo apt-get install avrdude"
fi

# 检查 gpio 命令是否可用
if ! command -v gpio &> /dev/null; then
    echo "警告: gpio 命令未找到，GPIO 控制可能无法工作"
fi

# 创建日志目录
mkdir -p logs

echo "启动 Arduino 烧录器服务..."
echo "服务地址: http://$HOST:$PORT"
echo "按 Ctrl+C 停止服务"
echo "=========================="

# 启动服务器
$PYTHON_CMD 基础Arduino上传.py --host $HOST --port $PORT
