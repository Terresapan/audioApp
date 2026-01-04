/**
 * 爸爸的翻译器 - Frontend JavaScript
 * Handles WebSocket connection and translation display
 */

let socket = null;
let isMuted = false;
let audioQueue = [];
let isPlaying = false;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    connect();
});

// WebSocket Connection
function connect() {
    updateConnectionStatus('connecting');
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/browser`;
    
    socket = new WebSocket(wsUrl);
    
    socket.onopen = () => {
        console.log('WebSocket connected');
        updateConnectionStatus('connected');
        reconnectAttempts = 0;
        updateStatus('已连接 - 等待音频');
    };
    
    socket.onmessage = (event) => {
        if (typeof event.data === 'string') {
            // JSON message (translation or status)
            const msg = JSON.parse(event.data);
            handleMessage(msg);
        } else {
            // Binary data (audio)
            handleAudio(event.data);
        }
    };
    
    socket.onclose = () => {
        console.log('WebSocket closed');
        updateConnectionStatus('disconnected');
        attemptReconnect();
    };
    
    socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        updateConnectionStatus('disconnected');
    };
}

function attemptReconnect() {
    if (reconnectAttempts < maxReconnectAttempts) {
        reconnectAttempts++;
        updateStatus(`正在重连... (${reconnectAttempts}/${maxReconnectAttempts})`);
        setTimeout(connect, 2000);
    } else {
        updateStatus('连接失败，请刷新页面重试');
    }
}

// Volume Control
function updateVolume(value) {
    document.getElementById('volumeValue').textContent = value + 'x';
    // Send volume update to server (which broadcasts to audio_bridge)
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'volume', value: parseFloat(value) }));
    }
}

// Message Handlers
function handleMessage(msg) {
    switch (msg.type) {
        case 'translation':
            addTranslation(msg.original, msg.translation);
            break;
        case 'status':
            updateStatus(msg.message);
            break;
        case 'pong':
            // Heartbeat response
            break;
    }
}

function handleAudio(audioBlob) {
    // Audio is now handled by Python receiver, not browser
    // This function kept for compatibility but we don't play in browser
    console.log("Audio received (handled by Python)");
}

// UI Updates
function addTranslation(original, translation) {
    const container = document.getElementById('translations');
    
    // Remove placeholder if present
    const placeholder = container.querySelector('.placeholder');
    if (placeholder) {
        placeholder.remove();
    }
    
    // Create translation card
    const card = document.createElement('div');
    card.className = 'translation-card';
    card.innerHTML = `
        <div class="translation-chinese">${escapeHtml(translation)}</div>
        <div class="translation-english">${escapeHtml(original)}</div>
    `;
    
    // Add to top
    container.insertBefore(card, container.firstChild);
    
    // Limit to 50 translations
    while (container.children.length > 50) {
        container.removeChild(container.lastChild);
    }
}

function updateStatus(message) {
    document.getElementById('status').textContent = message;
}

function updateConnectionStatus(status) {
    const dot = document.getElementById('connectionDot');
    const text = document.getElementById('connectionText');
    
    dot.className = 'dot ' + status;
    
    switch (status) {
        case 'connected':
            text.textContent = '已连接';
            break;
        case 'connecting':
            text.textContent = '连接中...';
            break;
        case 'disconnected':
            text.textContent = '未连接';
            break;
    }
}

// Controls
function toggleMute() {
    isMuted = !isMuted;
    const btn = document.getElementById('muteBtn');
    
    if (isMuted) {
        btn.textContent = '🔇 声音关';
        btn.classList.add('muted');
        audioQueue = []; // Clear pending audio
    } else {
        btn.textContent = '🔊 声音开';
        btn.classList.remove('muted');
    }
}

function clearTranslations() {
    const container = document.getElementById('translations');
    container.innerHTML = `
        <div class="placeholder">
            <p>翻译内容将显示在这里</p>
            <p class="hint">开始播放音频即可翻译</p>
        </div>
    `;
}

function stopTranslation() {
    // Send stop command to server
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'stop' }));
    }
    
    // Clear audio queue
    audioQueue = [];
    isPlaying = false;
    
    // Update UI
    updateStatus('⏹️ 翻译已停止');
    
    // Show confirmation alert (helpful for dad)
    alert('翻译已停止！');
}

// Utility
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Heartbeat to keep connection alive
setInterval(() => {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'ping' }));
    }
}, 30000);
