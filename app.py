from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi import Query
from pydantic import BaseModel
import os
import requests
from dotenv import load_dotenv

from wallet import (
    init_wallet_db,
    create_account,
    recharge,
    withdraw,
    get_balance
)

load_dotenv()

app = FastAPI()

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_TOKEN")  

if not VERIFY_TOKEN or not PAGE_ACCESS_TOKEN:
    print("❌ Thiếu VERIFY_TOKEN hoặc FB_PAGE_TOKEN trong file .env")

init_wallet_db()


class SendMessageRequest(BaseModel):
    psid: str | None = None         
    recipient_id: str | None = None  
    text: str
    messaging_type: str = "RESPONSE"

    def get_psid(self) -> str:
        if self.psid:
            return self.psid
        if self.recipient_id:
            return self.recipient_id
        raise ValueError("Bạn phải truyền 'psid' hoặc 'recipient_id'")


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge")
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN and hub_challenge:
        print(f"✅ WEBHOOK VERIFIED THÀNH CÔNG! Challenge: {hub_challenge}")
        return PlainTextResponse(content=hub_challenge)

    print("❌ VERIFICATION FAILED")
    raise HTTPException(status_code=403, detail="Verification failed")


def send_message(psid: str, text: str, messaging_type: str = "RESPONSE") -> bool:
    """Gửi tin nhắn text qua Facebook Messenger"""
    
    if not PAGE_ACCESS_TOKEN:
        print("❌ Lỗi: PAGE_ACCESS_TOKEN chưa được thiết lập")
        return False

    body = {
        "recipient": {"id": psid},
        "message": {"text": text},
        "messaging_type": messaging_type
    }
    
    try:
        response = requests.post(
            "https://graph.facebook.com/v21.0/me/messages",
            params={"access_token": PAGE_ACCESS_TOKEN},
            json=body,
            timeout=10
        )
                
        if response.status_code == 200:
            print(f"✅ Gửi tin nhắn THÀNH CÔNG đến {psid}")
            return True
        else:
            print(f"❌ Gửi thất bại - Status: {response.status_code}")
            try:
                error_detail = response.json()
                print("Lỗi từ Facebook:", error_detail)
            except:
                print("Response text:", response.text)
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Lỗi: Timeout khi kết nối Facebook")
        return False
    except Exception as e:
        print(f"❌ Lỗi ngoại lệ khi gửi tin nhắn: {e}")
        return False


@app.post("/webhook")
async def post_webhook(request: Request):
    try:
        body = await request.json()
    except:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    if body.get("object") != "page":
        raise HTTPException(status_code=404)

    for entry in body.get("entry", []):
        for event in entry.get("messaging", []):
            sender_psid = event.get("sender", {}).get("id")
            if not sender_psid:
                continue

            if event.get("message"):
                message = event["message"]

                if message.get("attachments"):
                    send_message(sender_psid, "Cảm ơn bạn đã xem video của mình nhé!!! ❤️")
                    continue

                text_received = message.get("text", "").strip()
                lower_text = text_received.lower()

                print(f"Tin nhắn từ {sender_psid}: {text_received}")

                if lower_text == "create account":
                    result = create_account(sender_psid)
                    send_message(sender_psid, result["message"])
                    continue

                elif lower_text.startswith("recharge -"):
                    try:
                        parts = [p.strip() for p in text_received.split("-")]
                        if len(parts) != 3:
                            raise ValueError
                        
                        target_psid = parts[1]
                        amount = int(parts[2].replace(",", "").replace(".", ""))
                        
                        result = recharge(target_psid, amount)
                        send_message(sender_psid, result["message"])
                        continue
                    except:
                        send_message(sender_psid, 
                            "❌ Cú pháp Recharge sai!\n\n"
                            "Cách dùng đúng:\n"
                            "recharge - id account - amount\n"
                            "Ví dụ: recharge - 5006935289398760 - 1000")
                        continue

                elif lower_text.startswith("withdraw -"):
                    try:
                        parts = [p.strip() for p in text_received.split("-")]
                        if len(parts) != 3:
                            raise ValueError
                        
                        target_psid = parts[1]
                        amount = int(parts[2].replace(",", "").replace(".", ""))
                        
                        result = withdraw(target_psid, amount)
                        send_message(sender_psid, result["message"])
                        continue
                    except:
                        send_message(sender_psid, 
                            "❌ Cú pháp Withdraw sai!\n\n"
                            "Cách dùng đúng:\n"
                            "withdraw - id account - amount\n"
                            "Ví dụ: withdraw - 5006935289398760 - 1000")
                        continue

                elif lower_text in ["balance", "số dư", "check balance", "my balance"]:
                    info = get_balance(sender_psid)
                    if info["exists"]:
                        text = f"Thông tin ví của bạn:\n\nAccount Id: {info['psid']}\nUsername: {info['username']}\nSố dư: {info['balance']:,}$"
                    else:
                        text = "❌ Bạn chưa có tài khoản.\nHãy nhắn: create account để tạo ví."
                    send_message(sender_psid, text)
                    continue

                if any(greet in lower_text for greet in ["hi", "hello", "chào", "hey", "hế lô", "xin chào", "chào bạn"]):
                    text = "Chào bạn! ❤️\nMình là bot được tạo bởi Clearlove7 nè. Hôm nay bạn thế nào rồi?"

                elif any(thank in lower_text for thank in ["cảm ơn", "thanks", "thank you", "cảm ơn nhiều", "cảm ơn bạn"]):
                    text = "Không có gì đâu! Rất vui được hỗ trợ bạn nha 😊"

                elif any(bye in lower_text for bye in ["tạm biệt", "bye", "goodbye", "hẹn gặp lại", "ngủ ngon", "bai"]):
                    text = "Tạm biệt bạn! Hẹn gặp lại lần sau nhé ❤️ Chúc bạn một ngày thật vui!"

                elif any(health in lower_text for health in ["bạn khỏe không", "bạn khỏe ko", "how are you", "bạn sao rồi", "bạn ổn không"]):
                    text = "Mình khỏe lắm, cảm ơn bạn đã hỏi! 💪 Còn bạn thì sao? Có gì vui hôm nay không?"

                elif any(who in lower_text for who in ["bạn là ai", "who are you", "bot gì vậy", "ai vậy"]):
                    text = "Mình là chatbot vui tính được tạo bởi Clearlove7 nè 😄"

                elif any(love in lower_text for love in ["yêu bạn", "thích bạn", "love you", "crush bạn", "iu bạn"]):
                    text = "Ôi dễ thương quá trời luôn! ❤️ Mình cũng thích bạn lắm á!"

                elif any(laugh in lower_text for laugh in ["haha", "hihi", "hú hú", "😂", "🤣", "cười", "vui quá"]):
                    text = "Haha cười theo bạn luôn nè 🤣 Hôm nay bạn đang vui hả?"

                elif "gì vậy" in lower_text or "là gì" in lower_text or "giải thích" in lower_text:
                    text = "Bạn đang hỏi gì vậy? Kể mình nghe thử nha, mình sẽ cố gắng trả lời 😊"

                else:
                    text = ("Hmm... Mình chưa hiểu rõ lắm 😅\n\n"
                           "Để tạo ví bạn hãy dùng các cú pháp nhắn tin sau:\n"
                           "• Tạo tài khoản: create account\n"
                           "• Nạp tiền: recharge - id account - amount\n"
                           "• Rút tiền: withdraw - id account - amount\n"
                           "• Xem số dư: balance, số dư, check balance, my balance\n\n"
                           "Hoặc bạn có thể chào bình thường nhé!")

                send_message(sender_psid, text)

            elif event.get("postback"):
                send_message(sender_psid, "Postback received! Bạn vừa bấm một nút nào đó đúng không? 😊")

    return {"status": "EVENT_RECEIVED"}


@app.post("/send-message")
async def send_external_message(request: SendMessageRequest):
    try:
        psid = request.get_psid()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    print(f"📤 Nhận yêu cầu gửi tin từ API → PSID: {psid}")

    success = send_message(psid, request.text, request.messaging_type)

    if success:
        return {
            "status": "success",
            "message": "Tin nhắn đã được gửi thành công qua Messenger",
            "psid": psid,
            "text": request.text
        }
    else:
        raise HTTPException(
            status_code=500, 
            detail="Không thể gửi tin nhắn. Vui lòng kiểm tra log server và PAGE_ACCESS_TOKEN."
        )


@app.get("/")
async def homepage():
    return {"message": "Facebook Messenger Webhook + Wallet System is running 🚀"}