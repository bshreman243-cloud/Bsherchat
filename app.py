import os
import secrets
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bsher-whatsapp-secret-2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading", max_http_buffer_size=10000000)

ADMIN_TOKEN = "bsher-admin-master-key-2026"

# تهيئة الـ 20 فتحة (الأدمن + 19 مستخدم)
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

# قائمة الحالات والستوريات
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
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
        body { background-color: #0b141a; color: #e9edef; display: flex; flex-direction: column; height: 100vh; overflow: hidden; }
        
        /* Header */
        .header { background-color: #202c33; padding: 10px 16px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #222d34; height: 60px; }
        .user-info { display: flex; align-items: center; gap: 12px; }
        .avatar { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; border: 1px solid #00a884; }
        .user-details h4 { font-size: 15px; color: #e9edef; font-weight: 600; }
        .user-details p { font-size: 12px; color: #8696a0; }
        
        /* Navigation Tabs */
        .nav-tabs { display: flex; background-color: #111b21; border-bottom: 1px solid #222d34; }
        .tab-btn { flex: 1; padding: 12px; text-align: center; background: none; border: none; color: #8696a0; font-weight: 600; font-size: 14px; cursor: pointer; border-bottom: 3px solid transparent; transition: 0.2s; }
        .tab-btn.active { color: #00a884; border-bottom-color: #00a884; }
        
        /* Content Panels */
        .content { flex: 1; overflow-y: auto; display: none; padding: 12px; background-color: #0b141a; }
        .content.active { display: block; }
        
        /* Chat Container */
        #chatTab { padding: 10px; display: flex; flex-direction: column; height: calc(100vh - 170px); }
        .chat-box { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; padding-bottom: 10px; }
        
        /* Message Bubbles */
        .msg { max-width: 80%; padding: 8px 12px; border-radius: 8px; font-size: 14px; line-height: 1.4; word-break: break-word; position: relative; }
        .my-msg { background-color: #005c4b; align-self: flex-start; border-top-right-radius: 0; color: #e9edef; }
        .other-msg { background-color: #202c33; align-self: flex-end; border-top-left-radius: 0; color: #e9edef; }
        .sender-title { font-size: 11px; color: #53bdeb; font-weight: bold; margin-bottom: 3px; }
        .msg-time { font-size: 9px; color: #8696a0; margin-top: 4px; text-align: left; }
        .chat-img { max-width: 100%; max-height: 220px; border-radius: 8px; margin-top: 4px; }
        audio { width: 220px; height: 35px; margin-top: 4px; }
        
        /* Bottom Input Bar */
        .input-bar { background-color: #202c33; padding: 8px 10px; display: flex; gap: 8px; align-items: center; position: fixed; bottom: 0; left: 0; right: 0; height: 60px; border-top: 1px solid #222d34; }
        .input-bar input[type="text"] { flex: 1; background-color: #2a3942; border: none; padding: 10px 14px; border-radius: 20px; color: white; outline: none; font-size: 14px; }
        .icon-btn { background: none; border: none; font-size: 20px; cursor: pointer; padding: 6px; color: #8696a0; }
        .btn-send { background-color: #00a884; color: #111b21; border: none; width: 40px; height: 40px; border-radius: 50%; font-size: 18px; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center; }
        
        /* Emoji Picker Panel */
        .emoji-panel { display: none; background: #202c33; padding: 10px; position: fixed; bottom: 65px; left: 10px; right: 10px; border-radius: 12px; grid-template-columns: repeat(8, 1fr); gap: 8px; text-align: center; border: 1px solid #3b4a54; max-height: 150px; overflow-y: auto; }
        .emoji-panel span { font-size: 22px; cursor: pointer; }
        
        /* Status / Stories Tab */
        .status-card { background: #202c33; padding: 12px; border-radius: 10px; margin-bottom: 10px; display: flex; align-items: center; gap: 12px; border: 1px solid #222d34; }
        .status-card img { width: 45px; height: 45px; border-radius: 50%; border: 2px solid #00a884; }
        .status-box { background: #202c33; padding: 15px; border-radius: 10px; margin-bottom: 15px; display: flex; gap: 8px; }
        
        /* Admin Grid & QR Cards */
        .qr-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; padding-bottom: 70px; }
        .qr-card { background-color: #202c33; padding: 12px; border-radius: 10px; text-align: center; border: 1px solid #222d34; }
        .btn-kick { background-color: #ea868f; color: #842029; border: none; padding: 8px 16px; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top: 8px; width: 100%; }
        
        /* Profile Form */
        .profile-form { display: flex; flex-direction: column; gap: 12px; max-width: 400px; margin: 0 auto; background: #202c33; padding: 20px; border-radius: 10px; }
        .profile-form label { font-size: 12px; color: #8696a0; }
        .profile-form input { background: #2a3942; border: 1px solid #3b4a54; padding: 10px; border-radius: 6px; color: white; }
    </style>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
</head>
<body>

    <!-- Upper Header -->
    <div class="header">
        <div class="user-info">
            <img src="{{ user_data.avatar }}" class="avatar">
            <div class="user-details">
                <h4>{{ user_data.name }}</h4>
                <p>{{ user_data.bio }}</p>
            </div>
        </div>
        <span style="color: #00a884; font-size: 12px; font-weight: bold;">🟢 نشط الآن</span>
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
        <div class="status-box">
            <input type="text" id="statusText" placeholder="اكتب حالتك الجديدة..." style="flex:1; background:#2a3942; border:none; padding:10px; border-radius:8px; color:white;">
            <button onclick="postStatus()" style="background:#00a884; color:#111b21; border:none; padding:10px 15px; border-radius:8px; font-weight:bold; cursor:pointer;">نشر</button>
        </div>
        <h4 style="margin-bottom:10px; color:#8696a0; font-size:13px;">الحالات الحديثة</h4>
        <div id="statusList">
            {% for st in statuses %}
            <div class="status-card">
                <img src="{{ st.avatar }}">
                <div>
                    <h4 style="font-size:14px; color:#e9edef;">{{ st.name }}</h4>
                    <p style="font-size:13px; color:#00a884; margin-top:2px;">{{ st.text }}</p>
                    <span style="font-size:10px; color:#8696a0;">{{ st.time }}</span>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>

    <!-- Tab 3: Profile -->
    <div id="profileTab" class="content">
        <div class="profile-form">
            <label>الاسم الظاهر</label>
            <input type="text" id="inputName" value="{{ user_data.name }}">
            
            <label>النبذة التعريفية (Bio)</label>
            <input type="text" id="inputBio" value="{{ user_data.bio }}">
            
            <label>رابط الصورة الشخصية</label>
            <input type="text" id="inputAvatar" value="{{ user_data.avatar }}">
            
            <button onclick="saveProfile()" style="background:#00a884; color:#111b21; border:none; padding:12px; border-radius:6px; font-weight:bold; cursor:pointer;">حفظ البيانات</button>
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
        <span onclick="addEmoji('😭')">😭</span><span onclick="addEmoji('🥳')">🥳</span>
        <span onclick="addEmoji('👏')">👏</span><span onclick="addEmoji('🤍')">🤍</span>
    </div>

    <!-- Input Bar (For Chat) -->
    <div class="input-bar" id="inputBar">
        <button class="icon-btn" onclick="toggleEmoji()">😊</button>
        <button class="icon-btn" onclick="document.getElementById('imgFile').click()">📷</button>
        <input type="file" id="imgFile" accept="image/*" style="display:none;" onchange="sendImage(this)">
        <input type="text" id="msgText" placeholder="اكتب رسالتك...">
        <button class="icon-btn" id="micBtn" onclick="toggleRecord()">🎙️</button>
        <button class="btn-send" onclick="sendMsg()">➤</button>
    </div>

    <script>
        const currentToken = "{{ user_data.token }}";
        const socket = io();

        socket.emit('join', { token: currentToken });

        socket.on('receive_message', function(data) {
            const chatBox = document.getElementById("chatBox");
            const div = document.createElement("div");
            
            let contentHtml = "";
            if (data.msg_type === 'text') {
                contentHtml = data.text;
            } else if (data.msg_type === 'image') {
                contentHtml = `<img src="${data.media_url}" class="chat-img">`;
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
            card.innerHTML = `<img src="${st.avatar}"><div><h4 style="font-size:14px; color:#e9edef;">${st.name}</h4><p style="font-size:13px; color:#00a884; margin-top:2px;">${st.text}</p><span style="font-size:10px; color:#8696a0;">${st.time}</span></div>`;
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

        function sendImage(input) {
            if (input.files && input.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    socket.emit('send_message', { token: currentToken, msg_type: 'image', media_url: e.target.result });
                };
                reader.readAsDataURL(input.files[0]);
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

        function toggleEmoji() {
            const p = document.getElementById("emojiPanel");
            p.style.display = (p.style.display === "grid") ? "none" : "grid";
        }

        function addEmoji(emoji) {
            document.getElementById("msgText").value += emoji;
        }

        function postStatus() {
            const txt = document.getElementById("statusText");
            if (txt.value.trim() !== "") {
                socket.emit('add_status', { token: currentToken, text: txt.value });
                txt.value = "";
            }
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
            const avatar = document.getElementById('inputAvatar').value;
            fetch('/update_profile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: currentToken, name: name, bio: bio, avatar: avatar })
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
            'text': data.get('text'),
            'time': datetime.now().strftime("%I:%M %p")
        }
        statuses.insert(0, st_obj)
        emit('new_status', st_obj, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
