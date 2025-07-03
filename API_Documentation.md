# Arduino 烧录器 API 文档

## 概述

Arduino 烧录器是一个基于 Flask 和 WebSocket 的 Web 服务，允许通过 HTTP API 对 Arduino 设备进行程序烧录、全片擦除等操作。使用 WebSocket 提供实时日志输出，便于监控操作进程。

**服务地址**: `http://localhost:5000` (默认)
**WebSocket地址**: `ws://localhost:5000/socket.io/` (自动)

## 认证

当前版本不需要认证。

## 通用响应格式

### 成功响应
```json
{
    "status": "success",
    "data": {...}
}
```

### 错误响应
```json
{
    "error": "错误描述信息"
}
```

## API 端点

### 1. 主页面

**GET** `/`

返回 Web 界面主页。

**响应**: HTML 页面

---

### 2. 健康检查

**GET** `/health`

检查服务器状态。

**响应**:
```json
{
    "status": "ok",
    "timestamp": "2024-01-01T12:00:00",
    "version": "1.0.0"
}
```

---

### 3. 获取服务能力

**GET** `/capabilities`

获取服务器支持的功能和选项。

**响应**:
```json
{
    "supported_options": {
        "basic": ["part", "programmer", "port", "baud", "bitclock", "config_file"],
        "boolean": ["disable_auto_erase", "disable_verify", "verbose", "extra_verbose", "quiet", "force", "erase_chip", "operation_only"],
        "advanced": ["extended_params", "memory_operations"]
    },
    "examples": {
        "upload_hex": "POST /upload with hex_file or hex_url",
        "erase_chip": "POST /upload with operation_only=true&erase_chip=true",
        "read_fuses": "POST /upload with operation_only=true&memory_operations=lfuse:r:-:h,hfuse:r:-:h,efuse:r:-:h",
        "write_fuses": "POST /upload with operation_only=true&memory_operations=lfuse:w:0xFF:m,hfuse:w:0xDE:m"
    },
    "supported_file_types": [".hex", ".bin"],
    "default_port": "/dev/ttyS7"
}
```

---

### 4. 获取操作状态

**GET** `/status`

获取当前操作状态。

**响应**:
```json
{
    "is_running": false,
    "start_time": "2024-01-01T12:00:00",
    "operation_type": "上传程序",
    "queue_size": 0
}
```

---

### 5. 上传和操作

**POST** `/upload`

执行 Arduino 烧录操作。支持文件上传、URL 下载和各种 avrdude 操作。

**Content-Type**: `multipart/form-data`

**参数**:

#### 基本参数
- `port` (string, 可选): 串口路径，默认 `/dev/ttyS7`
- `part` (string, 可选): 芯片型号，默认 `atmega328p`
- `programmer` (string, 可选): 编程器类型，默认 `arduino`
- `baud` (string, 可选): 波特率，默认 `115200`

#### 文件参数 (三选一)
- `hex_file` (file): 上传的 HEX/BIN 文件
- `hex_url` (string): HEX 文件的 URL
- `operation_only` (boolean): 设为 true 时不上传文件，仅执行操作

#### 操作选项
- `erase_chip` (boolean): 全片擦除
- `disable_verify` (boolean): 禁用验证
- `verbose` (boolean): 详细输出
- `extra_verbose` (boolean): 超详细输出
- `quiet` (boolean): 静默模式
- `force` (boolean): 强制执行
- `disable_auto_erase` (boolean): 禁用自动擦除

#### 高级参数
- `bitclock` (string): 位时钟设置
- `config_file` (string): 配置文件路径
- `extended_params` (array): 扩展参数列表
- `memory_operations` (array): 内存操作列表

**响应**:
```json
{
    "status": "started",
    "message": "操作已开始，请查看实时日志"
}
```

**实时日志**: 通过 WebSocket 发送，详见 WebSocket 事件部分

**示例**:

1. **上传 HEX 文件**:
```bash
curl -X POST http://localhost:5000/upload \
  -F "hex_file=@firmware.hex" \
  -F "port=/dev/ttyS7" \
  -F "verbose=true"
```

2. **从 URL 下载并烧录**:
```bash
curl -X POST http://localhost:5000/upload \
  -F "hex_url=https://example.com/firmware.hex" \
  -F "part=atmega328p"
```

3. **全片擦除**:
```bash
curl -X POST http://localhost:5000/upload \
  -F "operation_only=true" \
  -F "erase_chip=true"
```

4. **读取熔丝位**:
```bash
curl -X POST http://localhost:5000/upload \
  -F "operation_only=true" \
  -F "memory_operations=lfuse:r:-:h,hfuse:r:-:h,efuse:r:-:h"
```

---

### 6. 停止操作

**POST** `/stop`

请求停止当前操作。

**响应**:
```json
{
    "message": "Stop request received"
}
```

---

### 7. 获取日志

**GET** `/logs`

获取服务器日志文件内容（最后100行）。

**响应**:
```json
{
    "logs": [
        "[2024-01-01 12:00:00] 操作开始...",
        "[2024-01-01 12:00:01] 连接到设备..."
    ]
}
```

## WebSocket 事件

### 客户端事件

#### connect
客户端连接到服务器时触发。

#### disconnect
客户端断开连接时触发。

#### request_status
请求当前操作状态。

### 服务器事件

#### connected
```json
{
    "message": "已连接到Arduino烧录器"
}
```

#### log_message
实时日志消息。
```json
{
    "message": "[2024-01-01 12:00:00] 开始上传程序到Arduino...",
    "timestamp": "2024-01-01 12:00:00",
    "raw_message": "开始上传程序到Arduino..."
}
```

#### operation_complete
操作完成通知。
```json
{
    "success": true,
    "message": "操作成功完成!"
}
```

#### status_update
状态更新通知。
```json
{
    "is_running": false,
    "start_time": "2024-01-01T12:00:00",
    "operation_type": "上传程序"
}
```

## 错误代码

- `400 Bad Request`: 请求参数错误
- `409 Conflict`: 已有操作正在进行
- `500 Internal Server Error`: 服务器内部错误

## 使用示例

### JavaScript (前端)

```javascript
// 初始化WebSocket连接
const socket = io();

// 监听日志消息
socket.on('log_message', (data) => {
    console.log('日志:', data.message);
});

// 监听操作完成
socket.on('operation_complete', (data) => {
    console.log('操作完成:', data.success ? '成功' : '失败');
    console.log('消息:', data.message);
});

// 上传文件
const formData = new FormData();
formData.append('hex_file', fileInput.files[0]);
formData.append('port', '/dev/ttyS7');
formData.append('verbose', 'true');

fetch('/upload', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => {
    console.log('上传开始:', data.message);
});
```

### Python 客户端

```python
import requests

# 上传文件
with open('firmware.hex', 'rb') as f:
    files = {'hex_file': f}
    data = {
        'port': '/dev/ttyS7',
        'verbose': 'true'
    }
    
    response = requests.post('http://localhost:5000/upload', 
                           files=files, data=data, stream=True)
    
    for line in response.iter_lines():
        if line:
            print(line.decode('utf-8'))
```

### cURL 示例

```bash
# 检查服务状态
curl http://localhost:5000/health

# 获取服务能力
curl http://localhost:5000/capabilities

# 上传并烧录
curl -X POST http://localhost:5000/upload \
  -F "hex_file=@firmware.hex" \
  -F "port=/dev/ttyS7" \
  -F "part=atmega328p" \
  -F "programmer=arduino" \
  -F "baud=115200" \
  -F "verbose=true"

# 全片擦除
curl -X POST http://localhost:5000/upload \
  -F "operation_only=true" \
  -F "erase_chip=true" \
  -F "port=/dev/ttyS7"
```

## 注意事项

1. **文件类型**: 仅支持 `.hex` 和 `.bin` 文件
2. **并发限制**: 同时只能执行一个操作
3. **文件清理**: 临时文件会在操作完成后自动清理
4. **日志记录**: 所有操作都会记录到 `arduino_uploader.log` 文件
5. **GPIO 控制**: 需要确保有权限控制 GPIO 7 用于 Arduino 复位

## 故障排除

### 常见错误

1. **"Another operation is already in progress"**
   - 等待当前操作完成或调用 `/stop` 端点

2. **"GPIO控制失败"**
   - 检查是否有 GPIO 访问权限
   - 确认 `gpio` 命令可用

3. **"avrdude: stk500_recv(): programmer is not responding"**
   - 检查串口连接
   - 确认 Arduino 处于正确状态
   - 尝试不同的波特率

4. **文件上传失败**
   - 检查文件格式是否正确
   - 确认文件大小不超过限制
