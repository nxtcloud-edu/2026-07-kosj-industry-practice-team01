import sqlite3
from datetime import datetime

# 데이터베이스 파일이 저장될 경로 (루트 폴더)
DB_PATH = "chat_logs.db"

def init_db():
    """서버가 시작될 때 비식별 로그 테이블을 자동 생성하는 함수"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 식별 정보(IP, 세션 등) 없이 순수 대화 데이터만 저장
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            user_message TEXT,
            status TEXT,
            bot_message TEXT,
            source_title TEXT
        )
    ''')
    conn.commit()
    conn.close()

def insert_log(user_message: str, status: str, bot_message: str, source_title: str = None):
    """채팅 응답 시 호출되어 DB에 로그를 기록하는 함수"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute('''
        INSERT INTO chat_logs (timestamp, user_message, status, bot_message, source_title)
        VALUES (?, ?, ?, ?, ?)
    ''', (timestamp, user_message, status, bot_message, source_title))
    
    conn.commit()
    conn.close()