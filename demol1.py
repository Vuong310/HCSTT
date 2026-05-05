import mysql.connector

def connect_db():
    # Kết nối tới MySQL Workbench
    # LƯU Ý: Bạn cần thay đổi 'user' và 'password' cho đúng với MySQL trên máy của bạn
    conn = mysql.connector.connect(
        host="localhost",
        user="root",          # Tên đăng nhập MySQL (thường mặc định là root)
        password="Tamihaya198", # <--- NHẬP MẬT KHẨU MYSQL CỦA BẠN VÀO ĐÂY
        database="chatbot"    # Tên database đã tạo ở lệnh 'USE chatbot;'
    )
    return conn

def xuly_cau_tra_loi(id_cauhoi_hien_tai, cau_tra_loi_cua_user):
    conn = connect_db()
    cursor = conn.cursor()
    
    # 1. Tìm luật trong bảng Cây Quyết Định khớp với câu trả lời
    # Chú ý: MySQL dùng %s thay vì ? như SQLite
    query = """
        SELECT id_cauhoi_tiep_theo, id_ketluan 
        FROM Rules
        WHERE id_cauhoi_ht = %s AND gia_tri_tra_loi = %s
    """
    cursor.execute(query, (id_cauhoi_hien_tai, cau_tra_loi_cua_user))
    luat = cursor.fetchone()
    
    if luat:
        id_cauhoi_tiep = luat[0]
        id_ketluan = luat[1]
        
        # 2. Nếu có câu hỏi tiếp theo -> Đi lấy nội dung câu hỏi
        if id_cauhoi_tiep is not None:
            cursor.execute("SELECT noi_dung FROM Questions WHERE id_cauhoi = %s", (id_cauhoi_tiep,))
            cau_hoi_moi = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            return {"type": "question", "content": cau_hoi_moi, "id": id_cauhoi_tiep}
            
        # 3. Nếu đã đến cuối đường -> Đi lấy kết luận
        elif id_ketluan is not None:
            cursor.execute("SELECT noi_dung, loi_khuyen FROM Conclusions WHERE id_ketluan = %s", (id_ketluan,))
            ket_luan = cursor.fetchone()
            cursor.close()
            conn.close()
            return {"type": "conclusion", "content": f"{ket_luan[0]}\nLời khuyên: {ket_luan[1]}"}
            
    cursor.close()
    conn.close()
    return {"type": "error", "content": "Tôi không hiểu câu trả lời này."}

# ==========================================
# KHỐI LỆNH THỰC THI (GIẢI QUYẾT VẤN ĐỀ 1)
# ==========================================
if __name__ == "__main__":
    print("--- BẮT ĐẦU TEST HỆ SUY DIỄN ---")
    
    # Kịch bản 1: Giả sử đang ở câu 101 (Đèn Router sáng không?) và User gõ "Có"
    # Theo luật trong database, hệ thống phải trả về câu hỏi 102 (Có vào được Google không?)
    print("\nTest Kịch bản 1 (Đang ở Q101, Trả lời: 'Có'):")
    ket_qua_1 = xuly_cau_tra_loi(101, 'Có')
    print(ket_qua_1)
    
    # Kịch bản 2: Giả sử đang ở câu 102 (Vào Google được không?) và User gõ "Không"
    # Theo luật, hệ thống phải trả về Kết luận 12 (Lỗi DNS)
    print("\nTest Kịch bản 2 (Đang ở Q102, Trả lời: 'Không'):")
    ket_qua_2 = xuly_cau_tra_loi(102, 'Không')
    print(ket_qua_2)
    
    print("\n--- HOÀN TẤT ---")