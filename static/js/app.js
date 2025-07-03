// Arduino 烧录器前端应用
class ArduinoUploader {
    constructor() {
        this.socket = null;
        this.isOperating = false;
        this.autoScroll = true;

        this.initializeElements();
        this.bindEvents();
        this.initializeWebSocket();
        this.checkServerStatus();
        this.startStatusPolling();
    }

    initializeElements() {
        // 状态元素
        this.statusBadge = document.getElementById('status-badge');
        this.statusText = document.getElementById('status-text');
        this.progressBar = document.getElementById('progress-bar');
        
        // 表单元素
        this.uploadForm = document.getElementById('upload-form');
        this.hexFile = document.getElementById('hex-file');
        this.hexUrl = document.getElementById('hex-url');
        this.port = document.getElementById('port');
        this.part = document.getElementById('part');
        this.programmer = document.getElementById('programmer');
        this.baud = document.getElementById('baud');
        this.verbose = document.getElementById('verbose');
        
        // 按钮元素
        this.uploadBtn = document.getElementById('upload-btn');
        this.eraseBtn = document.getElementById('erase-btn');
        this.readFusesBtn = document.getElementById('read-fuses-btn');
        this.stopBtn = document.getElementById('stop-btn');
        this.clearLogBtn = document.getElementById('clear-log-btn');
        this.autoScrollBtn = document.getElementById('auto-scroll-btn');
        
        // 日志元素
        this.logContainer = document.getElementById('log-container');
    }

    bindEvents() {
        // 按钮事件
        this.uploadBtn.addEventListener('click', () => this.startUpload());
        this.eraseBtn.addEventListener('click', () => this.startErase());
        this.readFusesBtn.addEventListener('click', () => this.readFuses());
        this.stopBtn.addEventListener('click', () => this.stopOperation());
        this.clearLogBtn.addEventListener('click', () => this.clearLog());
        this.autoScrollBtn.addEventListener('click', () => this.toggleAutoScroll());
        
        // 文件选择事件
        this.hexFile.addEventListener('change', () => {
            if (this.hexFile.files.length > 0) {
                this.hexUrl.value = '';
            }
        });
        
        this.hexUrl.addEventListener('input', () => {
            if (this.hexUrl.value.trim()) {
                this.hexFile.value = '';
            }
        });
        
        // 拖拽上传
        this.setupDragAndDrop();
    }

    setupDragAndDrop() {
        const dropArea = this.hexFile.parentElement;
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, this.preventDefaults, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => dropArea.classList.add('dragover'), false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, () => dropArea.classList.remove('dragover'), false);
        });
        
        dropArea.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.hexFile.files = files;
                this.hexUrl.value = '';
            }
        });
    }

    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    initializeWebSocket() {
        // 初始化WebSocket连接
        this.socket = io();

        // 连接成功
        this.socket.on('connect', () => {
            console.log('WebSocket连接成功');
            this.appendLog('WebSocket连接已建立', 'info');
        });

        // 连接断开
        this.socket.on('disconnect', () => {
            console.log('WebSocket连接断开');
            this.appendLog('WebSocket连接已断开', 'warning');
        });

        // 接收日志消息
        this.socket.on('log_message', (data) => {
            this.appendLog(data.message);
        });

        // 操作完成通知
        this.socket.on('operation_complete', (data) => {
            this.operationComplete(data.success);
            if (data.message) {
                this.appendLog(data.message, data.success ? 'success' : 'error');
            }
        });

        // 状态更新
        this.socket.on('status_update', (data) => {
            if (data.is_running && !this.isOperating) {
                this.isOperating = true;
                this.updateStatus('操作进行中', 'uploading');
                this.setButtonsEnabled(false);
            }
        });

        // 连接确认
        this.socket.on('connected', (data) => {
            this.appendLog(data.message, 'info');
        });
    }

    async checkServerStatus() {
        try {
            const response = await fetch('/health');
            const data = await response.json();
            
            if (data.status === 'ok') {
                this.updateStatus('就绪', 'ready');
                this.appendLog('服务器连接正常，可以开始操作', 'info');
            }
        } catch (error) {
            this.updateStatus('服务器连接失败', 'error');
            this.appendLog('无法连接到服务器', 'error');
        }
    }

    startStatusPolling() {
        setInterval(async () => {
            if (!this.isOperating) {
                try {
                    const response = await fetch('/status');
                    const status = await response.json();
                    
                    if (status.is_running && !this.isOperating) {
                        this.isOperating = true;
                        this.updateStatus('操作进行中', 'uploading');
                        this.setButtonsEnabled(false);
                    } else if (!status.is_running && this.isOperating) {
                        this.isOperating = false;
                        this.setButtonsEnabled(true);
                    }
                } catch (error) {
                    console.error('Status polling error:', error);
                }
            }
        }, 2000);
    }

    updateStatus(message, type) {
        this.statusBadge.textContent = message;
        this.statusBadge.className = `badge me-2 status-${type}`;
        this.statusText.textContent = this.getStatusDescription(type);
    }

    getStatusDescription(type) {
        const descriptions = {
            'ready': '等待操作',
            'uploading': '正在执行操作...',
            'success': '操作成功完成',
            'error': '操作失败'
        };
        return descriptions[type] || '未知状态';
    }

    appendLog(message, type = 'info') {
        const logLine = document.createElement('div');
        logLine.className = `log-line log-${type}`;
        logLine.textContent = message;
        
        this.logContainer.appendChild(logLine);
        
        if (this.autoScroll) {
            this.logContainer.scrollTop = this.logContainer.scrollHeight;
        }
    }

    clearLog() {
        this.logContainer.innerHTML = '<div class="p-3 text-muted"><i class="bi bi-info-circle"></i> 日志已清空</div>';
    }

    toggleAutoScroll() {
        this.autoScroll = !this.autoScroll;
        this.autoScrollBtn.innerHTML = this.autoScroll 
            ? '<i class="bi bi-arrow-down"></i> 自动滚动' 
            : '<i class="bi bi-arrow-down-circle"></i> 手动滚动';
        this.autoScrollBtn.classList.toggle('btn-outline-secondary');
        this.autoScrollBtn.classList.toggle('btn-secondary');
    }

    setButtonsEnabled(enabled) {
        this.uploadBtn.disabled = !enabled;
        this.eraseBtn.disabled = !enabled;
        this.readFusesBtn.disabled = !enabled;
        this.stopBtn.disabled = enabled;
        
        if (!enabled) {
            this.uploadBtn.innerHTML = '<span class="spinner"></span> 上传中...';
        } else {
            this.uploadBtn.innerHTML = '<i class="bi bi-upload"></i> 上传程序';
        }
    }

    validateForm() {
        const hasFile = this.hexFile.files.length > 0;
        const hasUrl = this.hexUrl.value.trim() !== '';
        
        if (!hasFile && !hasUrl) {
            this.appendLog('错误: 请选择文件或输入URL', 'error');
            return false;
        }
        
        if (!this.port.value.trim()) {
            this.appendLog('错误: 请输入串口', 'error');
            return false;
        }
        
        return true;
    }

    createFormData(operationType = 'upload') {
        const formData = new FormData();
        
        // 基本参数
        formData.append('port', this.port.value);
        formData.append('part', this.part.value);
        formData.append('programmer', this.programmer.value);
        formData.append('baud', this.baud.value);
        
        if (this.verbose.checked) {
            formData.append('verbose', 'true');
        }
        
        // 根据操作类型设置参数
        switch (operationType) {
            case 'upload':
                if (this.hexFile.files.length > 0) {
                    formData.append('hex_file', this.hexFile.files[0]);
                } else if (this.hexUrl.value.trim()) {
                    formData.append('hex_url', this.hexUrl.value.trim());
                }
                break;
                
            case 'erase':
                formData.append('operation_only', 'true');
                formData.append('erase_chip', 'true');
                break;
                
            case 'read_fuses':
                formData.append('operation_only', 'true');
                formData.append('memory_operations', 'lfuse:r:-:h,hfuse:r:-:h,efuse:r:-:h');
                break;
        }
        
        return formData;
    }

    async startOperation(operationType) {
        if (this.isOperating) {
            this.appendLog('警告: 已有操作正在进行中', 'warning');
            return;
        }
        
        if (operationType === 'upload' && !this.validateForm()) {
            return;
        }
        
        this.clearLog();
        this.isOperating = true;
        this.setButtonsEnabled(false);
        this.updateStatus('操作进行中', 'uploading');
        
        const formData = this.createFormData(operationType);
        
        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            const result = await response.json();
            this.appendLog(result.message || '操作已开始', 'info');

        } catch (error) {
            this.appendLog(`操作失败: ${error.message}`, 'error');
            this.operationComplete(false);
        }
    }



    updateProgress(message) {
        // 简单的进度估算
        if (message.includes('Writing') || message.includes('写入')) {
            this.progressBar.style.width = '60%';
        } else if (message.includes('Reading') || message.includes('读取')) {
            this.progressBar.style.width = '80%';
        } else if (message.includes('Verifying') || message.includes('验证')) {
            this.progressBar.style.width = '90%';
        } else if (message.includes('成功') || message.includes('完成')) {
            this.progressBar.style.width = '100%';
        }
    }

    operationComplete(success) {
        this.isOperating = false;
        this.setButtonsEnabled(true);

        if (success) {
            this.updateStatus('操作完成', 'success');
            this.progressBar.style.width = '100%';
            setTimeout(() => {
                this.progressBar.style.width = '0%';
            }, 3000);
        } else {
            this.updateStatus('操作失败', 'error');
            this.progressBar.style.width = '0%';
        }
    }

    startUpload() {
        this.startOperation('upload');
    }

    startErase() {
        if (confirm('确定要执行全片擦除操作吗？这将删除Arduino上的所有程序。')) {
            this.startOperation('erase');
        }
    }

    readFuses() {
        this.startOperation('read_fuses');
    }

    async stopOperation() {
        try {
            await fetch('/stop', { method: 'POST' });
            this.appendLog('停止请求已发送', 'warning');
        } catch (error) {
            this.appendLog('停止请求失败', 'error');
        }
    }
}

// 初始化应用
document.addEventListener('DOMContentLoaded', () => {
    new ArduinoUploader();
});
