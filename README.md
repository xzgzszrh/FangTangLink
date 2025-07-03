# Arduino 程序烧录器

一个基于 Web 的 Arduino 程序烧录系统，支持通过浏览器或 HTTP API 进行程序上传、全片擦除等操作，并提供实时日志流式输出。

## 功能特性

- 🚀 **Web 界面**: 现代化的响应式 Web 界面
- 📁 **文件上传**: 支持拖拽上传 HEX/BIN 文件
- 🌐 **URL 下载**: 支持从 URL 下载固件文件
- 📡 **实时日志**: WebSocket实时输出操作日志
- ⚙️ **高级配置**: 支持 avrdude 的各种参数配置
- 🔧 **多种操作**: 程序烧录、全片擦除、熔丝位读取等
- 🎛️ **GPIO 控制**: 自动控制 Arduino 复位
- 📊 **状态监控**: 实时显示操作状态和进度

## 系统要求

- Python 3.7+
- Flask 2.3+
- avrdude (Arduino 烧录工具)
- gpio 命令 (用于控制 Arduino 复位)
- RK3566 香橙派或类似的 Linux 系统

## 安装和配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 安装系统依赖

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install avrdude

# 确保 gpio 命令可用 (通常在 WiringPi 包中)
# 对于香橙派，可能需要安装特定的 GPIO 库
```

### 3. 配置权限

确保运行用户有权限访问串口和 GPIO：

```bash
# 添加用户到相关组
sudo usermod -a -G dialout $USER
sudo usermod -a -G gpio $USER

# 重新登录以使组权限生效
```

## 使用方法

### 启动服务器

```bash
python 基础Arduino上传.py --host 0.0.0.0 --port 5000
```

参数说明：
- `--host`: 服务器监听地址 (默认: 0.0.0.0)
- `--port`: 服务器端口 (默认: 5000)

### Web 界面

打开浏览器访问 `http://localhost:5000`

#### 主要功能：

1. **文件上传**
   - 点击选择文件或拖拽文件到上传区域
   - 支持 .hex 和 .bin 文件格式
   - 或者输入文件 URL 进行下载

2. **配置选项**
   - 串口设置 (默认: /dev/ttyS7)
   - 芯片型号选择 (ATmega328P, ATmega168 等)
   - 编程器类型 (Arduino, USBasp 等)
   - 波特率设置
   - 详细输出选项

3. **操作按钮**
   - **上传程序**: 烧录选定的固件文件
   - **全片擦除**: 清除 Arduino 上的所有程序
   - **读取熔丝位**: 读取当前的熔丝位设置
   - **停止操作**: 中断当前操作

4. **实时日志**
   - 显示操作过程的详细日志
   - 支持自动滚动
   - 可清空日志内容

### API 使用

详细的 API 文档请参考 [API_Documentation.md](API_Documentation.md)

#### 快速示例

```bash
# 上传 HEX 文件
curl -X POST http://localhost:5000/upload \
  -F "hex_file=@firmware.hex" \
  -F "port=/dev/ttyS7"

# 全片擦除
curl -X POST http://localhost:5000/upload \
  -F "operation_only=true" \
  -F "erase_chip=true"

# 检查服务状态
curl http://localhost:5000/health
```

## 项目结构

```
FangTangLink/
├── 基础Arduino上传.py          # 主服务器文件
├── templates/
│   └── index.html              # Web 界面模板
├── static/
│   ├── css/
│   │   └── style.css          # 样式文件
│   └── js/
│       └── app.js             # 前端 JavaScript
├── requirements.txt            # Python 依赖
├── README.md                  # 项目说明
├── API_Documentation.md       # API 文档
└── arduino_uploader.log       # 日志文件 (运行时生成)
```

## 配置说明

### 默认配置

- **串口**: `/dev/ttyS7`
- **芯片**: `atmega328p`
- **编程器**: `arduino`
- **波特率**: `115200`
- **GPIO 复位引脚**: `7`

### 自定义配置

可以通过 Web 界面或 API 参数修改这些设置。

## 故障排除

### 常见问题

1. **串口权限问题**
   ```bash
   sudo chmod 666 /dev/ttyS7
   # 或添加用户到 dialout 组
   sudo usermod -a -G dialout $USER
   ```

2. **GPIO 控制失败**
   ```bash
   # 检查 gpio 命令是否可用
   which gpio

   # 测试 GPIO 控制
   gpio write 7 0
   gpio write 7 1
   ```

3. **avrdude 找不到设备**
   - 检查 Arduino 连接
   - 确认串口路径正确
   - 尝试不同的波特率

4. **Web 界面无法访问**
   - 检查防火墙设置
   - 确认服务器正在运行
   - 检查端口是否被占用

### 日志查看

```bash
# 查看实时日志
tail -f arduino_uploader.log

# 查看最近的错误
grep ERROR arduino_uploader.log
```