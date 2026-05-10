from flask import Flask, request
import requests
import mysql.connector

app = Flask(__name__)

# --- CẤU HÌNH FACEBOOK ---
PAGE_ACCESS_TOKEN = 'EAAzRK4mXReABRTZC4ZBrA7DzQOsP0lXgOP8TbBKSU8X4VifOH4BwmSE0VZCR05ea3k4VWoDOrhbkQC5bADwbZAuSz1B47kBOWKCbGd9d09y12bgPO9hzL8FOBIZC2hUl9JOEjvqn3MQYn7vMpfqsxt9VbyC1UVuRFFcN8ZCuJ3ZAyXAMZBZAr4uyBcg6g6FWipKAa4ZAbV5Ep0Ea37ldETqPNvHAZDZD'
VERIFY_TOKEN = 'xacminh'

# --- KẾT NỐI DATABASE ---
def connect_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="30122005", 
        database="chatbot"
    )

# --- ĐỘNG CƠ SUY DIỄN TỪ DEMOL1.PY ---
def xuly_cau_tra_loi(id_cauhoi_hien_tai, cau_tra_loi_cua_user):
    conn = connect_db()
    cursor = conn.cursor()
    query = """
        SELECT id_cauhoi_tiep_theo, id_ketluan 
        FROM Rules
        WHERE id_cauhoi_ht = %s AND gia_tri_tra_loi = %s
    """
    cursor.execute(query, (id_cauhoi_hien_tai, cau_tra_loi_cua_user))
    luat = cursor.fetchone()
    
    result = {"type": "error", "content": "Tôi không hiểu. Hãy trả lời theo gợi ý (ví dụ: Có / Không)."}
    
    if luat:
        id_cauhoi_tiep = luat[0]
        id_ketluan = luat[1]
        
        if id_cauhoi_tiep is not None:
            cursor.execute("SELECT noi_dung FROM Questions WHERE id_cauhoi = %s", (id_cauhoi_tiep,))
            result = {"type": "question", "content": cursor.fetchone()[0], "id": id_cauhoi_tiep}
        elif id_ketluan is not None:
            cursor.execute("SELECT noi_dung, loi_khuyen FROM Conclusions WHERE id_ketluan = %s", (id_ketluan,))
            ket_luan = cursor.fetchone()
            result = {"type": "conclusion", "content": f"KẾT LUẬN: {ket_luan[0]}\n💡 Lời khuyên: {ket_luan[1]}"}
            
    cursor.close()
    conn.close()
    return result

# --- QUẢN LÝ TRÍ NHỚ (USER SESSIONS) ---
def get_user_state(sender_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id_cauhoi_vua_tl FROM UserSessions WHERE fb_user_id = %s", (sender_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else None

def set_user_state(sender_id, question_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT fb_user_id FROM UserSessions WHERE fb_user_id = %s", (sender_id,))
    if cursor.fetchone():
        cursor.execute("UPDATE UserSessions SET id_cauhoi_vua_tl = %s WHERE fb_user_id = %s", (question_id, sender_id))
    else:
        # Tạm thời fix cứng chủ đề 1 (Kỹ thuật máy tính) cho bài test này
        cursor.execute("INSERT INTO UserSessions (fb_user_id, id_chude_dang_chon, id_cauhoi_vua_tl, trang_thai) VALUES (%s, 1, %s, 1)", (sender_id, question_id))
    conn.commit()
    cursor.close()
    conn.close()

def clear_user_state(sender_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM UserSessions WHERE fb_user_id = %s", (sender_id,))
    conn.commit()
    cursor.close()
    conn.close()

# --- WEBHOOK & XỬ LÝ NHẮN TIN ---
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get('hub.verify_token') == VERIFY_TOKEN:
            return request.args.get('hub.challenge'), 200
        return 'Forbidden', 403

    if request.method == 'POST':
        data = request.get_json()
        if data['object'] == 'page':
            for entry in data['entry']:
                for event in entry['messaging']:
                    if event.get('message') and event['message'].get('text'):
                        sender_id = event['sender']['id']
                        text = event['message']['text']
                        
                        # Kích hoạt luồng suy diễn
                        process_message(sender_id, text)
                        
            return 'EVENT_RECEIVED', 200
        return 'Not Found', 404

# Quyên mới thêm
#hàm lấy trạng thái
def get_full_user_state(sender_id):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id_chude_dang_chon, id_cauhoi_vua_tl, trang_thai
        FROM UserSessions
        WHERE fb_user_id = %s
    """, (sender_id,))

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    return row if row else None
def process_message(sender_id, text):

    user_state = get_full_user_state(sender_id)

    # =========================
    # BẮT ĐẦU CHAT
    # =========================
    if user_state is None or text.lower() in ['bắt đầu', 'bat dau', 'chào']:

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO UserSessions 
            (fb_user_id, id_chude_dang_chon, id_cauhoi_vua_tl, trang_thai)
            VALUES (%s, NULL, NULL, 0)
            ON DUPLICATE KEY UPDATE
            trang_thai = 0,
            id_chude_dang_chon = NULL,
            id_cauhoi_vua_tl = NULL
        """, (sender_id,))

        conn.commit()
        cursor.close()
        conn.close()

        menu = """
🤖 Chào bạn! Hãy chọn chủ đề:

1️⃣ Kỹ thuật máy tính
2️⃣ Thế giới động vật
3️⃣ Tư vấn điện thoại
4️⃣ Tư vấn thời trang

👉 Hãy nhập số 1 - 4
"""

        send_message(sender_id, menu)
        return

    # =========================
    # LẤY THÔNG TIN USER
    # =========================
    id_chude = user_state[0]
    current_q_id = user_state[1]
    trang_thai = user_state[2]

    # =========================
    # USER ĐANG CHỌN CHỦ ĐỀ
    # =========================
    if trang_thai == 0:

        topic_mapping = {
            "1": (1, 101),
            "2": (2, 201),
            "3": (3, 301),
            "4": (4, 401)
        }

        if text not in topic_mapping:
            send_message(sender_id, "❌ Vui lòng nhập số từ 1 đến 4.")
            return

        selected_topic, first_question = topic_mapping[text]

        conn = connect_db()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE UserSessions
            SET id_chude_dang_chon = %s,
                id_cauhoi_vua_tl = %s,
                trang_thai = 1
            WHERE fb_user_id = %s
        """, (selected_topic, first_question, sender_id))

        conn.commit()

        cursor.execute("""
            SELECT noi_dung
            FROM Questions
            WHERE id_cauhoi = %s
        """, (first_question,))

        question = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        send_message(sender_id, question)
        return

    # =========================
    # ĐANG CHAT SUY DIỄN
    # =========================
    result = xuly_cau_tra_loi(current_q_id, text)

    if result["type"] == "question":

        set_user_state(sender_id, result["id"])
        send_message(sender_id, result["content"])

    elif result["type"] == "conclusion":

        clear_user_state(sender_id)

        send_message(
            sender_id,
            result["content"] + "\n\n👉 Gõ 'Bắt đầu' để chọn chủ đề mới."
        )

    else:
        send_message(sender_id, result["content"])
#sử đến đây là 

# def process_message(sender_id, text):
#     current_q_id = get_user_state(sender_id)

#     # Nếu người dùng nhắn chữ "Bắt đầu" hoặc chưa có phiên làm việc
#     if current_q_id is None or text.lower() in ['bắt đầu', 'bat dau', 'chào']:
#         set_user_state(sender_id, 101) # Load câu hỏi đầu tiên của Chủ đề 1
#         send_message(sender_id, "🤖 Chào bạn! Tôi là Hệ chuyên gia chẩn đoán lỗi mạng.\n👉 Đèn báo Internet trên cục Router có đang sáng màu xanh không? (Có / Không)")
#         return

#     # Nếu đang ở giữa cuộc hội thoại -> Đưa câu trả lời vào cây quyết định
#     result = xuly_cau_tra_loi(current_q_id, text)

#     if result["type"] == "question":
#         set_user_state(sender_id, result["id"])
#         send_message(sender_id, result["content"])
#     elif result["type"] == "conclusion":
#         clear_user_state(sender_id) # Xóa trí nhớ để sẵn sàng tư vấn ca mới
#         send_message(sender_id, result["content"])
#     else:
#         send_message(sender_id, result["content"])

def send_message(recipient_id, text):
    params = {"access_token": PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    data = {"recipient": {"id": recipient_id}, "message": {"text": text}}
    requests.post("https://graph.facebook.com/v19.0/me/messages", params=params, headers=headers, json=data)

if __name__ == '__main__':
    app.run(port=5000, debug=True)