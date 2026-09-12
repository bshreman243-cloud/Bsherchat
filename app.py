import eventlet
eventlet.monkey_patch()

import os
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

HTML_PAGE = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>bisher chat</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: sans-serif; background-color: #efeae2; padding: 8px; }
        .header { background-color: #075e54; color: white; padding: 10px; border-radius: 8px; text-align: center; font-size: 14px; }
        .status { font-size: 11px; margin-top: 4px; color: #a3e635; }
        .chat-box { background-color: #e5ddd5; height: 320px; border-radius: 8px; padding: 10px; margin: 8px 0; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; }
        .my-msg { background-color: #dcf8c6; padding: 8px 12px; border-radius: 8px; align-self: flex-start; max-width: 80%; font-size: 14px; }
        .other-msg { background-color: #ffffff; padding: 8px 12px; border-radius: 8px; align-self: flex-end; max-width: 80%; font-size: 14px; }
        .sender-name { font-size: 11px; color: #075e54; font-weight: bold; margin-bottom: 3px; }
        .input-box { display: flex; gap: 5px; }
        input { flex: 1; padding: 10px; border: 1px solid #ccc; border-radius: 5px; font-size: 14px; }
        button { background-color: #128c7e; color: white; border: none; padding: 10px 15px; border-radius: 5px; font-size: 14px; font-weight: bold; cursor: pointer; }
    </style>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
</head>
<body>
    <div class="header">
        <h3 id="appTitle">💬 bisher chat</h3>
        <div class="status" id="statusText">🟢 متصل بالخادم عالمياً</div>
    </div>
    <div class="chat-box" id="box"></div>
    <div class="input-box">
        <input type="text" id="txt" placeholder="اكتب رسالتك...">
        <button onclick="sendMsg()">إرسال</button>
    </div>
    <script>
        var params = new URLSearchParams(window.location.search);
        var currentUserId = params.get('user') || '1';
        document.getElementById("appTitle").innerText = "💬 bisher chat (مستخدم #" + currentUserId + ")";
        var socket = io();
        socket.on('receive_message', function(data) {
            var box = document.getElementById("box");
            var d = document.createElement("div");
            if (data.user === currentUserId) {
                d.className = "my-msg";
                d.innerText = data.text;
            } else {
                d.className = "other-msg";
                d.innerHTML = "<div class='sender-name'>مستخدم #" + data.user + "</div>" + data.text;
            }
            box.appendChild(d);
            box.scrollTop = box.scrollHeight;
        });
        function sendMsg() {
            var txtInput = document.getElementById("txt");
            if (txtInput.value.trim() !== "") {
                socket.emit('send_message', {
                    user: currentUserId,
                    text: txtInput.value
                });
                txtInput.value = "";
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

@socketio.on('send_message')
def handle_message(data):
    emit('receive_message', data, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, host='0.0.0.0', port=port)
