from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from instagrapi import Client
import time
import os

app = FastAPI()

# WebApp HTML faylini ko'rsatish
@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("index.html", "r", encoding="utf-8") as file:
        return file.read()

# Kelayotgan ma'lumotlar strukturasi
class UnfollowRequest(BaseModel):
    session_id: str
    count: int

# Orqa fonda ishlaydigan Unfollow funksiyasi
def process_unfollow(session_id: str, count: int):
    try:
        cl = Client()
        # Session ID orqali Instagram'ga kirish (Parolsiz)
        cl.login_by_sessionid(session_id)
        
        # Akkauntdagi obunalar ro'yxatini olish
        following = cl.user_following(cl.user_id)
        unfollowed_count = 0

        for user_id in list(following.keys()):
            if unfollowed_count >= count:
                break
            try:
                cl.user_unfollow(user_id)
                unfollowed_count += 1
                time.sleep(2) # Instagram bloklamasligi uchun 2 soniya kutish
            except Exception as e:
                print(f"Xatolik yuz berdi: {e}")
                continue
                
        print(f"Jami {unfollowed_count} ta obuna bekor qilindi.")
    except Exception as e:
        print(f"Instagram'ga ulanishda xatolik: {e}")

# Frontend'dan so'rov keladigan API
@app.post("/api/unfollow")
async def start_unfollow(request: UnfollowRequest, background_tasks: BackgroundTasks):
    if request.count < 1 or request.count > 10000:
        raise HTTPException(status_code=400, detail="Xato! Unfollow soni 1 dan 10,000 gacha bo'lishi kerak.")
    
    if not request.session_id:
        raise HTTPException(status_code=400, detail="Session ID kiritilmadi!")

    # Jarayonni orqa fonga yuboramiz (API qotib qolmasligi uchun)
    background_tasks.add_task(process_unfollow, request.session_id, request.count)
    
    return {"status": "success", "message": f"{request.count} ta obunani bekor qilish jarayoni boshlandi."}
