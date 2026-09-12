import os
import secrets
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bsher-full-whatsapp-2026'
# زيادة حجم الاستيعاب إلى 50 ميجا لرفع الصور والفيديوهات والحالات بحرية
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading", max_http_buffer_size=50000000)

ADMIN_TOKEN = "bsher-admin-master-key-2026"

slots = {
    0: {
        "type": "admin",
        "token": ADMIN_TOKEN,
        "name": "المشرف (بشر)",
        "bio": "مالك التطبيق 👑",
        "avatar": "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
    }
}

for i in range(1, 20):
    slots[i] = {
        "type": "user",
        "token": secrets.token_hex(6),
        "name": f"مستخدم #{i}",
        "bio": "أهلاً بي في bisher chat",
        "avatar": "https://cdn-icons-png.flaticon.com/512/149/149071.png"
    }

statuses = []

def get_slot_by_token(token):
    for slot_id, data in slots.items():
        if data["token"] == token:
            return slot_id, data
    return None, None

HTML_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>bisher chat</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: #0b141a; color: #e9edef; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        
        /* Header */
        .header { background-color: #202c33; padding: 10px 14px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #222d34; height: 60px; }
        .user-info { display: flex; align-items: center; gap: 10px; }
        .avatar { width: 42px; height: 42px; border-radius: 50%; object-fit: cover; border: 1.5px solid #00a884; }
        .user-details h4 { font-size: 15px; color: #e9edef; font-weight: 600; }
        .user-details p { font-size: 11px; color: #8696a0; }
        .call-actions { display: flex; gap: 10px; }
        .btn-call { background: #2a3942; border: none; color: #00a884; width: 36px; height: 36px; border-radius: 50%; font-size: 16px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
        
        /* Navigation Tabs */
        .nav-tabs { display: flex; background-color: #111b21; border-bottom: 1px solid #222d34; }
        .tab-btn { flex: 1; padding: 12px; text-align: center; background: none; border: none; color: #8696a0; font-weight: 600; font-size: 13px; cursor: pointer; border-bottom: 3px solid transparent; }
        .tab-btn.active { color: #00a884; border-bottom-color: #00a884; }
        
        /* Content Panels */
        .content { flex: 1; overflow-y: auto; display: none; padding: 12px; background-color: #0b141a; }
        .content.active { display: block; }
        
        /* Chat Container */
        #chatTab { padding: 10px; display: flex; flex-direction: column; height: calc(100vh - 170px); }
        .chat-box { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; padding-bottom: 10px; }
        
        /* Messages */
        .msg { max-width: 80%; padding: 8px 12px; border-radius: 8px; font-size: 14px; line-height: 1.4; word-break: break-word; }
        .my-msg { background-color: #005c4b; align-self: flex-start; border-top-right-radius: 0; color: #e9edef; }
        .other-msg { background-color: #202c33; align-self: flex-end; border-top-left-radius: 0; color: #e9edef; }
        .sender-title { font-size: 11px; color: #53bdeb; font-weight: bold; margin-bottom: 3px; }
        .msg-time { font-size: 9px; color: #8696a0; margin-top: 4px; text-align: left; }
        .chat-media { max-width: 100%; max-height: 220px; border-radius: 8px; margin-top: 4px; }
        audio { width: 220px; height: 35px; margin-top: 4px; }
        
        /* Bottom Input Bar */
        .input-bar { background-color: #202c33; padding: 8px 10px; display: flex; gap: 6px; align-items: center; position: fixed; bottom: 0; left: 0; right: 0; height: 60px; border-top: 1px solid #222d34; }
        .input-bar input[type="text"] { flex: 1; background-color: #2a3942; border: none; padding: 10px 14px; border-radius: 20px; color: white; outline: none; font-size: 14px; }
        .icon-btn { background: none; border: none; font-size: 19px; cursor: pointer; padding: 5px; color: #8696a0; }
        .btn-send { background-color: #00a884; color: #111b21; border: none; width: 40px; height: 40px; border-radius: 50%; font-size: 18px; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center; }
        
        /* Emoji Panel */
        .emoji-panel { display: none; background: #202c33; padding: 10px; position: fixed; bottom: 65px; left: 10px; right: 10px; border-radius: 12px; grid-template-columns: repeat(8, 1fr); gap: 8px; text-align: center; border: 1px solid #3b4a54; max-height: 140px; overflow-y: auto; }
        .emoji-panel span { font-size: 22px; cursor: pointer; }
        
        /* Status Card */
        .status-card { background: #202c33; padding: 12px; border-radius: 10px; margin-bottom: 12px; border: 1px solid #222d34; }
        .status-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
        .status-header img { width: 38px; height: 38px; border-radius: 50%; border: 2px solid #00a884; }
        .status-body-text { font-size: 14px; color: #00a884; margin-bottom: 6px; font-weight: 500; }
        .status-media { width: 100%; max-height: 250px; border-radius: 8px; object-fit: cover; }
        
        /* Status Publisher Box */
        .status-publisher { background: #202c33; padding: 14px; border-radius: 10px; margin-bottom: 15px; display: flex; flex-direction: column; gap: 10px; border: 1px solid #222d34; }
        .status-publisher textarea { background: #2a3942; border: none; padding: 10px; border-radius: 8px; color: white; resize: none; font-size: 13px; outline: none; }
        .status-actions { display: flex; justify-content: space-between; align-items: center; }
        
        /* Admin Grid */
        .qr-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; padding-bottom: 70px; }
        .qr-card { background-color: #202c33; padding: 12px; border-radius: 10px; text-align: center; border: 1px solid #222d34; }
        .btn-kick { background-color: #ea868f; color: #842029; border: none; padding: 8px 16px; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top: 8px; width: 100%; }
        
        /* Profile Form */
        .profile-form { display: flex; flex-direction: column; gap: 12px; max-width: 400px; margin: 0 auto; background: #202c33; padding: 20px; border-radius: 10px; text-align: center; }
        .profile-form label { font-size: 12px; color: #8696a0; text-align: right; }
        .profile-form input[type="text"] { background: #2a3942; border: 1px solid #3b4a54; padding: 10px; border-radius: 6px; color: white; }
        .profile-avatar-preview { width: 90px; height: 90px; border-radius: 50%; object-fit: cover; margin: 0 auto 10px auto; border: 3px solid #00a884; }

        /* Video Call Overlay Modal */
        #callModal { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(11,20,26,0.95); z-index: 9999; flex-direction: column; align-items: center; justify-content: space-between; padding: 20px; }
        .video-container { display: flex; flex-direction: column; width: 100%; max-width: 400px; height: 75%; position: relative; gap: 10px; }
        video { width: 100%; height: 100%; background: #000; border-radius: 12px; object-fit: cover; }
        #localVideo { position: absolute; top: 10px; right: 10px; width: 100px; height: 140px; border: 2px solid #00a884; z-index: 10; }
        .call-controls { display: flex; gap: 20px; margin-bottom: 20px; }
        .btn-end-call { background: #ea868f; color: white; border: none; width: 60px; height: 60px; border-radius: 50%; font-size: 24px; cursor: pointer; }
    </style>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
</head>
<body>

    <!-- Header -->
    <div class="header">
        <div class="user-info">
            <img src="{{ user_data.avatar }}" class="avatar" id="hdrAvatar">
            <div class="user-details">
                <h4 id="hdrName">{{ user_data.name }}</h4>
                <p>{{ user_data.bio }}</p>
            </div>
        </div>
        <div class="call-actions">
            <button class="btn-call" onclick="startCall(false)">📞</button>
            <button class="btn-call" onclick="startCall(true)">📹</button>
        </div>
    </div>

    <!-- Navigation Tabs -->
    <div class="nav-tabs">
        <button class="tab-btn active" onclick="switchTab('chatTab')">💬 الدردشة</button>
        <button class="tab-btn" onclick="switchTab('statusTab')">⭕ الحالات</button>
        <button class="tab-btn" onclick="switchTab('profileTab')">👤 البروفايل</button>
        {% if user_data.type == 'admin' %}
        <button class="tab-btn" onclick="switchTab('adminTab')">👑 لوحة الأكواد (20)</button>
        {% endif %}
    </div>

    <!-- Tab 1: Chat -->
    <div id="chatTab" class="content active">
        <div class="chat-box" id="chatBox"></div>
    </div>

    <!-- Tab 2: Statuses -->
    <div id="statusTab" class="content">
        <div class="status-publisher">
            <textarea id="statusText" rows="2" placeholder="اكتب حالتك الجديدة..."></textarea>
            <div class="status-actions">
                <div>
                    <button class="icon-btn" onclick="document.getElementById('statusMediaFile').click()">📷 / 🎥 إضافة ملف</button>
                    <input type="file" id="statusMediaFile" accept="image/*,video/*" style="display:none;" onchange="previewStatusMedia(this)">
                </div>
                <button onclick="postStatus()" style="background:#00a884; color:#111b21; border:none; padding:8px 16px; border-radius:6px; font-weight:bold; cursor:pointer;">نشر الحالة</button>
            </div>
            <div id="statusMediaPreview" style="font-size:11px; color:#00a884; display:none;">✅ تم تزويد ملف الحالة جاهز للنشر</div>
        </div>
        
        <h4 style="margin-bottom:10px; color:#8696a0; font-size:13px;">الحالات الحديثة</h4>
        <div id="statusList">
            {% for st in statuses %}
            <div class="status-card">
                <div class="status-header">
                    <img src="{{ st.avatar }}">
                    <div>
                        <h4 style="font-size:13px; color:#e9edef;">{{ st.name }}</h4>
                        <span style="font-size:10px; color:#8696a0;">{{ st.time }}</span>
                    </div>
                </div>
                {% if st.text %}
                <p class="status-body-text">{{ st.text }}</p>
                {% endif %}
                {% if st.media_type == 'image' %}
                <img src="{{ st.media_url }}" class="status-media">
                {% elif st.media_type == 'video' %}
                <video src="{{ st.media_url }}" controls class="status-media"></video>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>

    <!-- Tab 3: Profile -->
    <div id="profileTab" class="content">
        <div class="profile-form">
            <img src="{{ user_data.avatar }}" class="profile-avatar-preview" id="previewProfileAvatar">
            
            <button type="button" onclick="document.getElementById('avatarFileInput').click()" style="background:#2a3942; color:#00a884; border:1px solid #00a884; padding:8px; border-radius:6px; font-size:12px; font-weight:bold; cursor:pointer; margin-bottom:10px;">📷 تغيير الصورة من الهاتف</button>
            <input type="file" id="avatarFileInput" accept="image/*" style="display:none;" onchange="uploadAvatarFile(this)">

            <label>الاسم الظاهر</label>
            <input type="text" id="inputName" value="{{ user_data.name }}">
            
            <label>النبذة التعريفية (Bio)</label>
            <input type="text" id="inputBio" value="{{ user_data.bio }}">
            
            <button onclick="saveProfile()" style="background:#00a884; color:#111b21; border:none; padding:12px; border-radius:6px; font-weight:bold; cursor:pointer; margin-top:10px;">حفظ والتحديث</button>
        </div>
    </div>

    <!-- Tab 4: Admin Panel -->
    {% if user_data.type == 'admin' %}
    <div id="adminTab" class="content">
        <h4 style="margin-bottom:12px; color:#00a884;">أكواد الـ QR والتحكم بالمستخدمين</h4>
        <div class="qr-grid">
            {% for sid, sinfo in all_slots.items() %}
            <div class="qr-card">
                <h4>{{ sinfo.name }} {% if sid == 0 %}(أنت - المالك){% endif %}</h4>
                <p style="font-size:11px; color:#8696a0; margin-bottom:6px;">{{ sinfo.bio }}</p>
                <img src="https://api.qrserver.com/v1/create-qr-code/?size=140x140&data={{ base_url }}/?token={{ sinfo.token }}" width="130" height="130" style="border:3px solid white; border-radius:6px;">
                <p style="font-size:10px; color:#00a884; word-break:break-all; margin-top:4px;">{{ base_url }}/?token={{ sinfo.token }}</p>
                {% if sid != 0 %}
                <button class="btn-kick" onclick="kickUser({{ sid }})">🚫 طرد وتجديد الـ QR</button>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>
    {% endif %}

    <!-- Emoji Panel -->
    <div class="emoji-panel" id="emojiPanel">
        <span onclick="addEmoji('😀')">😀</span><span onclick="addEmoji('😂')">😂</span>
        <span onclick="addEmoji('😍')">😍</span><span onclick="addEmoji('👍')">👍</span>
        <span onclick="addEmoji('❤️')">❤️</span><span onclick="addEmoji('🔥')">🔥</span>
        <span onclick="addEmoji('🙏')">🙏</span><span onclick="addEmoji('🎉')">🎉</span>
        <span onclick="addEmoji('😎')">😎</span><span onclick="addEmoji('🙌')">🙌</span>
        <span onclick="addEmoji('✨')">✨</span><span onclick="addEmoji('💯')">💯</span>
    </div>

    <!-- Input Bar -->
    <div class="input-bar" id="inputBar">
        <button class="icon-btn" onclick="toggleEmoji()">😊</button>
        <button class="icon-btn" onclick="document.getElementById('imgFile').click()">📷</button>
        <input type="file" id="imgFile" accept="image/*,video/*" style="display:none;" onchange="sendMediaMessage(this)">
        <input type="text" id="msgText" placeholder="اكتب رسالتك...">
        <button class="icon-btn" id="micBtn" onclick="toggleRecord()">🎙️</button>
        <button class="btn-send" onclick="sendMsg()">➤</button>
    </div>

    <!-- Call Overlay Modal -->
    <div id="callModal">
        <h3 id="callStatusText" style="color:#00a884; margin-top:10px;">جاري الاتصال...</h3>
        <div class="video-container">
            <video id="remoteVideo" autoplay playsinline></video>
            <video id="localVideo" autoplay playsinline muted></video>
        </div>
        <div class="call-controls">
            <button class="btn-end-call" onclick="endCall()">📞</button>
        </div>
    </div>

    <script>
        const currentToken = "{{ user_data.token }}";
        let currentAvatarData = "{{ user_data.avatar }}";
        let currentStatusMediaData = "", currentStatusMediaType = "";
        const socket = io();

        socket.emit('join', { token: currentToken });

        socket.on('receive_message', function(data) {
            const chatBox = document.getElementById("chatBox");
            const div = document.createElement("div");
            
            let contentHtml = "";
            if (data.msg_type === 'text') {
                contentHtml = data.text;
            } else if (data.msg_type === 'image') {
                contentHtml = `<img src="${data.media_url}" class="chat-media">`;
            } else if (data.msg_type === 'video') {
                contentHtml = `<video src="${data.media_url}" controls class="chat-media"></video>`;
            } else if (data.msg_type === 'audio') {
                contentHtml = `<audio controls src="${data.media_url}"></audio>`;
            }

            if (data.token === currentToken) {
                div.className = "msg my-msg";
                div.innerHTML = contentHtml + `<div class="msg-time">${data.time}</div>`;
            } else {
                div.className = "msg other-msg";
                div.innerHTML = `<div class="sender-title">${data.name}</div>` + contentHtml + `<div class="msg-time">${data.time}</div>`;
            }
            
            chatBox.appendChild(div);
            chatBox.scrollTop = chatBox.scrollHeight;
        });

        socket.on('new_status', function(st) {
            const list = document.getElementById("statusList");
            const card = document.createElement("div");
            card.className = "status-card";
            
            let mediaHtml = "";
            if (st.media_type === 'image') mediaHtml = `<img src="${st.media_url}" class="status-media">`;
            else if (st.media_type === 'video') mediaHtml = `<video src="${st.media_url}" controls class="status-media"></video>`;

            card.innerHTML = `<div class="status-header"><img src="${st.avatar}"><div><h4 style="font-size:13px; color:#e9edef;">${st.name}</h4><span style="font-size:10px; color:#8696a0;">${st.time}</span></div></div>` +
                             (st.text ? `<p class="status-body-text">${st.text}</p>` : '') + mediaHtml;
            list.prepend(card);
        });

        socket.on('kicked', function() {
            alert('تم طردك وتحديث كود الدخول الخاص بك!');
            window.location.reload();
        });

        function sendMsg() {
            const input = document.getElementById("msgText");
            if (input.value.trim() !== "") {
                socket.emit('send_message', { token: currentToken, msg_type: 'text', text: input.value });
                input.value = "";
                document.getElementById("emojiPanel").style.display = "none";
            }
        }

        function sendMediaMessage(input) {
            if (input.files && input.files[0]) {
                const file = input.files[0];
                const reader = new FileReader();
                const isVideo = file.type.startsWith('video');
                reader.onload = function(e) {
                    socket.emit('send_message', { 
                        token: currentToken, 
                        msg_type: isVideo ? 'video' : 'image', 
                        media_url: e.target.result 
                    });
                };
                reader.readAsDataURL(file);
            }
        }

        function uploadAvatarFile(input) {
            if (input.files && input.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    currentAvatarData = e.target.result;
                    document.getElementById('previewProfileAvatar').src = currentAvatarData;
                };
                reader.readAsDataURL(input.files[0]);
            }
        }

        function previewStatusMedia(input) {
            if (input.files && input.files[0]) {
                const file = input.files[0];
                currentStatusMediaType = file.type.startsWith('video') ? 'video' : 'image';
                const reader = new FileReader();
                reader.onload = function(e) {
                    currentStatusMediaData = e.target.result;
                    document.getElementById('statusMediaPreview').style.display = 'block';
                };
                reader.readAsDataURL(file);
            }
        }

        function postStatus() {
            const txt = document.getElementById("statusText");
            if (txt.value.trim() !== "" || currentStatusMediaData !== "") {
                socket.emit('add_status', { 
                    token: currentToken, 
                    text: txt.value,
                    media_url: currentStatusMediaData,
                    media_type: currentStatusMediaType
                });
                txt.value = "";
                currentStatusMediaData = "";
                currentStatusMediaType = "";
                document.getElementById('statusMediaPreview').style.display = 'none';
            }
        }

        // Voice Recording Script
        let mediaRecorder, audioChunks = [], isRecording = false;
        async function toggleRecord() {
            const micBtn = document.getElementById("micBtn");
            if (!isRecording) {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                    audioChunks = [];
                    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
                    mediaRecorder.onstop = () => {
                        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                        const reader = new FileReader();
                        reader.onload = function(e) {
                            socket.emit('send_message', { token: currentToken, msg_type: 'audio', media_url: e.target.result });
                        };
                        reader.readAsDataURL(audioBlob);
                    };
                    mediaRecorder.start();
                    isRecording = true;
                    micBtn.style.color = "#ea868f";
                } catch(err) {
                    alert("يرجى إعطاء الصلاحية لاستخدام الميكروفون!");
                }
            } else {
                mediaRecorder.stop();
                isRecording = false;
                micBtn.style.color = "#8696a0";
            }
        }

        // WebRTC Video & Audio Calling Logic
        let localStream, peerConnection;
        const config = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };

        async function startCall(isVideo) {
            document.getElementById('callModal').style.display = 'flex';
            document.getElementById('callStatusText').innerText = "جاري فتح الكاميرا والصوت...";
            try {
                localStream = await navigator.mediaDevices.getUserMedia({ video: isVideo, audio: true });
                document.getElementById('localVideo').srcObject = localStream;
                
                peerConnection = new RTCPeerConnection(config);
                localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));

                peerConnection.ontrack = e => {
                    document.getElementById('remoteVideo').srcObject = e.streams[0];
                };

                peerConnection.onicecandidate = e => {
                    if (e.candidate) socket.emit('signal', { token: currentToken, type: 'candidate', candidate: e.candidate });
                };

                const offer = await peerConnection.createOffer();
                await peerConnection.setLocalDescription(offer);
                socket.emit('signal', { token: currentToken, type: 'offer', offer: offer });
                document.getElementById('callStatusText').innerText = "جاري الاتصال بالفريق...";
            } catch(e) {
                alert("يرجى إعطاء صلاحيات الكاميرا والميكروفون للاتصال!");
                endCall();
            }
        }

        socket.on('signal', async function(data) {
            if (data.token === currentToken) return;
            
            if (data.type === 'offer') {
                if (confirm("مكالمة واردة! هل تريد الرد؟")) {
                    document.getElementById('callModal').style.display = 'flex';
                    localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
                    document.getElementById('localVideo').srcObject = localStream;
                    
                    peerConnection = new RTCPeerConnection(config);
                    localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));

                    peerConnection.ontrack = e => {
                        document.getElementById('remoteVideo').srcObject = e.streams[0];
                    };

                    peerConnection.onicecandidate = e => {
                        if (e.candidate) socket.emit('signal', { token: currentToken, type: 'candidate', candidate: e.candidate });
                    };

                    await peerConnection.setRemoteDescription(new RTCSessionDescription(data.offer));
                    const answer = await peerConnection.createAnswer();
                    await peerConnection.setLocalDescription(answer);
                    socket.emit('signal', { token: currentToken, type: 'answer', answer: answer });
                    document.getElementById('callStatusText').innerText = "المكالمة متصلة 🟢";
                }
            } else if (data.type === 'answer' && peerConnection) {
                await peerConnection.setRemoteDescription(new RTCSessionDescription(data.answer));
                document.getElementById('callStatusText').innerText = "المكالمة متصلة 🟢";
            } else if (data.type === 'candidate' && peerConnection) {
                await peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
            } else if (data.type === 'end') {
                endCall(false);
            }
        });

        function endCall(emitEvent = true) {
            if (emitEvent) socket.emit('signal', { token: currentToken, type: 'end' });
            if (localStream) localStream.getTracks().forEach(track => track.stop());
            if (peerConnection) peerConnection.close();
            document.getElementById('callModal').style.display = 'none';
        }

        function toggleEmoji() {
            const p = document.getElementById("emojiPanel");
            p.style.display = (p.style.display === "grid") ? "none" : "grid";
        }

        function addEmoji(emoji) {
            document.getElementById("msgText").value += emoji;
        }

        function switchTab(tabId) {
            document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            event.target.classList.add('active');
            
            document.getElementById('inputBar').style.display = (tabId === 'chatTab') ? 'flex' : 'none';
        }

        function saveProfile() {
            const name = document.getElementById('inputName').value;
            const bio = document.getElementById('inputBio').value;
            fetch('/update_profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: currentToken, name: name, bio: bio, avatar: currentAvatarData })
            }).then(() => location.reload());
        }

        function kickUser(slotId) {
            if (confirm('هل أنت تأكد من طرد هذا المستخدم؟')) {
                fetch('/kick_user', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ admin_token: currentToken, slot_id: slotId })
                }).then(() => location.reload());
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    token = request.args.get('token', ADMIN_TOKEN)
    slot_id, user_data = get_slot_by_token(token)
    
    if not user_data:
        return "<h2 style='color:white; background:#111b21; padding:20px; text-align:center;'>❌ رابط الـ QR غير صالح!</h2>", 403
        
    base_url = request.host_url.rstrip('/')
    return render_template_string(HTML_PAGE, user_data=user_data, all_slots=slots, statuses=statuses, base_url=base_url)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    data = request.json
    slot_id, user_data = get_slot_by_token(data.get('token'))
    if user_data:
        user_data['name'] = data.get('name', user_data['name'])
        user_data['bio'] = data.get('bio', user_data['bio'])
        user_data['avatar'] = data.get('avatar', user_data['avatar'])
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

@app.route('/kick_user', methods=['POST'])
def kick_user():
    data = request.json
    if data.get('admin_token') == ADMIN_TOKEN:
        slot_id = int(data.get('slot_id'))
        if slot_id in slots and slot_id != 0:
            slots[slot_id]['token'] = secrets.token_hex(6)
            slots[slot_id]['name'] = f"مستخدم #{slot_id}"
            slots[slot_id]['bio'] = "أهلاً بي في bisher chat"
            socketio.emit('kicked', room=f"slot_{slot_id}")
            return jsonify({"success": True})
    return jsonify({"success": False}), 403

@socketio.on('join')
def on_join(data):
    slot_id, user_data = get_slot_by_token(data.get('token'))
    if user_data:
        join_room(f"slot_{slot_id}")
        join_room("global_chat")

@socketio.on('send_message')
def handle_message(data):
    slot_id, user_data = get_slot_by_token(data.get('token'))
    if user_data:
        now_time = datetime.now().strftime("%I:%M %p")
        emit('receive_message', {
            'token': user_data['token'],
            'name': user_data['name'],
            'msg_type': data.get('msg_type', 'text'),
            'text': data.get('text', ''),
            'media_url': data.get('media_url', ''),
            'time': now_time
        }, room="global_chat")

@socketio.on('add_status')
def handle_status(data):
    slot_id, user_data = get_slot_by_token(data.get('token'))
    if user_data:
        st_obj = {
            'name': user_data['name'],
            'avatar': user_data['avatar'],
            'text': data.get('text', ''),
            'media_url': data.get('media_url', ''),
            'media_type': data.get('media_type', ''),
            'time': datetime.now().strftime("%I:%M %p")
        }
        statuses.insert(0, st_obj)
        emit('new_status', st_obj, broadcast=True)

@socketio.on('signal')
def handle_signal(data):
    emit('signal', data, room="global_chat")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
