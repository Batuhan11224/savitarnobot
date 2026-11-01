import logging
import sqlite3
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- YAPILANDIRMA VE KİŞİSEL BİLGİLERİNİZ ---
BOT_TOKEN = "8890263750:AAGg63IXLBDsGgq_klkaqtXgTI5nDpBFmMY"
ADMIN_ID = 1291260407
SMS_API_KEY = "182ecc213e464d7b0a330f1fe1fbc09a"

# Kurumsal Ödeme Bilgileri
IBAN_BILGISI = "TR10 0006 2000 9100 0006 9697 09"
ALICI_ISIM = "Garanti Ödeme ve Elektronik Para Hizmetleri A.Ş."
ACIKLAMA_KODU = "TAMİ7366927098769000"

# --- 💰 DİNAMİK FİYATLANDIRMA AYARLARI (TL Cinsinden) ---
PRICES = {
    "telegram": {"TR": 120, "PS": 130, "UK": 100, "ID": 60},
    "whatsapp": {"TR": 150, "PS": 160, "UK": 120, "ID": 80},
    "instagram": {"TR": 80, "PS": 85, "UK": 70, "ID": 50}
}

# --- 🌍 ÜLKE API KODLARI ---
COUNTRY_CODES = {
    "TR": "0",   
    "PS": "97",  
    "UK": "16",  
    "ID": "6"    
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- VERİTABANI İŞLEMLERİ ---
def init_db():
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)")
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0

def update_balance(user_id, amount):
    conn = sqlite3.connect("bot_data.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?", (user_id, amount, amount))
    conn.commit()
    conn.close()

init_db()
PENDING_REQUESTS = {}  
request_counter = 1

# --- TURONAY API ENTEGRASYONU ---
def get_turonay_number(service, country_code):
    url = f"https://turonay.com{SMS_API_KEY}&action=getNumber&service={service}&country={country_code}"
    try:
        response = requests.get(url).text.strip()
        if "ACCESS_NUMBER" in response:
            parts = response.split(":")
            return {"status": "success", "order_id": parts[1], "number": parts[2]}
        return {"status": "error", "message": response}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def check_turonay_sms(order_id):
    url = f"https://turonay.com{SMS_API_KEY}&action=getStatus&id={order_id}"
    try:
        response = requests.get(url).text.strip()
        if "STATUS_OK" in response:
            code = response.split(":")
            return {"status": "received", "code": code[1]}
        elif "STATUS_WAIT_CODE" in response:
            return {"status": "waiting", "message": "Kod henüz gelmedi, bekleniyor..."}
        elif "STATUS_CANCEL" in response:
            return {"status": "canceled", "message": "Aktivasyon iptal edildi veya zaman aşımı."}
        return {"status": "unknown", "message": response}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- ANA MENÜ ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    current_bal = get_balance(user_id)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📱 Numara Satın Al", callback_data="menu_services")
    builder.button(text="💰 Bakiye Yükle (Dekont At)", callback_data="deposit")
    builder.adjust(1)
    
    await message.answer(
        f"👋 Merhaba! Sanal Numara Botuna Hoş Geldin.\n\n"
        f"💵 Mevcut Bakiyeniz: {current_bal} TL\n"
        f"Lütfen yapmak istediğiniz işlemi seçin:",
        reply_markup=builder.as_markup()
    )

# --- SERVİS SEÇİM MENÜSÜ ---
@dp.callback_query(F.data == "menu_services")
async def services_menu(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="🔹 Telegram", callback_data="select_service_telegram")
    builder.button(text="🟢 WhatsApp", callback_data="select_service_whatsapp")
    builder.button(text="📸 Instagram", callback_data="select_service_instagram")
    builder.button(text="⬅️ Ana Menü", callback_data="back_to_main")
    builder.adjust(1)
    await callback.message.edit_text("📱 Lütfen numara almak istediğiniz platformu seçin:", reply_markup=builder.as_markup())

# --- ÜLKE SEÇİM MENÜSÜ ---
@dp.callback_query(F.data.startswith("select_service_"))
async def countries_menu(callback: types.CallbackQuery):
    service = callback.data.split("_")[2]
    
    builder = InlineKeyboardBuilder()
    builder.button(text=f"🇹🇷 Türkiye ({PRICES[service]['TR']} TL)", callback_data=f"buy_{service}_TR")
    builder.button(text=f"🇵🇸 Filistin ({PRICES[service]['PS']} TL)", callback_data=f"buy_{service}_PS")
    builder.button(text=f"🇬🇧 İngiltere ({PRICES[service]['UK']} TL)", callback_data=f"buy_{service}_UK")
    builder.button(text=f"🇮🇩 Endonezya ({PRICES[service]['ID']} TL)", callback_data=f"buy_{service}_ID")
    builder.button(text="⬅️ Geri Dön", callback_data="menu_services")
    builder.adjust(1)
    
    await callback.message.edit_text(f"🌍 {service.upper()} için lütfen bir ülke seçin:", reply_markup=builder.as_markup())

# --- NUMARA SATIN ALMA TETİKLEYİCİSİ ---
@dp.callback_query(F.data.startswith("buy_"))
async def process_purchase(callback: types.CallbackQuery):
    data_parts = callback.data.split("_")
    service = data_parts[1]
    country_alias = data_parts[2]
    
    srv_code = "tg" if service == "telegram" else "wa" if service == "whatsapp" else "ig"
    country_code = COUNTRY_CODES[country_alias]
    cost = PRICES[service][country_alias]
    
    user_id = callback.from_user.id
    user_balance = get_balance(user_id)
    
    if user_balance < cost:
        await callback.answer(f"⚠️ Yetersiz bakiye! Bu işlem için {cost} TL gerekiyor.", show_alert=True)
        return
        
    await callback.message.answer(f"🔄 Turonay üzerinden numara talep ediliyor...")
    result = get_turonay_number(service=srv_code, country_code=country_code)
    
    if result["status"] == "success":
        update_balance(user_id, -cost)
        
        builder = InlineKeyboardBuilder()
        builder.button(text="📩 Kodu Sorgula (SMS Bekle)", callback_data=f"check_sms_{result['order_id']}")
        
        await callback.message.answer(
            f"🎉 **Numaranız Başarıyla Alındı!**\n\n"
            f"📱 Platform: {service.upper()}\n"
            f"🌍 Ülke: {country_alias}\n"
            f"📞 Numara: `{result['number']}`\n"
            f"🆔 Aktivasyon ID: `{result['order_id']}`\n\n"
            f"⚠️ **Talimat:** Numarayı uygulamanıza yazın ve kod gönderilmesini sağlayın. Ardından aşağıdaki butona basarak kodu sorgulayın.",
            reply_markup=builder.as_markup()
        )
    else:
        await callback.message.answer(f"❌ Numara alınamadı.\nTuronay Yanıtı: {result['message']}")
    await callback.answer()

# --- SMS SORGULAMA ---
@dp.callback_query(F.data.startswith("check_sms_"))
async def process_check_sms(callback: types.CallbackQuery):
    order_id = callback.data.split("_")[2]
    
    await callback.answer("🔍 Kod sorgulanıyor...")
    sms_result = check_turonay_sms(order_id)
    
    if sms_result["status"] == "received":
        await callback.message.answer(f"✅ **SMS KODU GELDİ!**\n\n🔑 Kodunuz: `{sms_result['code']}`")
    elif sms_result["status"] == "waiting":
        await callback.message.answer("⏳ Kod henüz Turonay sistemine ulaşmadı. Lütfen 1-2 dakika bekleyip butona tekrar basmayı deneyin.")
    else:
        await callback.message.answer(f"❌ Durum: {sms_result['message']}")

# --- BAKİYE YÜKLEME VE ADMİN SÜREÇLERİ ---
@dp.callback_query(F.data == "deposit")
async def deposit_callback(callback: types.CallbackQuery):
    await callback.message.answer(f"🏦 Ödeme Bilgileri:\n\n📍 IBAN: {IBAN_BILGISI}\n👤 Alıcı: {ALICI_ISIM}\n💵 Tutar: 100 TL\n\n⚠️ ÖNEMLİ NOT:\nAçıklama kısmına bu kodu yazın:\n👉 {ACIKLAMA_KODU} 👈\n\nÖdemeyi yaptıktan sonra dekont ekran görüntüsünü FOTOĞRAF olarak gönderiniz.")
    await callback.answer()

@dp.message(F.photo)
async def handle_receipt(message: types.Message):
    global request_counter
    user_id = message.from_user.id
    PENDING_REQUESTS[request_counter] = {"user_id": user_id, "amount": 100}
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Onayla (+100 TL)", callback_data=f"admin_approve_{request_counter}")
    builder.button(text="❌ Reddet", callback_data=f"admin_reject_{request_counter}")
    builder.adjust(2)
    username = f"@{message.from_user.username}" if message.from_user.username else "Kullanıcı adı yok"
    await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=f"🔔 Yeni Bakiye Talebi!\n\n👤 Kullanıcı: {username}\nID: {user_id}", reply_markup=builder.as_markup())
    request_counter += 1
    await message.answer("🔄 Dekont alındı, admin onayından sonra yüklenecektir.")

@dp.callback_query(F.data.startswith("admin_"))
async def admin_decision(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data_parts = callback.data.split("_")
    action = data_parts[1]
    req_id = int(data_parts[2])
    req_info = PENDING_REQUESTS.get(req_id)
    if not req_info: return
    target_user_id, amount = req_info["user_id"], req_info["amount"]
    if action == "approve":
        update_balance(target_user_id, amount)
        try: await bot.send_message(target_user_id, f"🎉 Hesabınıza {amount} TL yüklendi! /start ile menüyü açabilirsiniz.")
        except: pass
    elif action == "reject":
        try: await bot.send_message(target_user_id, "❌ Dekontunuz onaylanmadı.")
        except: pass
    del PENDING_REQUESTS[req_id]
    await callback.message.edit_caption(caption=f"İşlem tamamlandı: {action}")
    await callback.answer()