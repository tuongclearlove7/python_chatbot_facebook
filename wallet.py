import sqlite3
import random
import string

DB_NAME = "wallet.db"

def init_wallet_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            psid TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            balance INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def generate_username(psid: str) -> str:
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{psid}_{random_part}"

def create_account(psid: str) -> dict:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT psid, username, balance FROM accounts WHERE psid = ?", (psid,))
        if cursor.fetchone():
            return {"success": False, "message": "Bạn đã có tài khoản rồi!"}

        username = generate_username(psid)
        cursor.execute("INSERT INTO accounts (psid, username, balance) VALUES (?, ?, 0)", 
                      (psid, username))
        conn.commit()
        
        return {
            "success": True,
            "message": f"Tạo tài khoản thành công!\nAccount Id: {psid}\nUsername: {username}\nSố dư: 0$"
        }
    finally:
        conn.close()

def get_balance(psid: str) -> dict:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT psid, username, balance FROM accounts WHERE psid = ?", (psid,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return {"exists": True, "psid": result[0], "username": result[1], "balance": result[2]}
    return {"exists": False}

def recharge(psid: str, amount: int) -> dict:
    if amount <= 0:
        return {"success": False, "message": "Số tiền nạp phải lớn hơn 0!"}
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT balance FROM accounts WHERE psid = ?", (psid,))
        result = cursor.fetchone()
        if not result:
            return {"success": False, "message": "❌ Bạn chưa có tài khoản. Hãy tạo bằng lệnh: create account"}

        new_balance = result[0] + amount
        cursor.execute("UPDATE accounts SET balance = ? WHERE psid = ?", (new_balance, psid))
        conn.commit()
        
        return {
            "success": True,
            "message": f"Nạp tiền thành công +{amount:,}$\nSố dư hiện tại: {new_balance:,}$"
        }
    finally:
        conn.close()

def withdraw(psid: str, amount: int) -> dict:
    if amount <= 0:
        return {"success": False, "message": "Số tiền rút phải lớn hơn 0!"}
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT balance FROM accounts WHERE psid = ?", (psid,))
        result = cursor.fetchone()
        if not result:
            return {"success": False, "message": "❌ Bạn chưa có tài khoản!"}

        current = result[0]
        if current < amount:
            return {
                "success": False,
                "message": f"❌ Số dư không đủ!\nSố dư hiện tại: {current:,}$nYêu cầu rút: {amount:,}$"
            }

        new_balance = current - amount
        cursor.execute("UPDATE accounts SET balance = ? WHERE psid = ?", (new_balance, psid))
        conn.commit()
        
        return {
            "success": True,
            "message": f"Rút tiền thành công -{amount:,}$\nSố dư còn lại: {new_balance:,}$"
        }
    finally:
        conn.close()