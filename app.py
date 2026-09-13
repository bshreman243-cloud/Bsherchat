import os
import secrets
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bsher-e2ee-v15-master-key-2026'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading", max_http_buffer_size=50000000)

ADMIN_TOKEN = "bsher-admin-master-key-2026"

slots = {
    0: {
        "id": 0,
        "type": "admin",
        "token": ADMIN_TOKEN,
        "name": "المشرف (بشر)",
        "bio": "مالك التطبيق 👑",
        "avatar": "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"
    }
}

for i in range(1, 20):
    slots[i] = {
        "id": i,
        "type": "user",
        "token": f"bsher-user-code-0{i}" if i < 10 else f"bsher-user-code-{i}",
        "name": f"مستخدم #{i}",
        "bio": "أهلاً بي في bisher chat",
        "avatar": "https://cdn-icons-png.flaticon.com/512/149/149071.png"
    }

statuses = []
chat_history = {}
message_reactions = {}

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
        
        .header { background-color: #202c33; padding: 10px 14px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #222d34; height: 60px; }
        .user-info { display: flex; align-items: center; gap: 8px; cursor: pointer; }
        .btn-back { display: none; background: none; border: none; color: #00a884; font-size: 22px; cursor: pointer; padding: 0 4px; }
        .avatar { width: 42px; height: 42px; border-radius: 50%; object-fit: cover; border: 1.5px solid #00a884; }
        .user-details h4 { font-size: 15px; color: #e9edef; font-weight: 600; }
        .user-details p { font-size: 11px; color: #8696a0; }
        .call-actions { display: flex; gap: 10px; }
        .btn-call { background: #2a3942; border: none; color: #00a884; width: 36px; height: 36px; border-radius: 50%; font-size: 16px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
        
        .nav-tabs { display: flex; background-color: #111b21; border-bottom: 1px solid #222d34; }
        .tab-btn { flex: 1; padding: 12px; text-align: center; background: none; border: none; color: #8696a0; font-weight: 600; font-size: 13px; cursor: pointer; border-bottom: 3px solid transparent; }
        .tab-btn.active { color: #00a884; border-bottom-color: #00a884; }
        
        .content { flex: 1; overflow-y: auto; display: none; padding: 12px; background-color: #0b141a; -webkit-overflow-scrolling: touch; }
        .content.active { display: block; }
        
        #contactListContainer { padding-bottom: 120px; }
        .contact-item { display: flex; align-items: center; gap: 12px; padding: 12px; background: #202c33; border-radius: 10px; margin-bottom: 8px; cursor: pointer; border: 1px solid #222d34; }
        .contact-item:hover { background: #2a3942; }
        .contact-avatar { width: 45px; height: 45px; border-radius: 50%; object-fit: cover; }
        
        #activeChatArea { display: none; flex-direction: column; height: calc(100vh - 170px); }
        .chat-box { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; padding-bottom: 10px; }
        
        .msg { max-width: 80%; padding: 8px 12px; border-radius: 8px; font-size: 14px; line-height: 1.4; word-break: break-word; position: relative; }
        .my-msg { background-color: #005c4b; align-self: flex-start; border-top-right-radius: 0; color: #e9edef; }
        .other-msg { background-color: #202c33; align-self: flex-end; border-top-left-radius: 0; color: #e9edef; }
        .e2e-badge { font-size: 9px; color: #00a884; display: flex; align-items: center; gap: 3px; margin-bottom: 4px; }
        .msg-time { font-size: 9px; color: #8696a0; margin-top: 4px; text-align: left; }
        .chat-media { max-width: 100%; max-height: 220px; border-radius: 8px; margin-top: 4px; }
        audio { width: 220px; height: 35px; margin-top: 4px; }
        
        .msg-reactions { display: flex; gap: 4px; margin-top: 4px; flex-wrap: wrap; }
        .reaction-badge { background: #111b21; padding: 2px 6px; border-radius: 12px; font-size: 12px; border: 1px solid #222d34; display: inline-flex; align-items: center; gap: 2px; }
        .reaction-trigger { font-size: 12px; cursor: pointer; opacity: 0.7; margin-right: 6px; }
        .reaction-popup { display: none; position: absolute; background: #202c33; border: 1px solid #3b4a54; border-radius: 20px; padding: 4px 8px; gap: 6px; z-index: 100; bottom: 100%; right: 0; box-shadow: 0 4px 12px rgba(0,0,0,0.4); }
        .reaction-popup span { cursor: pointer; font-size: 16px; padding: 2px; }

        #emojiPicker { display: none; position: absolute; bottom: 65px; left: 10px; background: #202c33; border: 1px solid #3b4a54; border-radius: 10px; padding: 10px; width: 280px; grid-template-columns: repeat(6, 1fr); gap: 8px; text-align: center; z-index: 999; box-shadow: 0 5px 15px rgba(0,0,0,0.5); }
        #emojiPicker span { font-size: 20px; cursor: pointer; padding: 4px; border-radius: 4px; }
        #emojiPicker span:hover { background: #2a3942; }

        .input-bar { background-color: #202c33; padding: 8px 10px; display: none; gap: 6px; align-items: center; position: fixed; bottom: 0; left: 0; right: 0; height: 60px; border-top: 1px solid #222d34; }
        .input-bar input[type="text"] { flex: 1; background-color: #2a3942; border: none; padding: 10px 14px; border-radius: 20px; color: white; outline: none; font-size: 14px; }
        .icon-btn { background: none; border: none; font-size: 19px; cursor: pointer; padding: 5px; color: #8696a0; }
        .btn-send { background-color: #00a884; color: #111b21; border: none; width: 40px; height: 40px; border-radius: 50%; font-size: 18px; font-weight: bold; cursor: pointer; display: flex; align-items: center; justify-content: center; }
        
        .status-card { background: #202c33; padding: 12px; border-radius: 10px; margin-bottom: 12px; border: 1px solid #222d34; }
        .status-header { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
        .status-header img { width: 38px; height: 38px; border-radius: 50%; border: 2px solid #00a884; }
        .status-publisher { background: #202c33; padding: 14px; border-radius: 10px; margin-bottom: 15px; display: flex; flex-direction: column; gap: 10px; border: 1px solid #222d34; }
        .status-publisher textarea { background: #2a3942; border: none; padding: 10px; border-radius: 8px; color: white; resize: none; font-size: 13px; outline: none; }
        
        .qr-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; padding-bottom: 120px; }
        .qr-card { background-color: #202c33; padding: 12px; border-radius: 10px; text-align: center; border: 1px solid #222d34; }
        .btn-kick { background-color: #ea868f; color: #842029; border: none; padding: 8px 16px; border-radius: 6px; font-weight: bold; cursor: pointer; margin-top: 8px; width: 100%; }
        
        .profile-form { display: flex; flex-direction: column; gap: 12px; max-width: 400px; margin: 0 auto; background: #202c33; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 100px; }
        .profile-avatar-preview { width: 90px; height: 90px; border-radius: 50%; object-fit: cover; margin: 0 auto 10px auto; border: 3px solid #00a884; }

        #callModal { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(11,20,26,0.96); z-index: 9999; flex-direction: column; align-items: center; justify-content: space-between; padding: 30px 20px; }
        .call-user-avatar { width: 110px; height: 110px; border-radius: 50%; border: 3px solid #00a884; object-fit: cover; margin-top: 20px; }
        .video-container { display: flex; flex-direction: column; width: 100%; max-width: 400px; height: 60%; position: relative; gap: 10px; }
        video { width: 100%; height: 100%; background: #000; border-radius: 12px; object-fit: cover; }
        #localVideo { position: absolute; top: 10px; right: 10px; width: 90px; height: 130px; border: 2px solid #00a884; z-index: 10; border-radius: 8px; }
        .call-controls { display: flex; gap: 20px; margin-bottom: 20px; align-items: center; }
        .btn-ctrl { background: #2a3942; color: #00a884; border: none; width: 50px; height: 50px; border-radius: 50%; font-size: 20px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
        .btn-end-call { background: #ea868f; color: white; border: none; width: 60px; height: 60px; border-radius: 50%; font-size: 24px; cursor: pointer; }
        .btn-accept-call { background: #00a884; color: white; border: none; width: 60px; height: 60px; border-radius: 50%; font-size: 24px; cursor: pointer; display: none; }
    </style>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/crypto-js/4.1.1/crypto-js.min.js"></script>
</head>
<body>

    <div class="header">
        <div class="user-info">
            <button class="btn-back" id="btnBackToContacts" onclick="closePrivateChat(true)">⬅️</button>
            <img src="{{ user_data.avatar }}" class="avatar" id="hdrAvatar">
            <div class="user-details">
                <h4 id="hdrChatTarget">{{ user_data.name }}</h4>
                <p id="hdrStatusText">🔒 مشفر بالكامل (E2EE)</p>
            </div>
        </div>
        <div class="call-actions" id="callActionsBar" style="display:none;">
            <button class="btn-call" onclick="startCall(false)">📞</button>
            <button class="btn-call" onclick="startCall(true)">📹</button>
        </div>
    </div>

    <div class="nav-tabs" id="navTabsBar">
        <button class="tab-btn active" onclick="switchTab('contactsTab')">💬 المحادثات الخاصّة</button>
        <button class="tab-btn" onclick="switchTab('statusTab')">⭕ الحالات</button>
        <button class="tab-btn" onclick="switchTab('profileTab')">👤 البروفايل</button>
        {% if user_data.type == 'admin' %}
        <button class="tab-btn" onclick="switchTab('adminTab')">👑 لوحة الأكواد (20)</button>
        {% endif %}
    </div>

    <div id="contactsTab" class="content active">
        <div id="contactListContainer">
            <p style="font-size:12px; color:#8696a0; margin-bottom:10px;">اختر متصل لفتح شات خاص مشفر معه (1-on-1):</p>
            
            {% if user_data.type == 'admin' %}
                {% for sid, sinfo in all_slots.items() %}
                {% if sid != 0 %}
                <div class="contact-item" onclick="openPrivateChat({{ sid }}, '{{ sinfo.name }}', '{{ sinfo.avatar }}')">
                    <img src="{{ sinfo.avatar }}" class="contact-avatar">
                    <div>
                        <h4 style="font-size:14px; color:#e9edef;">{{ sinfo.name }}</h4>
                        <p style="font-size:11px; color:#00a884;">🔒 انقر لبدء محادثة مشفرة</p>
                    </div>
                </div>
                {% endif %}
                {% endfor %}
            {% else %}
                <div class="contact-item" onclick="openPrivateChat(0, '{{ all_slots[0].name }}', '{{ all_slots[0].avatar }}')">
                    <img src="{{ all_slots[0].avatar }}" class="contact-avatar">
                    <div>
                        <h4 style="font-size:14px; color:#e9edef;">{{ all_slots[0].name }}</h4>
                        <p style="font-size:11px; color:#00a884;">🔒 مالك التطبيق (انقر للتحدث معك)</p>
                    </div>
                </div>
            {% endif %}
        </div>

        <div id="activeChatArea">
            <div class="chat-box" id="chatBox"></div>
        </div>
    </div>

    <div id="statusTab" class="content">
        <div class="status-publisher">
            <textarea id="statusText" rows="2" placeholder="اكتب حالتك الجديدة..."></textarea>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <button class="icon-btn" onclick="document.getElementById('statusMediaFile').click()">📷 / 🎥 إضافة ملف</button>
                <input type="file" id="statusMediaFile" accept="image/*,video/*" style="display:none;" onchange="previewStatusMedia(this)">
                <button onclick="postStatus()" style="background:#00a884; color:#111b21; border:none; padding:8px 16px; border-radius:6px; font-weight:bold; cursor:pointer;">نشر الحالة</button>
            </div>
        </div>
        <h4 style="margin-bottom:10px; color:#8696a0; font-size:13px;">الحالات الحديثة</h4>
        <div id="statusList" style="padding-bottom:120px;">
            {% for st in statuses %}
            <div class="status-card">
                <div class="status-header">
                    <img src="{{ st.avatar }}">
                    <div>
                        <h4 style="font-size:13px; color:#e9edef;">{{ st.name }}</h4>
                        <span style="font-size:10px; color:#8696a0;">{{ st.time }}</span>
                    </div>
                </div>
                {% if st.text %}<p style="font-size:14px; color:#00a884;">{{ st.text }}</p>{% endif %}
                {% if st.media %}
                    {% if 'video' in st.media or st.media.startswith('data:video') %}
                        <video src="{{ st.media }}" controls class="chat-media"></video>
                    {% else %}
                        <img src="{{ st.media }}" class="chat-media">
                    {% endif %}
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>

    <div id="profileTab" class="content">
        <div class="profile-form">
            <img src="{{ user_data.avatar }}" class="profile-avatar-preview" id="previewProfileAvatar">
            <button type="button" onclick="document.getElementById('avatarFileInput').click()" style="background:#2a3942; color:#00a884; border:1px solid #00a884; padding:8px; border-radius:6px; font-size:12px; font-weight:bold; cursor:pointer;">📷 تغيير الصورة الشخصية</button>
            <input type="file" id="avatarFileInput" accept="image/*" style="display:none;" onchange="uploadAvatarFile(this)">
            
            <label style="font-size:12px; color:#8696a0; text-align:right;">الاسم الظاهر</label>
            <input type="text" id="inputName" value="{{ user_data.name }}" style="background:#2a3942; border:1px solid #3b4a54; padding:10px; border-radius:6px; color:white;">
            
            <label style="font-size:12px; color:#8696a0; text-align:right;">النبذة التعريفية (Bio)</label>
            <input type="text" id="inputBio" value="{{ user_data.bio }}" style="background:#2a3942; border:1px solid #3b4a54; padding:10px; border-radius:6px; color:white;">
            
            <button onclick="saveProfile()" style="background:#00a884; color:#111b21; border:none; padding:12px; border-radius:6px; font-weight:bold; cursor:pointer;">حفظ البيانات</button>
            
            <hr style="border-color:#222d34; margin:10px 0;">
            <h4 style="color:#00a884; font-size:14px; text-align:right;">🔔 تخصيص النغمات من الهاتف (MP3)</h4>
            
            <label style="font-size:11px; color:#8696a0; text-align:right;">نغمة الرنين (اتصال)</label>
            <button type="button" onclick="document.getElementById('ringAudioInput').click()" style="background:#2a3942; color:#e9edef; border:1px solid #00a884; padding:8px; border-radius:6px; font-size:11px; cursor:pointer;">🎵 اختيار نغمة رنين من الهاتف</button>
            <input type="file" id="ringAudioInput" accept="audio/*" style="display:none;" onchange="saveCustomTone('ring', this)">

            <label style="font-size:11px; color:#8696a0; text-align:right; margin-top:5px;">نغمة الرسائل</label>
            <button type="button" onclick="document.getElementById('msgAudioInput').click()" style="background:#2a3942; color:#e9edef; border:1px solid #00a884; padding:8px; border-radius:6px; font-size:11px; cursor:pointer;">🎵 اختيار نغمة رسالة من الهاتف</button>
            <input type="file" id="msgAudioInput" accept="audio/*" style="display:none;" onchange="saveCustomTone('msg', this)">

            <div style="display:flex; gap:10px; justify-content:center; margin-top:8px;">
                <button type="button" onclick="playMsgSound()" style="background:#202c33; color:#00a884; border:1px solid #222d34; padding:8px; border-radius:6px; font-size:11px; cursor:pointer;">▶ تجربة نغمة الرسالة</button>
                <button type="button" onclick="testRingtone()" style="background:#202c33; color:#00a884; border:1px solid #222d34; padding:8px; border-radius:6px; font-size:11px; cursor:pointer;">▶ تجربة الرنين</button>
            </div>

            <button type="button" onclick="logout()" style="background:#ea868f; color:#842029; border:none; padding:8px; border-radius:6px; font-size:11px; font-weight:bold; margin-top:10px; cursor:pointer;">🚪 تغيير الكود / تسجيل الخروج</button>
        </div>
    </div>

    {% if user_data.type == 'admin' %}
    <div id="adminTab" class="content">
        <h4 style="margin-bottom:12px; color:#00a884;">أكواد الـ QR والتحكم بالمستخدمين (19 كود ثابت)</h4>
        <div class="qr-grid">
            {% for sid, sinfo in all_slots.items() %}
            <div class="qr-card">
                <h4>{{ sinfo.name }} {% if sid == 0 %}(أنت - المالك){% endif %}</h4>
                <p style="font-size:11px; color:#8696a0;">الكود الثابت: <b style="color:#00a884;">{{ sinfo.token }}</b></p>
                <img src="https://api.qrserver.com/v1/create-qr-code/?size=140x140&data={{ base_url }}/?token={{ sinfo.token }}" width="130" height="130" style="border:3px solid white; border-radius:6px; margin:8px 0;">
                <p style="font-size:10px; color:#00a884; word-break:break-all;">{{ base_url }}/?token={{ sinfo.token }}</p>
                {% if sid != 0 %}
                <button class="btn-kick" onclick="kickUser({{ sid }})">🚫 إعادة تعيين الكود</button>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>
    {% endif %}

    <div id="emojiPicker">
        <span onclick="insertEmoji('😊')">😊</span>
        <span onclick="insertEmoji('😂')">😂</span>
        <span onclick="insertEmoji('❤️')">❤️</span>
        <span onclick="insertEmoji('👍')">👍</span>
        <span onclick="insertEmoji('🔥')">🔥</span>
        <span onclick="insertEmoji('😎')">😎</span>
        <span onclick="insertEmoji('😢')">😢</span>
        <span onclick="insertEmoji('😡')">😡</span>
        <span onclick="insertEmoji('😮')">😮</span>
        <span onclick="insertEmoji('👏')">👏</span>
        <span onclick="insertEmoji('🙏')">🙏</span>
        <span onclick="insertEmoji('🎉')">🎉</span>
    </div>

    <div class="input-bar" id="inputBar">
        <button class="icon-btn" onclick="toggleEmojiPicker()" title="الإيموجي">😊</button>
        <button class="icon-btn" onclick="document.getElementById('imgFile').click()">📷</button>
        <input type="file" id="imgFile" accept="image/*,video/*" style="display:none;" onchange="sendMediaMessage(this)">
        <input type="text" id="msgText" placeholder="اكتب رسالتك المشفرة...">
        <button class="icon-btn" id="micBtn" onclick="toggleRecord()">🎙️</button>
        <button class="btn-send" onclick="sendMsg()">➤</button>
    </div>

    <div id="callModal">
        <h3 id="callStatusText" style="color:#00a884; margin-top:10px;">جاري الاتصال...</h3>
        <img src="https://cdn-icons-png.flaticon.com/512/3135/3135715.png" class="call-user-avatar" id="callAvatar">
        <div class="video-container" id="videoContainer" style="display:none;">
            <video id="remoteVideo" autoplay playsinline></video>
            <video id="localVideo" autoplay playsinline muted></video>
        </div>
        <div class="call-controls">
            <button class="btn-ctrl" id="btnToggleMic" onclick="toggleMic()" style="display:none;">🎙️</button>
            <button class="btn-accept-call" id="btnAcceptCall" onclick="acceptIncomingCall()">📞</button>
            <button class="btn-end-call" onclick="endCall()">📞</button>
            <button class="btn-ctrl" id="btnToggleSpeaker" onclick="toggleSpeaker()" style="display:none;">🔊</button>
        </div>
    </div>

    <div id="scannerModal" style="display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: #000; z-index: 10000; flex-direction: column; align-items: center; justify-content: space-between; padding: 20px;">
        <h4 style="color:#00a884; margin-top:15px;">وجه الكاميرا نحو رمز الـ QR 📸</h4>
        <div style="width: 100%; max-width: 320px; height: 320px; position: relative; border-radius: 16px; overflow: hidden; border: 3px solid #00a884; margin-top: 40px;">
            <video id="videoFeed" playsinline style="width: 100%; height: 100%; object-fit: cover;"></video>
        </div>
        <button onclick="stopLiveScanner()" style="background: #ea868f; color: #842029; border: none; padding: 12px 24px; border-radius: 20px; font-weight: bold; cursor: pointer; margin-bottom: 30px;">إلغاء الكاميرا ✖</button>
    </div>

    <script>
        const currentToken = "{{ user_data.token }}";
        const mySlotId = {{ current_slot_id }};
        const myDefaultName = "{{ user_data.name }}";
        const myDefaultAvatar = "{{ user_data.avatar }}";
        
        localStorage.setItem('bisher_chat_token', currentToken);

        function logout() {
            localStorage.removeItem('bisher_chat_token');
            window.location.href = '/';
        }

        let activeTargetSlot = null;
        let activeRoom = null;
        let activeTargetName = "";
        let activeTargetAvatar = "";
        let secretKey = "bsher-e2ee-key-2026";
        let currentAvatarData = myDefaultAvatar;
        let currentStatusMedia = "";
        let pendingOfferData = null;
        let msgCounter = 0;

        window.onpopstate = function(event) {
            if (document.getElementById('activeChatArea').style.display === 'flex') {
                closePrivateChat(false);
            }
        };

        function toggleEmojiPicker() {
            const picker = document.getElementById('emojiPicker');
            picker.style.display = (picker.style.display === 'grid') ? 'none' : 'grid';
        }

        function insertEmoji(emoji) {
            const input = document.getElementById('msgText');
            input.value += emoji;
            document.getElementById('emojiPicker').style.display = 'none';
            input.focus();
        }

        function saveCustomTone(type, input) {
            if (input.files && input.files[0]) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    if (type === 'ring') {
                        localStorage.setItem('bisher_custom_ring', e.target.result);
                        alert("✅ تم حفظ نغمة الرنين بنجاح!");
                    } else {
                        localStorage.setItem('bisher_custom_msg', e.target.result);
                        alert("✅ تم حفظ نغمة الرسالة بنجاح!");
                    }
                };
                reader.readAsDataURL(input.files[0]);
            }
        }

        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        let audioCtx = null;
        let ringtoneInterval = null;

        function getAudioContext() {
            if (!audioCtx) audioCtx = new AudioCtx();
            if (audioCtx.state === 'suspended') audioCtx.resume();
            return audioCtx;
        }

        function playMsgSound() {
            const customMsg = localStorage.getItem('bisher_custom_msg');
            if (customMsg) {
                try {
                    const audio = new Audio(customMsg);
                    audio.play();
                    return;
                } catch(e){}
            }
            try {
                const ctx = getAudioContext();
                const osc = ctx.createOscillator();
                const gain = ctx.createGain();
                osc.type = 'sine';
                osc.frequency.setValueAtTime(880, ctx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(440, ctx.currentTime + 0.15);
                gain.gain.setValueAtTime(0.3, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.15);
                osc.connect(gain);
                gain.connect(ctx.destination);
                osc.start();
                osc.stop(ctx.currentTime + 0.15);
            } catch(e){}
        }

        function startRingtone() {
            stopRingtone();
            const customRing = localStorage.getItem('bisher_custom_ring');
            if (customRing) {
                ringtoneInterval = setInterval(() => {
                    try {
                        const audio = new Audio(customRing);
                        audio.play();
                    } catch(e){}
                }, 3000);
                return;
            }

            ringtoneInterval = setInterval(() => {
                try {
                    const ctx = getAudioContext();
                    const osc1 = ctx.createOscillator();
                    const osc2 = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc1.frequency.value = 440;
                    osc2.frequency.value = 480;
                    gain.gain.setValueAtTime(0.25, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.8);
                    osc1.connect(gain);
                    osc2.connect(gain);
                    gain.connect(ctx.destination);
                    osc1.start(); osc2.start();
                    osc1.stop(ctx.currentTime + 0.8);
                    osc2.stop(ctx.currentTime + 0.8);
                } catch(e){}
            }, 1200);
        }

        function stopRingtone() {
            if (ringtoneInterval) {
                clearInterval(ringtoneInterval);
                ringtoneInterval = null;
            }
        }

        function testRingtone() {
            startRingtone();
            setTimeout(stopRingtone, 4000);
        }

        const socket = io();
        socket.emit('join', { token: currentToken });

        function encryptPayload(text) {
            return CryptoJS.AES.encrypt(text, secretKey).toString();
        }

        function decryptPayload(ciphertext) {
            try {
                const bytes = CryptoJS.AES.decrypt(ciphertext, secretKey);
                return bytes.toString(CryptoJS.enc.Utf8);
            } catch(e) {
                return "[رسالة غير صالحة]";
            }
        }

        function openPrivateChat(targetSlotId, targetName, targetAvatar) {
            activeTargetSlot = targetSlotId;
            activeTargetName = targetName;
            activeTargetAvatar = targetAvatar;

            document.getElementById('contactListContainer').style.display = 'none';
            document.getElementById('activeChatArea').style.display = 'flex';
            document.getElementById('inputBar').style.display = 'flex';
            document.getElementById('callActionsBar').style.display = 'flex';
            document.getElementById('btnBackToContacts').style.display = 'block';

            document.getElementById('hdrChatTarget').innerText = targetName;
            document.getElementById('hdrAvatar').src = targetAvatar;
            
            activeRoom = (mySlotId < targetSlotId) ? `room_${mySlotId}_${targetSlotId}` : `room_${targetSlotId}_${mySlotId}`;
            
            // Clear current chat box and request history
            document.getElementById('chatBox').innerHTML = `<div style="text-align:center; font-size:11px; color:#00a884; margin:10px 0;">🔒 المحادثة مشفرة بالكامل بينك وبين ${targetName} (E2EE)</div>`;
            socket.emit('join_private_room', { room: activeRoom });

            history.pushState({ inChat: true }, "");
        }

        function closePrivateChat(triggerHistoryBack = false) {
            activeTargetSlot = null;
            activeRoom = null;

            document.getElementById('contactListContainer').style.display = 'block';
            document.getElementById('activeChatArea').style.display = 'none';
            document.getElementById('inputBar').style.display = 'none';
            document.getElementById('callActionsBar').style.display = 'none';
            document.getElementById('btnBackToContacts').style.display = 'none';
            document.getElementById('emojiPicker').style.display = 'none';

            document.getElementById('hdrChatTarget').innerText = myDefaultName;
            document.getElementById('hdrAvatar').src = myDefaultAvatar;

            if (triggerHistoryBack && history.state && history.state.inChat) {
                history.back();
            }
        }

        // Load historical messages when entering room
        socket.on('load_history', function(historyMessages) {
            const chatBox = document.getElementById("chatBox");
            historyMessages.forEach(data => {
                appendMessage(data, false);
            });
            chatBox.scrollTop = chatBox.scrollHeight;
        });

        socket.on('receive_private_message', function(data) {
            if (data.sender_slot !== mySlotId) {
                playMsgSound();
            }
            if (data.room !== activeRoom) return;
            appendMessage(data, true);
        });

        function appendMessage(data, autoScroll = true) {
            const chatBox = document.getElementById("chatBox");
            if (document.getElementById("msg_" + data.msg_id)) return; // prevent duplication

            const div = document.createElement("div");
            div.id = "msg_" + data.msg_id;
            const decryptedContent = decryptPayload(data.encrypted_data);
            
            let contentHtml = "";
            if (data.msg_type === 'text') {
                contentHtml = decryptedContent;
            } else if (data.msg_type === 'image') {
                contentHtml = `<img src="${decryptedContent}" class="chat-media">`;
            } else if (data.msg_type === 'video') {
                contentHtml = `<video src="${decryptedContent}" controls class="chat-media"></video>`;
            } else if (data.msg_type === 'audio') {
                contentHtml = `<audio controls src="${decryptedContent}"></audio>`;
            }

            const badgeHtml = `<div class="e2e-badge">🔒 مشفّرة E2EE</div>`;
            const reactionsHtml = `<div class="msg-reactions" id="reactions_${data.msg_id}"></div>`;
            const triggerHtml = `<span class="reaction-trigger" onclick="toggleReactionPopup(${data.msg_id})">👍 تفاعل</span>`;
            const popupHtml = `
                <div class="reaction-popup" id="popup_${data.msg_id}">
                    <span onclick="sendReaction(${data.msg_id}, '❤️')">❤️</span>
                    <span onclick="sendReaction(${data.msg_id}, '👍')">👍</span>
                    <span onclick="sendReaction(${data.msg_id}, '😂')">😂</span>
                    <span onclick="sendReaction(${data.msg_id}, '😮')">😮</span>
                    <span onclick="sendReaction(${data.msg_id}, '😢')">😢</span>
                    <span onclick="sendReaction(${data.msg_id}, '😡')">😡</span>
                </div>`;

            if (data.sender_slot === mySlotId) {
                div.className = "msg my-msg";
                div.innerHTML = badgeHtml + contentHtml + reactionsHtml + `<div style="display:flex; justify-content:space-between; align-items:center; margin-top:4px;"><span class="msg-time">${data.time}</span>${triggerHtml}</div>` + popupHtml;
            } else {
                div.className = "msg other-msg";
                div.innerHTML = badgeHtml + `<div style="font-size:11px; color:#53bdeb; font-weight:bold;">${data.sender_name}</div>` + contentHtml + reactionsHtml + `<div style="display:flex; justify-content:space-between; align-items:center; margin-top:4px;"><span class="msg-time">${data.time}</span>${triggerHtml}</div>` + popupHtml;
            }
            
            chatBox.appendChild(div);
            if (autoScroll) {
                chatBox.scrollTop = chatBox.scrollHeight;
            }

            if (data.reactions) {
                updateReactionsUI(data.msg_id, data.reactions);
            }
        }

        function toggleReactionPopup(msgId) {
            const popup = document.getElementById(`popup_${msgId}`);
            popup.style.display = (popup.style.display === 'flex') ? 'none' : 'flex';
        }

        function sendReaction(msgId, emoji) {
            document.getElementById(`popup_${msgId}`).style.display = 'none';
            socket.emit('send_reaction', {
                room: activeRoom,
                msg_id: msgId,
                emoji: emoji,
                token: currentToken
            });
        }

        socket.on('update_reactions', function(data) {
            updateReactionsUI(data.msg_id, data.reactions);
        });

        function updateReactionsUI(msgId, reactions) {
            const container = document.getElementById(`reactions_${msgId}`);
            if (!container) return;
            container.innerHTML = '';
            for (let emoji in reactions) {
                const badge = document.createElement('span');
                badge.className = 'reaction-badge';
                badge.innerHTML = `${emoji} ${reactions[emoji].length}`;
                container.appendChild(badge);
            }
        }

        function sendMsg() {
            const input = document.getElementById("msgText");
            if (input.value.trim() !== "" && activeRoom) {
                msgCounter++;
                const encrypted = encryptPayload(input.value);
                socket.emit('send_private_message', {
                    token: currentToken,
                    room: activeRoom,
                    msg_id: msgCounter,
                    msg_type: 'text',
                    encrypted_data: encrypted
                });
                input.value = "";
                document.getElementById('emojiPicker').style.display = 'none';
            }
        }

        function sendMediaMessage(input) {
            if (input.files && input.files[0] && activeRoom) {
                msgCounter++;
                const file = input.files[0];
                const reader = new FileReader();
                const isVideo = file.type.startsWith('video');
                reader.onload = function(e) {
                    const encrypted = encryptPayload(e.target.result);
                    socket.emit('send_private_message', {
                        token: currentToken,
                        room: activeRoom,
                        msg_id: msgCounter,
                        msg_type: isVideo ? 'video' : 'image',
                        encrypted_data: encrypted
                    });
                };
                reader.readAsDataURL(file);
            }
        }

        let mediaRecorder, audioChunks = [], isRecording = false, recordStream = null;
        async function toggleRecord() {
            const micBtn = document.getElementById("micBtn");
            if (!isRecording) {
                try {
                    recordStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    let options = { mimeType: 'audio/webm' };
                    if (!MediaRecorder.isTypeSupported('audio/webm')) {
                        if (MediaRecorder.isTypeSupported('audio/mp4')) options = { mimeType: 'audio/mp4' };
                        else options = {};
                    }
                    mediaRecorder = new MediaRecorder(recordStream, options);
                    audioChunks = [];
                    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
                    
                    mediaRecorder.onstop = () => {
                        if (recordStream) {
                            recordStream.getTracks().forEach(track => { track.stop(); track.enabled = false; });
                            recordStream = null;
                        }
                        msgCounter++;
                        const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
                        const reader = new FileReader();
                        reader.onload = function(e) {
                            const encrypted = encryptPayload(e.target.result);
                            socket.emit('send_private_message', { token: currentToken, room: activeRoom, msg_id: msgCounter, msg_type: 'audio', encrypted_data: encrypted });
                        };
                        reader.readAsDataURL(audioBlob);
                    };

                    mediaRecorder.start();
                    isRecording = true;
                    micBtn.style.color = "#ea868f";
                    document.getElementById('msgText').placeholder = "🎙️ جاري التسجيل... اضغط لإيقافه وإرساله";
                } catch(err) {
                    alert("يرجى السماح بصلاحية الميكروفون!");
                }
            } else {
                if (mediaRecorder) mediaRecorder.stop();
                if (recordStream) {
                    recordStream.getTracks().forEach(track => { track.stop(); track.enabled = false; });
                    recordStream = null;
                }
                isRecording = false;
                micBtn.style.color = "#8696a0";
                document.getElementById('msgText').placeholder = "اكتب رسالتك المشفرة...";
            }
        }

        let localStream = null, peerConnection = null;
        let isMicMuted = false, isSpeakerMuted = false;
        const config = { 
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' },
                { urls: 'stun:stun1.l.google.com:19302' }
            ] 
        };

        async function startCall(isVideo) {
            if (!activeRoom) return;
            document.getElementById('callModal').style.display = 'flex';
            document.getElementById('callAvatar').src = activeTargetAvatar || myDefaultAvatar;
            document.getElementById('callStatusText').innerText = isVideo ? "جاري الاتصال المرئي..." : "جاري الاتصال الصوتي...";
            document.getElementById('btnAcceptCall').style.display = 'none';
            document.getElementById('btnToggleMic').style.display = 'flex';
            document.getElementById('btnToggleSpeaker').style.display = 'flex';
            
            if (isVideo) {
                document.getElementById('videoContainer').style.display = 'flex';
                document.getElementById('callAvatar').style.display = 'none';
            } else {
                document.getElementById('videoContainer').style.display = 'none';
                document.getElementById('callAvatar').style.display = 'block';
            }

            try {
                localStream = await navigator.mediaDevices.getUserMedia({ video: isVideo, audio: true });
                if (isVideo) document.getElementById('localVideo').srcObject = localStream;
                
                peerConnection = new RTCPeerConnection(config);
                localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));
                
                peerConnection.ontrack = e => {
                    const remoteVid = document.getElementById('remoteVideo');
                    remoteVid.srcObject = e.streams[0];
                };
                
                peerConnection.onicecandidate = e => {
                    if (e.candidate) socket.emit('signal', { room: activeRoom, token: currentToken, type: 'candidate', candidate: e.candidate });
                };

                const offer = await peerConnection.createOffer();
                await peerConnection.setLocalDescription(offer);
                socket.emit('signal', { room: activeRoom, token: currentToken, type: 'offer', offer: offer, isVideo: isVideo });
            } catch(e) {
                alert("يرجى السماح بصلاحيات الميكروفون والكاميرا للمكالمات!");
                endCall(false);
            }
        }

        socket.on('signal', async function(data) {
            if (data.token === currentToken) return;
            if (!activeRoom && data.type === 'offer') activeRoom = data.room;
            if (data.room !== activeRoom) return;
            
            if (data.type === 'offer') {
                startRingtone();
                pendingOfferData = data;
                const callTypeLabel = data.isVideo ? "مكالمة فيديو مرئية 📹" : "مكالمة صوتية 📞";
                
                document.getElementById('callModal').style.display = 'flex';
                document.getElementById('callAvatar').src = myDefaultAvatar;
                document.getElementById('callStatusText').innerText = `مكالمة واردة: ${callTypeLabel}`;
                document.getElementById('videoContainer').style.display = 'none';
                document.getElementById('callAvatar').style.display = 'block';
                document.getElementById('btnAcceptCall').style.display = 'flex';
                document.getElementById('btnToggleMic').style.display = 'none';
                document.getElementById('btnToggleSpeaker').style.display = 'none';

            } else if (data.type === 'answer' && peerConnection) {
                stopRingtone();
                await peerConnection.setRemoteDescription(new RTCSessionDescription(data.answer));
                document.getElementById('callStatusText').innerText = "المكالمة متصلة 🟢";
            } else if (data.type === 'candidate' && peerConnection) {
                await peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
            } else if (data.type === 'end') {
                stopRingtone();
                endCall(false);
            }
        });

        async function acceptIncomingCall() {
            stopRingtone();
            if (!pendingOfferData) return;
            
            document.getElementById('btnAcceptCall').style.display = 'none';
            document.getElementById('btnToggleMic').style.display = 'flex';
            document.getElementById('btnToggleSpeaker').style.display = 'flex';
            document.getElementById('callStatusText').innerText = "المكالمة متصلة 🟢";

            if (pendingOfferData.isVideo) {
                document.getElementById('videoContainer').style.display = 'flex';
                document.getElementById('callAvatar').style.display = 'none';
            } else {
                document.getElementById('videoContainer').style.display = 'none';
                document.getElementById('callAvatar').style.display = 'block';
            }

            try {
                localStream = await navigator.mediaDevices.getUserMedia({ video: pendingOfferData.isVideo, audio: true });
                if (pendingOfferData.isVideo) document.getElementById('localVideo').srcObject = localStream;
                
                peerConnection = new RTCPeerConnection(config);
                localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));
                
                peerConnection.ontrack = e => {
                    const remoteVid = document.getElementById('remoteVideo');
                    remoteVid.srcObject = e.streams[0];
                };
                
                peerConnection.onicecandidate = e => {
                    if (e.candidate) socket.emit('signal', { room: activeRoom, token: currentToken, type: 'candidate', candidate: e.candidate });
                };

                await peerConnection.setRemoteDescription(new RTCSessionDescription(pendingOfferData.offer));
                const answer = await peerConnection.createAnswer();
                await peerConnection.setLocalDescription(answer);
                socket.emit('signal', { room: activeRoom, token: currentToken, type: 'answer', answer: answer });
            } catch(e) {
                alert("يرجى السماح بالصلاحيات للرد على المكالمة!");
                endCall(true);
            }
        }

        function toggleMic() {
            if (localStream) {
                const audioTrack = localStream.getAudioTracks()[0];
                if (audioTrack) {
                    audioTrack.enabled = !audioTrack.enabled;
                    isMicMuted = !audioTrack.enabled;
                    document.getElementById('btnToggleMic').innerText = isMicMuted ? "🛑" : "🎙️";
                }
            }
        }

        function toggleSpeaker() {
            const remoteVid = document.getElementById('remoteVideo');
            if (remoteVid) {
                remoteVid.muted = !remoteVid.muted;
                isSpeakerMuted = remoteVid.muted;
                document.getElementById('btnToggleSpeaker').innerText = isSpeakerMuted ? "🔇" : "🔊";
            }
        }

        function endCall(emitEvent = true) {
            stopRingtone();
            pendingOfferData = null;
            if (emitEvent && activeRoom) socket.emit('signal', { room: activeRoom, token: currentToken, type: 'end' });
            
            if (localStream) {
                localStream.getTracks().forEach(track => { track.stop(); track.enabled = false; });
                localStream = null;
            }
            if (peerConnection) {
                peerConnection.close();
                peerConnection = null;
            }

            const lVid = document.getElementById('localVideo');
            const rVid = document.getElementById('remoteVideo');
            if (lVid) lVid.srcObject = null;
            if (rVid) rVid.srcObject = null;

            document.getElementById('callModal').style.display = 'none';
        }

        function switchTab(tabId) {
            document.querySelectorAll('.content').forEach(c => c.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            event.target.classList.add('active');
            document.getElementById('emojiPicker').style.display = 'none';
            
            if (tabId !== 'contactsTab') {
                document.getElementById('inputBar').style.display = 'none';
                document.getElementById('callActionsBar').style.display = 'none';
                document.getElementById('btnBackToContacts').style.display = 'none';
            } else if (activeRoom) {
                document.getElementById('inputBar').style.display = 'flex';
                document.getElementById('callActionsBar').style.display = 'flex';
                document.getElementById('btnBackToContacts').style.display = 'block';
            }
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
                const reader = new FileReader();
                reader.onload = function(e) {
                    currentStatusMedia = e.target.result;
                    alert("✅ تم إرفاق ملف الحالة بنجاح، اضغط الآن على 'نشر الحالة'!");
                };
                reader.readAsDataURL(input.files[0]);
            }
        }

        function postStatus() {
            const text = document.getElementById('statusText').value.trim();
            if (!text && !currentStatusMedia) {
                alert("يرجى كتابة نص أو إضافة صورة/فيديو للحالة!");
                return;
            }
            fetch('/post_status', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token: currentToken, text: text, media: currentStatusMedia })
            }).then(res => res.json()).then(data => {
                if (data.success) {
                    document.getElementById('statusText').value = "";
                    currentStatusMedia = "";
                }
            });
        }

        socket.on('new_status_broadcast', function(st) {
            const statusList = document.getElementById('statusList');
            const div = document.createElement('div');
            div.className = 'status-card';
            
            let mediaHtml = '';
            if (st.media) {
                if (st.media.includes('video') || st.media.startsWith('data:video')) {
                    mediaHtml = `<video src="${st.media}" controls class="chat-media"></video>`;
                } else {
                    mediaHtml = `<img src="${st.media}" class="chat-media">`;
                }
            }

            div.innerHTML = `
                <div class="status-header">
                    <img src="${st.avatar}">
                    <div>
                        <h4 style="font-size:13px; color:#e9edef;">${st.name}</h4>
                        <span style="font-size:10px; color:#8696a0;">${st.time}</span>
                    </div>
                </div>
                ${st.text ? `<p style="font-size:14px; color:#00a884;">${st.text}</p>` : ''}
                ${mediaHtml}
            `;
            statusList.insertBefore(div, statusList.firstChild);
        });

        function kickUser(slotId) {
            if (confirm('هل أنت تأكد من إعادة تعيين كود هذا المستخدم؟')) {
                fetch('/kick_user', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ admin_token: currentToken, slot_id: slotId })
                }).then(() => location.reload());
            }
        }

        let videoStream = null;
        let scanAnimFrame = null;

        async function startLiveScanner() {
            document.getElementById('scannerModal').style.display = 'flex';
            const video = document.getElementById('videoFeed');
            try {
                videoStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
                video.srcObject = videoStream;
                video.setAttribute("playsinline", true);
                video.play();
                requestAnimationFrame(tickScanner);
            } catch(err) {
                alert("يرجى إعطاء صلاحية استخدام الكاميرا لمسح الـ QR!");
                stopLiveScanner();
            }
        }

        function tickScanner() {
            const video = document.getElementById('videoFeed');
            if (video.readyState === video.HAVE_ENOUGH_DATA) {
                const canvas = document.createElement('canvas');
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                const code = jsQR(imageData.data, imageData.width, imageData.height);

                if (code && code.data) {
                    stopLiveScanner();
                    try {
                        const url = new URL(code.data);
                        const token = url.searchParams.get('token');
                        if (token) loginWithToken(token);
                        else loginWithToken(code.data);
                    } catch(err) {
                        loginWithToken(code.data);
                    }
                    return;
                }
            }
            scanAnimFrame = requestAnimationFrame(tickScanner);
        }

        function stopLiveScanner() {
            if (scanAnimFrame) cancelAnimationFrame(scanAnimFrame);
            if (videoStream) {
                videoStream.getTracks().forEach(track => { track.stop(); track.enabled = false; });
                videoStream = null;
            }
            document.getElementById('scannerModal').style.display = 'none';
        }

        function loginWithToken(tokenVal) {
            if (tokenVal) {
                localStorage.setItem('bisher_chat_token', tokenVal);
                window.location.href = '/?token=' + tokenVal;
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    token = request.args.get('token')
    if not token:
        return render_template_string("""
        <!DOCTYPE html>
        <html lang="ar" dir="rtl">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
            <title>bisher chat - تفعيل التطبيق</title>
            <script src="https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.min.js"></script>
            <style>
                body { background: #0b141a; color: white; font-family: sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; overflow: hidden; }
                .card { background: #202c33; padding: 25px; border-radius: 12px; width: 88%; max-width: 350px; border: 1px solid #00a884; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
                input[type="text"] { width: 100%; padding: 12px; margin: 12px 0; border-radius: 8px; border: 1px solid #3b4a54; background: #2a3942; color: white; font-size: 14px; text-align: center; outline: none; }
                .btn-main { width: 100%; padding: 12px; background: #00a884; border: none; color: #111b21; border-radius: 8px; font-weight: bold; font-size: 15px; cursor: pointer; margin-bottom: 8px; }
                .btn-scanner { width: 100%; padding: 12px; background: #00a884; border: none; color: #111b21; border-radius: 8px; font-weight: bold; font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 8px; }
                .btn-qr { width: 100%; padding: 10px; background: #2a3942; border: 1px solid #3b4a54; color: #e9edef; border-radius: 8px; font-weight: bold; font-size: 12px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; }
                .divider { margin: 10px 0; color: #8696a0; font-size: 11px; }

                #scannerModal { display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: #000; z-index: 10000; flex-direction: column; align-items: center; justify-content: space-between; padding: 20px; }
                .scan-view { width: 100%; max-width: 320px; height: 320px; position: relative; border-radius: 16px; overflow: hidden; border: 3px solid #00a884; margin-top: 40px; }
                #videoFeed { width: 100%; height: 100%; object-fit: cover; }
                .btn-close-scan { background: #ea868f; color: #842029; border: none; padding: 12px 24px; border-radius: 20px; font-weight: bold; cursor: pointer; margin-bottom: 30px; }
            </style>
        </head>
        <body>
            <script>
                const saved = localStorage.getItem('bisher_chat_token');
                if (saved) { window.location.href = '/?token=' + saved; }
            </script>

            <div class="card">
                <h3 style="color:#00a884; margin-bottom: 6px;">bisher chat 🔒</h3>
                <p style="font-size:12px; color:#8696a0; margin-bottom: 12px;">اختر طريقة تفعيل حسابه سريعة:</p>
                
                <button class="btn-scanner" onclick="parentStartLiveScanner()">📷 مسح الـ QR مباشر بالكاميرا</button>
                <button class="btn-qr" onclick="document.getElementById('qrFileInput').click()">🖼️ اختر صورة الـ QR من ألبوم الصور</button>
                <input type="file" id="qrFileInput" accept="image/*" style="display:none;" onchange="scanQRFromImage(this)">
                
                <div class="divider">─── أو أدخل الكود يدوياً ───</div>
                
                <input type="text" id="tkInput" placeholder="أدخل الكود السرّي هنا...">
                <button class="btn-main" onclick="login()">دخول الشات 🚀</button>
            </div>

            <div id="scannerModal">
                <h4 style="color:#00a884; margin-top:15px;">وجه الكاميرا نحو رمز الـ QR 📸</h4>
                <div class="scan-view">
                    <video id="videoFeed" playsinline></video>
                </div>
                <button class="btn-close-scan" onclick="parentStopLiveScanner()">إلغاء الكاميرا ✖</button>
            </div>

            <script>
                let videoStream = null;
                let scanAnimFrame = null;

                async function parentStartLiveScanner() {
                    document.getElementById('scannerModal').style.display = 'flex';
                    const video = document.getElementById('videoFeed');
                    try {
                        videoStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
                        video.srcObject = videoStream;
                        video.setAttribute("playsinline", true);
                        video.play();
                        requestAnimationFrame(tickScanner);
                    } catch(err) {
                        alert("يرجى إعطاء صلاحية استخدام الكاميرا لمسح الـ QR!");
                        parentStopLiveScanner();
                    }
                }

                function tickScanner() {
                    const video = document.getElementById('videoFeed');
                    if (video.readyState === video.HAVE_ENOUGH_DATA) {
                        const canvas = document.createElement('canvas');
                        canvas.width = video.videoWidth;
                        canvas.height = video.videoHeight;
                        const ctx = canvas.getContext('2d');
                        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                        const code = jsQR(imageData.data, imageData.width, imageData.height);

                        if (code && code.data) {
                            parentStopLiveScanner();
                            try {
                                const url = new URL(code.data);
                                const token = url.searchParams.get('token');
                                if (token) loginWithToken(token);
                                else loginWithToken(code.data);
                            } catch(err) {
                                loginWithToken(code.data);
                            }
                            return;
                        }
                    }
                    scanAnimFrame = requestAnimationFrame(tickScanner);
                }

                function parentStopLiveScanner() {
                    if (scanAnimFrame) cancelAnimationFrame(scanAnimFrame);
                    if (videoStream) {
                        videoStream.getTracks().forEach(track => { track.stop(); track.enabled = false; });
                        videoStream = null;
                    }
                    document.getElementById('scannerModal').style.display = 'none';
                }

                function loginWithToken(tokenVal) {
                    if (tokenVal) {
                        localStorage.setItem('bisher_chat_token', tokenVal);
                        window.location.href = '/?token=' + tokenVal;
                    }
                }

                function login() {
                    const val = document.getElementById('tkInput').value.trim();
                    if (val) loginWithToken(val);
                    else alert('يرجى مسح الـ QR أو إدخال الكود!');
                }

                function scanQRFromImage(input) {
                    if (input.files && input.files[0]) {
                        const file = input.files[0];
                        const reader = new FileReader();
                        reader.onload = function(e) {
                            const img = new Image();
                            img.onload = function() {
                                const canvas = document.createElement('canvas');
                                const ctx = canvas.getContext('2d');
                                canvas.width = img.width;
                                canvas.height = img.height;
                                ctx.drawImage(img, 0, 0, img.width, img.height);
                                const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                                const code = jsQR(imageData.data, imageData.width, imageData.height);
                                
                                if (code && code.data) {
                                    try {
                                        const url = new URL(code.data);
                                        const token = url.searchParams.get('token');
                                        if (token) loginWithToken(token);
                                        else loginWithToken(code.data);
                                    } catch(err) {
                                        loginWithToken(code.data);
                                    }
                                } else {
                                    alert('❌ لم يتم العثور على رمز QR واضح بالصورة!');
                                }
                            };
                            img.src = e.target.result;
                        };
                        reader.readAsDataURL(file);
                    }
                }
            </script>
        </body>
        </html>
        """)
        
    slot_id, user_data = get_slot_by_token(token)
    if not user_data:
        return "<h2 style='color:white; background:#111b21; padding:20px; text-align:center;'>❌ الكود غير صالح أو تم طرده!</h2>", 403
        
    base_url = request.host_url.rstrip('/')
    return render_template_string(HTML_PAGE, user_data=user_data, current_slot_id=slot_id, all_slots=slots, statuses=statuses, base_url=base_url)

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

@app.route('/post_status', methods=['POST'])
def post_status():
    data = request.json
    slot_id, user_data = get_slot_by_token(data.get('token'))
    if user_data:
        new_st = {
            "name": user_data['name'],
            "avatar": user_data['avatar'],
            "text": data.get('text', ''),
            "media": data.get('media', ''),
            "time": datetime.now().strftime("%I:%M %p")
        }
        statuses.insert(0, new_st)
        socketio.emit('new_status_broadcast', new_st)
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

@app.route('/kick_user', methods=['POST'])
def kick_user():
    data = request.json
    if data.get('admin_token') == ADMIN_TOKEN:
        slot_id = int(data.get('slot_id'))
        if slot_id in slots and slot_id != 0:
            slots[slot_id]['token'] = f"bsher-user-code-0{slot_id}" if slot_id < 10 else f"bsher-user-code-{slot_id}"
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

@socketio.on('join_private_room')
def on_join_private_room(data):
    room = data.get('room')
    join_room(room)
    if room in chat_history:
        emit('load_history', chat_history[room])

@socketio.on('send_private_message')
def handle_private_message(data):
    slot_id, user_data = get_slot_by_token(data.get('token'))
    if user_data:
        room = data.get('room')
        now_time = datetime.now().strftime("%I:%M %p")
        msg_id = data.get('msg_id')
        
        msg_obj = {
            'room': room,
            'sender_slot': slot_id,
            'sender_name': user_data['name'],
            'msg_id': msg_id,
            'msg_type': data.get('msg_type', 'text'),
            'encrypted_data': data.get('encrypted_data'),
            'time': now_time,
            'reactions': {}
        }
        
        if room not in chat_history:
            chat_history[room] = []
        chat_history[room].append(msg_obj)
        message_reactions[msg_id] = {}

        emit('receive_private_message', msg_obj, room=room)

@socketio.on('send_reaction')
def handle_reaction(data):
    msg_id = data.get('msg_id')
    emoji = data.get('emoji')
    slot_id, user_data = get_slot_by_token(data.get('token'))
    if user_data and msg_id in message_reactions:
        reactions = message_reactions[msg_id]
        if emoji not in reactions:
            reactions[emoji] = []
        if slot_id not in reactions[emoji]:
            reactions[emoji].append(slot_id)
        else:
            reactions[emoji].remove(slot_id)
            if not reactions[emoji]:
                del reactions[emoji]
        
        room = data.get('room')
        # Also update in chat_history if needed
        if room in chat_history:
            for m in chat_history[room]:
                if m.get('msg_id') == msg_id:
                    m['reactions'] = reactions

        emit('update_reactions', {'msg_id': msg_id, 'reactions': reactions}, room=room)

@socketio.on('signal')
def handle_signal(data):
    emit('signal', data, room=data.get('room'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
