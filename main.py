import subprocess
import time
import argparse
import os
import tempfile
import logging
from datetime import datetime
from flask import Flask, request, Response, jsonify, render_template, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import threading
import queue
import requests
from werkzeug.utils import secure_filename
import json

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # 启用CORS支持
socketio = SocketIO(app, cors_allowed_origins="*")  # 启用WebSocket支持

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('arduino_uploader.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 创建一个队列用于存储输出消息
output_queue = queue.Queue()

# 全局变量用于跟踪操作状态
operation_status = {
    'is_running': False,
    'start_time': None,
    'operation_type': None
}

def log_message(message):
    """将消息添加到队列并通过WebSocket发送"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    print(formatted_message)
    logger.info(message)

    # 通过WebSocket发送日志
    socketio.emit('log_message', {
        'message': formatted_message,
        'timestamp': timestamp,
        'raw_message': message
    })

    # 保留队列用于其他用途
    output_queue.put(formatted_message)

def control_arduino_reset(reset=True):
    """
    通过GPIO控制Arduino的复位
    reset=True: 使Arduino进入复位状态 (GPIO 7 设为0)
    reset=False: 使Arduino退出复位状态 (GPIO 7 设为1)
    """
    state = "0" if reset else "1"
    cmd = ["gpio", "write", "7", state]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        action = "进入" if reset else "退出"
        log_message(f"Arduino {action}复位状态")
        return True
    except subprocess.CalledProcessError as e:
        log_message(f"GPIO控制失败: {e.stderr}")
        return False

def run_avrdude_command(cmd):
    """
    执行avrdude命令并实时输出结果
    """
    log_message(f"执行命令: {' '.join(cmd)}")
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    
    # 实时读取输出并添加到队列
    for line in process.stdout:
        log_message(line.strip())
    
    process.wait()
    return process.returncode == 0

def upload_using_avrdude(hex_file, port='/dev/ttyS7', options=None):
    """
    使用avrdude上传hex文件到Arduino，支持额外选项
    
    options: 字典，包含avrdude的额外选项
    """
    if options is None:
        options = {}
    
    # 基本命令
    cmd = [
        'avrdude',
        '-p', options.get('part', 'atmega328p'),
        '-c', options.get('programmer', 'arduino'),
        '-P', port,
        '-b', options.get('baud', '115200'),
    ]
    
    # 添加可选参数
    if options.get('disable_auto_erase', False):
        cmd.append('-D')
    
    if options.get('disable_verify', False):
        cmd.append('-V')
    
    if options.get('verbose', False):
        cmd.append('-v')
    
    if options.get('extra_verbose', False):
        cmd.extend(['-v', '-v'])
    
    if options.get('quiet', False):
        cmd.append('-q')
    
    if options.get('force', False):
        cmd.append('-F')
    
    if options.get('bitclock'):
        cmd.extend(['-B', options.get('bitclock')])
    
    if options.get('config_file'):
        cmd.extend(['-C', options.get('config_file')])
    
    # 添加内存操作
    if options.get('erase_chip', False):
        cmd.append('-e')
    
    # 添加扩展参数
    for ext_param in options.get('extended_params', []):
        cmd.extend(['-x', ext_param])
    
    # 添加内存操作
    memory_ops = []
    
    # 如果提供了hex文件，添加写入操作
    if hex_file:
        memory_ops.append(f'flash:w:{hex_file}:i')
    
    # 添加其他内存操作
    for op in options.get('memory_operations', []):
        memory_ops.append(op)
    
    # 将所有内存操作添加到命令中
    for op in memory_ops:
        cmd.extend(['-U', op])
    
    return run_avrdude_command(cmd)

def perform_arduino_operation(hex_file=None, port='/dev/ttyS7', options=None):
    """
    完整的Arduino操作流程，包括复位控制
    """
    global operation_status

    try:
        operation_status['is_running'] = True
        operation_status['start_time'] = datetime.now()
        operation_status['operation_type'] = "上传程序" if hex_file else "执行操作"

        if hex_file and not os.path.exists(hex_file):
            log_message(f"错误: 文件 {hex_file} 不存在")
            return False

        operation_type = "上传程序" if hex_file else "执行操作"
        log_message(f"开始{operation_type}到Arduino...")

        # 1. 使Arduino进入复位状态
        if not control_arduino_reset(reset=True):
            log_message("错误: 无法控制Arduino复位")
            return False

        # 2. 等待一小段时间确保复位生效
        time.sleep(0.5)

        # 3. 使Arduino退出复位状态，进入bootloader
        if not control_arduino_reset(reset=False):
            log_message("错误: 无法退出Arduino复位状态")
            return False

        # 4. 给bootloader一点时间初始化
        time.sleep(0.5)

        # 5. 执行avrdude操作
        success = upload_using_avrdude(hex_file, port, options)

        # 6. 操作后再次复位Arduino使程序开始运行
        if success:
            control_arduino_reset(reset=True)
            time.sleep(0.1)
            control_arduino_reset(reset=False)
            log_message("Arduino已重启，程序开始运行")
            log_message("操作成功完成!")
        else:
            log_message("操作失败!")

        # 发送操作完成通知
        socketio.emit('operation_complete', {
            'success': success,
            'message': '操作成功完成!' if success else '操作失败!'
        })

        return success

    except Exception as e:
        log_message(f"操作过程中发生异常: {str(e)}")
        logger.exception("Arduino operation failed with exception")

        # 发送操作失败通知
        socketio.emit('operation_complete', {
            'success': False,
            'message': f'操作异常: {str(e)}'
        })

        return False

    finally:
        operation_status['is_running'] = False
        # 清理临时文件
        if hex_file and hex_file.startswith(tempfile.gettempdir()):
            try:
                os.remove(hex_file)
                log_message(f"已清理临时文件: {hex_file}")
            except Exception as e:
                log_message(f"清理临时文件失败: {str(e)}")

def download_hex_file(url, save_path=None):
    """从URL下载HEX文件"""
    try:
        log_message(f"正在从 {url} 下载HEX文件...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        if save_path is None:
            # 创建临时文件
            fd, save_path = tempfile.mkstemp(suffix='.hex')
            os.close(fd)
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        log_message(f"HEX文件已下载到 {save_path}")
        return save_path
    except Exception as e:
        log_message(f"下载HEX文件失败: {str(e)}")
        return None

def parse_avrdude_options(form_data):
    """从请求表单数据解析avrdude选项"""
    options = {}
    
    # 基本选项
    if 'part' in form_data:
        options['part'] = form_data['part']
    
    if 'programmer' in form_data:
        options['programmer'] = form_data['programmer']
    
    if 'baud' in form_data:
        options['baud'] = form_data['baud']
    
    if 'bitclock' in form_data:
        options['bitclock'] = form_data['bitclock']
    
    if 'config_file' in form_data:
        options['config_file'] = form_data['config_file']
    
    # 布尔选项
    boolean_options = [
        'disable_auto_erase', 'disable_verify', 'verbose', 'extra_verbose', 
        'quiet', 'force', 'erase_chip'
    ]
    
    for option in boolean_options:
        if option in form_data:
            options[option] = form_data[option].lower() in ['true', '1', 'yes', 'y']
    
    # 扩展参数
    if 'extended_params' in form_data:
        if isinstance(form_data['extended_params'], list):
            options['extended_params'] = form_data['extended_params']
        else:
            # 假设是逗号分隔的字符串
            options['extended_params'] = [p.strip() for p in form_data['extended_params'].split(',') if p.strip()]
    
    # 内存操作
    if 'memory_operations' in form_data:
        if isinstance(form_data['memory_operations'], list):
            options['memory_operations'] = form_data['memory_operations']
        else:
            # 假设是逗号分隔的字符串
            options['memory_operations'] = [op.strip() for op in form_data['memory_operations'].split(',') if op.strip()]
    
    return options

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_endpoint():
    """处理上传请求的端点"""
    try:
        # 检查是否有操作正在进行
        if operation_status['is_running']:
            return jsonify({"error": "Another operation is already in progress"}), 409

        # 清空之前的输出队列
        while not output_queue.empty():
            output_queue.get()

        hex_file_path = None
        port = request.form.get('port', '/dev/ttyS7')

        # 解析avrdude选项
        options = parse_avrdude_options(request.form)

        # 检查是否是纯操作模式（不上传HEX文件）
        operation_only = request.form.get('operation_only', 'false').lower() in ['true', '1', 'yes', 'y']

        if not operation_only:
            # 检查是否提供了文件URL
            if 'hex_url' in request.form:
                url = request.form['hex_url']
                hex_file_path = download_hex_file(url)
                if not hex_file_path:
                    return jsonify({"error": "Failed to download HEX file"}), 400

            # 检查是否直接上传了文件
            elif 'hex_file' in request.files:
                file = request.files['hex_file']
                if file.filename == '':
                    return jsonify({"error": "No file selected"}), 400

                # 验证文件类型
                if not file.filename.lower().endswith(('.hex', '.bin')):
                    return jsonify({"error": "Invalid file type. Only .hex and .bin files are allowed"}), 400

                # 保存上传的文件
                filename = secure_filename(file.filename)
                hex_file_path = os.path.join(tempfile.gettempdir(), f"{int(time.time())}_{filename}")
                file.save(hex_file_path)
                log_message(f"已接收上传的文件: {filename}")

            elif not options.get('memory_operations'):
                return jsonify({"error": "No HEX file provided. Please provide either 'hex_url', 'hex_file', or set 'operation_only=true' with memory_operations"}), 400

        # 在新线程中执行上传操作
        threading.Thread(target=perform_arduino_operation,
                        args=(hex_file_path, port, options),
                        name="arduino_operation").start()

        # 返回操作开始确认
        return jsonify({
            "status": "started",
            "message": "操作已开始，请查看实时日志"
        })

    except Exception as e:
        logger.exception("Upload endpoint error")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500



@app.route('/status', methods=['GET'])
def get_status():
    """获取当前操作状态"""
    return jsonify({
        "is_running": operation_status['is_running'],
        "start_time": operation_status['start_time'].isoformat() if operation_status['start_time'] else None,
        "operation_type": operation_status['operation_type'],
        "queue_size": output_queue.qsize()
    })

@app.route('/stop', methods=['POST'])
def stop_operation():
    """停止当前操作"""
    # 这里可以添加停止操作的逻辑
    # 由于avrdude操作通常很快，这个功能主要用于UI反馈
    return jsonify({"message": "Stop request received"})

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })

@app.route('/capabilities', methods=['GET'])
def capabilities():
    """返回支持的功能和选项"""
    return jsonify({
        "supported_options": {
            "basic": ["part", "programmer", "port", "baud", "bitclock", "config_file"],
            "boolean": ["disable_auto_erase", "disable_verify", "verbose", "extra_verbose",
                       "quiet", "force", "erase_chip", "operation_only"],
            "advanced": ["extended_params", "memory_operations"]
        },
        "examples": {
            "upload_hex": "POST /upload with hex_file or hex_url",
            "erase_chip": "POST /upload with operation_only=true&erase_chip=true",
            "read_fuses": "POST /upload with operation_only=true&memory_operations=lfuse:r:-:h,hfuse:r:-:h,efuse:r:-:h",
            "write_fuses": "POST /upload with operation_only=true&memory_operations=lfuse:w:0xFF:m,hfuse:w:0xDE:m",
        },
        "supported_file_types": [".hex", ".bin"],
        "default_port": "/dev/ttyS7"
    })

@app.route('/logs', methods=['GET'])
def get_logs():
    """获取日志文件内容"""
    try:
        with open('arduino_uploader.log', 'r', encoding='utf-8') as f:
            logs = f.readlines()
        # 返回最后100行日志
        return jsonify({"logs": logs[-100:]})
    except FileNotFoundError:
        return jsonify({"logs": []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# WebSocket 事件处理
@socketio.on('connect')
def handle_connect():
    """客户端连接事件"""
    print('客户端已连接')
    emit('connected', {'message': '已连接到Arduino烧录器'})

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开连接事件"""
    print('客户端已断开连接')

@socketio.on('request_status')
def handle_status_request():
    """客户端请求状态"""
    emit('status_update', {
        'is_running': operation_status['is_running'],
        'start_time': operation_status['start_time'].isoformat() if operation_status['start_time'] else None,
        'operation_type': operation_status['operation_type']
    })

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='上传程序到Arduino的HTTP服务')
    parser.add_argument('--port', type=int, default=5000, help='HTTP服务器端口 (默认: 5000)')
    parser.add_argument('--host', default='0.0.0.0', help='HTTP服务器主机 (默认: 0.0.0.0)')
    
    args = parser.parse_args()
    
    log_message(f"启动WebSocket服务器在 {args.host}:{args.port}")
    socketio.run(app, host=args.host, port=args.port, debug=False)
