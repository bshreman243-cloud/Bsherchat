import os
import secrets
from flask import Flask, render_template_string, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, disconnect

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bsher-secret-key-2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# مفتاح المشرف الثابت (الخاص بك يا بشر)
ADMIN_TOKEN = "bsher-admin-master-key-2026"

# تهيئة الـ 19 فتحة للمستخدمين بأكواد متجددة
slots = {
    0: {
        "type": "admin",
        "token": ADMIN_TOKEN,
        "name": "المشرف (بشر)",
        "bio": "مالك التطبيق 👑",
        "avatar": "https://cdn-icons-png.flaticon.com/512/3135/3135715.png",
        "online": False
    }
}

for i in range(1, 20):
    slots[i] = {
        "type": "user",
        "token": secrets.token_hex(6),  # كود حماية عشوائي متجدد
        "name": f"مستخدم #{i}",
        "bio": "أهلاً بي في bisher chat",
        "avatar": "https://cdn-icons-png.flaticon.com/512/149/149071.png",
        "online": False
    }

# البحث عن الفتحة ببيانات التوكن
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>bisher chat</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: system-ui, -apple-system, sans-serif; }
        body { background-color: #0b141a; color: #e9edef; display: flex; flex-direction: column; height: 100vh; }
        
        /* Header */
        .header { background-color: #202c33; padding: 12px 16px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #222d34; }
        .user-info { display: flex; align-items: center; gap: 12px; }
        .avatar { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; }
        .user-details h4 { font-size: 15px; color: #e9edef; }
        .user-details p { font-size: 12px; color: #8696a0; }
        
        /* Tabs */
        .nav-tabs { display: flex; background-color: #111b21; border-bottom: 1px solid #222d34; }
        .tab-btn { flex: 1; padding: 12px; text-align: center; background: none; border: none; color: #8696a0; font-weight: bold; font-size: 14px; cursor: pointer; border-bottom: 3px solid transparent; }
        .tab-btn.active { color: #00a884; border-bottom-color: #00a884; }
        
        /* Content Sections */
        .content { flex: 1; overflow-y: auto; display: none; padding: 12px; }
        .content.active { display: block; }
        
        /* Chat Box */
        .chat-box { display: flex; flex-direction: column; gap: 10px; min-height: 250px; }
        .msg { max-width: 80%; padding: 8px 12px; border-radius: 8px; font-size: 14px; line-height: 1.4; word-break: break-word; }
        .my-msg { background-color: #005c4b; align-self: flex-start; border-top-right-radius: 0; }
        .other-msg { background-color: #202c33; align-self: flex-end; border-top-left-radius: 0; }
        .sender-title { font-size: 11px; color: #53bdeb; font-weight: bold; margin-bottom: 2px; }
        
        /* Input Bar */
        .input-bar { background-color: #202c33; padding: 10px; display: flex; gap: 8px; align-items: center; }
        .input-bar input { flex: 1; background-color: #2a3942; border: none; padding: 12px; border-radius: 8px; color: white; outline: none; font-size: 14px; }
        .input-bar button { background-color: #00a884; color: #111b21; border: none; padding: 12px 18px; border-radius: 8px; font-weight: bold; cursor: pointer; }
        
        /* Admin Grid & QR Cards */
        .qr-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; }
        .qr-card { background-color: #202c33; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #222d34; }
        .qr-card img { margin: 10px 0; border: 4px solid white; border-radius: 8px; }
        .btn-kick { background-color: #ea868f; color: #842029; border: none; padding: 8px 16px; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top: 8px; width: 100%; }
        
        /* Profile Form */
        .profile-form { display: flex; flex-direction: column; gap: 12px; max-width: 400px; margin: 0 auto; background: #202c33; padding: 20px; border-radius: 10px; }
        .profile-form label { font-size: 12px; color: #8696a0; }
        .profile-form input { background: #2a3942; border: 1px solid #3b4a54; padding: 10px; border-radius: 6px; color: white; }
    </style>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
</head>
<body>

    <div class="header">
        <div class="user-info">
            <img src="{{ user_data.avatar }}" class="avatar" id="hdrAvatar">
            <div class="user-details">
                <h4 id="hdrName">{{ user_data.name }}</h4>
                <p id="hdrBio">{{ user_data.bio }}</p>
            </div>
        </div>
        <span style="color: #00a884; font-size: 12px;">🟢 متصل</span>
    </div>

    <div class="nav-tabs">
        <button class="tab-btn active" onclick="switchTab('chatTab')">💬 المحادثة</button>
        <button class="tab-btn" onclick="switchTab('profileTab')">👤 البروفايل</button>
        {% if user_data.type == 'admin' %}
        <button class="tab-btn" onclick="switchTab('adminTab')">👑 لوحة الأكواد (20)</button>
        {% endif %}
    </div>

    <!-- Tab 1: Chat -->
    <div id="chatTab" class="content active">
        <div class="chat-box" id="chatBox"></div>
    </div>

    <!-- Tab 2: Profile -->
    <div id="profileTab" class="content">
        <div class="profile-form">
            <label>الاسم الكامل</label>
            <input type="text" id="inputName" value="{{ user_data.name }}">
            
            <label>النبذة التعريفية (Bio)</label>
            <input type="text" id="inputBio" value="{{ user_data.bio }}">
            
            <label>رابط الصورة الشخصية</label>
            <input type="text" id="inputAvatar" value="{{ user_data.avatar }}">
            
            <button onclick="saveProfile()" style="background:#00a884; color:#111b21; border:none; padding:10px; border-radius:6px; font-weight:bold; cursor:pointer;">حفظ البيانات</button>
        </div>
    </div>

    <!-- Tab 3: Admin Panel (Visible to Admin only) -->
    {% if user_data.type == 'admin' %}
    <div id="adminTab" class="content">
        <h3 style="margin-bottom:15px; color:#00a884;">أكواد الـ QR والتحكم بالمستخدمين</h3>
        <div class="qr-grid">
            {% for sid, sinfo in all_slots.items() %}
            <div class="qr-card">
                <h4>{{ sinfo.name }} {% if sid == 0 %}(أنت - المالك){% endif %}</h4>
                <p style="font-size:11px; color:#8696a0;">{{ sinfo.bio }}</p>
                
                <!-- QR Code Image -->
                <img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data={{ base_url }}/?token={{ sinfo.token }}" width="140" height="140">
                
                <p style="font-size:10px; color:#00a884; word-break:break-all;">الرابط: {{ base_url }}/?token={{ sinfo.token }}</p>
                
                {% if sid != 0 %}
                <button class="btn-kick" onclick="kickUser({{ sid }})">🚫 طرد وتجديد الـ QR</button>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>
    {% endif %}

    <div class="input-bar" id="inputBar">
        <input type="text" id="msgText" placeholder="اكتب رسالتك...">
        <button onclick="sendMsg()">إرسال</button>
    </div>

    <script>
        const currentToken = "{{ user_data.token }}";
        const socket = io();

        socket.emit('join', { token: currentToken });

        socket.on('receive_message', function(data) {
            const chatBox = document.getElementById("chatBox");
            const div = document.createElement("div");
            
            if (data.token === currentToken) {
                div.className = "msg my-msg";
                div.innerText = data.text;
            } else {
                div.className = "msg other-msg";
                div.innerHTML = `<div class="sender-title">${data.name}</div>` + data.text;
            }
            chatBox.appendChild(div);
            chatBox.scrollTop = chatBox.scrollHeight;
        });

        socket.on('kicked', function() {
            alert('لقد تم طردك من قبل المشرف وتغيير كود الدخول الخاص بك!');
            window.location.href = "/invalid";
        });

        function sendMsg() {
            const input = document.getElementById("msgText");
            if (input.value.trim() !== "") {
                socket.emit('send_message', {
                    token: currentToken,
                    text: input.value
                });
                input.value = "";
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
            if (confirm('هل أنت تأكد من طرد هذا المستخدم وتوليد رمز QR جديد له؟')) {
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
        return "<h2 style='color:white; background:#111b21; padding:20px; text-align:center;'>❌ رابط الـ QR غير صالح أو تم إلغاؤه من قبل المشرف!</h2>", 403
        
    base_url = request.host_url.rstrip('/')
    return render_template_string(HTML_PAGE, user_data=user_data, all_slots=slots, base_url=base_url)

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
            # توليد كود عشوائي جديد تماماً للفتح المحددة
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
        emit('receive_message', {
            'token': user_data['token'],
            'name': user_data['name'],
            'text': data.get('text')
        }, room="global_chat")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
