/**
 * Conversation Mode JavaScript
 * Press and HOLD button while speaking, release when done
 */

let socket = null;
let mediaRecorder = null;
let mediaStream = null;
let currentMode = null;
let isRecording = false;
let pendingAudioForSpeaker = null;

const statusEl = document.getElementById('status');
const conversationEl = document.getElementById('conversation');
const dadBtn = document.getElementById('dadBtn');
const friendBtn = document.getElementById('friendBtn');

/**
 * Start recording when button is pressed
 */
async function startRecording(mode) {
    if (isRecording) return;
    
    isRecording = true;
    currentMode = mode;
    
    const btn = mode === 'dad' ? dadBtn : friendBtn;
    btn.classList.add('recording');
    statusEl.textContent = mode === 'dad' ? '🔴 说中文... (说完松开)' : '🔴 Speak English... (release when done)';
    
    try {
        mediaStream = await navigator.mediaDevices.getUserMedia({ 
            audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } 
        });
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        socket = new WebSocket(`${protocol}//${window.location.host}/ws/conversation?mode=${mode}`);
        
        socket.onopen = () => {
            console.log('WebSocket connected');
            try {
                mediaRecorder = new MediaRecorder(mediaStream, { mimeType: 'audio/webm;codecs=opus' });
            } catch (e) {
                mediaRecorder = new MediaRecorder(mediaStream, { mimeType: 'audio/webm' });
            }
            
            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0 && socket && socket.readyState === WebSocket.OPEN) {
                    socket.send(event.data);
                }
            };
            mediaRecorder.start(250);
        };
        
        socket.onmessage = (event) => {
            if (typeof event.data === 'string') {
                try {
                    handleMessage(JSON.parse(event.data));
                } catch (e) {
                    console.error('Parse error:', e);
                }
            } else {
                handleAudioData(event.data);
            }
        };
        
        socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            statusEl.textContent = '❌ 连接错误';
            cleanup();
        };
        
        socket.onclose = () => {
            console.log('WebSocket closed');
            cleanup(); // Full cleanup including media stream
        };
        
    } catch (error) {
        console.error('Error:', error);
        statusEl.textContent = '❌ ' + error.message;
        cleanup();
    }
}

/**
 * Stop recording when button is released
 */
function stopRecording() {
    if (!isRecording) return;
    
    console.log('Stopping...');
    statusEl.textContent = '⏳ 处理中... Processing...';
    
    // Send STOP signal AFTER recorder stops and flushes last data
    mediaRecorder.onstop = () => {
        if (socket && socket.readyState === WebSocket.OPEN) {
            console.log('Recorder stopped, sending stop signal');
            socket.send(JSON.stringify({ type: "stop" }));
            
            // Safety close after response received
            setTimeout(() => {
                if (socket && socket.readyState === WebSocket.OPEN) {
                    socket.close();
                }
            }, 8000); 
        }
    };
    
    // Wait 800ms to capture more audio before stopping
    // This ensures the last words spoken are included in the recording
    setTimeout(() => {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
            // Do NOT stop tracks here, wait for socket close to cleanup
        }
    }, 800);
}

function cleanup() {
    isRecording = false;
    dadBtn.classList.remove('recording');
    friendBtn.classList.remove('recording');
    
    // Stop all media tracks
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
        mediaStream = null;
    }
    
    mediaRecorder = null;
    socket = null;
    statusEl.textContent = '准备就绪 Ready';
}

function handleAudioData(audioBlob) {
    // Auto-play all audio since users are sharing earbuds
    playAudio(audioBlob);
}

async function playAudio(audioBlob) {
    statusEl.textContent = '🔊 播放中... Playing...';
    const audio = new Audio(URL.createObjectURL(new Blob([audioBlob], { type: 'audio/mpeg' })));
    audio.onended = () => { statusEl.textContent = '准备就绪 Ready'; };
    audio.onerror = () => { statusEl.textContent = '❌ 播放失败'; };
    try { await audio.play(); } catch (e) { statusEl.textContent = '❌ 播放失败'; }
}

function handleMessage(msg) {
    if (msg.type === 'translation') {
        statusEl.textContent = '⏳ 生成语音...';
        addTranslation(msg.original, msg.translation);
    } else if (msg.type === 'transcription_update') {
        // Show what we hear so far
        statusEl.textContent = '👂 ' + msg.text;
    } else if (msg.type === 'error') {
        statusEl.textContent = '❌ ' + msg.message;
    }
}

function addTranslation(original, translation) {
    const placeholder = document.getElementById('placeholder');
    if (placeholder) placeholder.remove();
    
    const div = document.createElement('div');
    div.className = `message ${currentMode}`;
    div.innerHTML = `
        <div class="message-original">${escapeHtml(original)}</div>
        <div class="message-translation">${escapeHtml(translation)}</div>
    `;
    conversationEl.appendChild(div);
    conversationEl.scrollTop = conversationEl.scrollHeight;
}

function clearConversation() {
    conversationEl.innerHTML = `<div class="placeholder" id="placeholder">
        <p>� 长按按钮说话</p><p class="hint">Press & hold to speak</p>
    </div>`;
    pendingAudioForSpeaker = null;
    statusEl.textContent = '准备就绪 Ready';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

document.addEventListener('contextmenu', e => e.preventDefault());
document.querySelectorAll('.btn').forEach(btn => {
    btn.addEventListener('touchstart', e => e.preventDefault(), { passive: false });
});
