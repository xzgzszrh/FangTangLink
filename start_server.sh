#!/bin/bash

# Arduino 烧录器启动脚本

# 设置默认参数
HOST="0.0.0.0"
PORT="5000"

# 激活conda环境
echo "激活conda环境..."
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate opencv

# 检查依赖是否安装
if ! python -c "import flask" &> /dev/null; then
    echo "警告: Flask 未安装，正在安装依赖..."
    conda install flask flask-cors requests -y
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
python 基础Arduino上传.py --host $HOST --port $PORT

