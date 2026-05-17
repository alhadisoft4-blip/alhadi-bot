import os
import asyncio
import http.server
import socketserver
import threading
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import TelegramError

# 🔒 إعدادات البيئة الأساسية
TOKEN = os.environ.get("BOT_TOKEN", "8914679676:AAEeV07KSkz_w5y-qbESc0BTFxB9d5LOvhA")
CHANNEL_ID = '@AlhadiSoft'
CHANNEL_INVITE_LINK = 'https://t.me/+BIHVdkbZ_qY5OTM0'

user_urls = {}

# 🌐 قائمة المحركات السحابية العالمية المحدثة لكسر الحظر
COBALT_INSTANCES = [
    "https://api.cobalt.tools/api/json",
    "https://cobalt.fastest.workers.dev/api/json",
    "https://api.wukong.wtf/api/json",
    "https://cobalt-api.lcom.cloud/api/json"
]

def start_dummy_server():
    """خادم وهمي يعمل في خيط منفصل تماماً لمنع ريندر من النوم دون التأثير على البوت"""
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"✅ Web server active on port {port}")
            httpd.serve_forever()
    except Exception as e:
        print(f"⚠️ Web server notice: {e}")

async def is_subscribed(user_id: int, bot) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except TelegramError:
        return True 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_subscribed(user_id, context.bot):
        keyboard = [[InlineKeyboardButton("📢 اشترك في القناة هنا", url=CHANNEL_INVITE_LINK)]]
        await update.message.reply_text(
            "⚠️ عذراً! يجب عليك الاشتراك في قناة المؤسسة أولاً لتتمكن من استخدام البوت مجاناً.\n\n"
            "👇 اشترك عبر الرابط أدناه ثم أرسل /start مجدداً للتحقق والتشغيل:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    reply_keyboard = [
        [KeyboardButton("🟢 Start")],
        [KeyboardButton("💼 خدماتنا"), KeyboardButton("👥 فريق الدعم الهادي سوفت")]
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "🚀 أهلاً بك في بوت التحميل غير القابل للحظر - مؤسسة الهادي سوفت!\n\n👇 أرسل رابط الفيديو مباشرة لبدء السحب الرقمي الآمن.",
        reply_markup=markup
    )

async def handle_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    chat_id = update.message.chat_id
    
    if not await is_subscribed(user_id, context.bot):
        keyboard = [[InlineKeyboardButton("📢 اشترك في القناة هنا", url=CHANNEL_INVITE_LINK)]]
        await update.message.reply_text("⚠️ يرجى الاشتراك في القناة أولاً لتفعيل خدمات البوت:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if text == "🟢 Start":
        await update.message.reply_text("🔄 البوت نشط وجاهز تماماً، أرسل رابط الفيديو المُراد تحميله الآن.")
        return
    elif text == "💼 خدماتنا":
        await update.message.reply_text("🛠️ **خدمات مؤسسة الهادي سوفت:**\n\n👈 تطوير وترقية البوتات والأنظمة البرمجية بأحدث التقنيات السحابية العالمية.")
        return
    elif text == "👥 فريق الدعم الهادي سوفت":
        await update.message.reply_text("👋 للتواصل معنا مباشرة عبر الرابط التالي:\n👉 t.me/AlhadiSoft")
        return

    if text.startswith("http://") or text.startswith("https://"):
        user_urls[chat_id] = text
        buttons = [
            [InlineKeyboardButton("🎬 جودة عالية", callback_data="1080"), InlineKeyboardButton("🎬 جودة متوسطة", callback_data="720")],
            [InlineKeyboardButton("🎬 جودة عادية", callback_data="480"), InlineKeyboardButton("🎵 تحويله إلى صوت MP3", callback_data="audio")]
        ]
        await update.message.reply_text("📌 تم فحص الرابط بنجاح وتحضير نفق السحب السحابي!\n\n👇 اختر الجودة المطلوبة:", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await update.message.reply_text("⚠️ يرجى إرسال رابط فيديو صحيح.")

async def try_download_from_instances(url, quality, is_audio):
    payload = {
        "url": url,
        "videoQuality": quality,
        "downloadMode": "audio" if is_audio else "video"
    }
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    
    async with aiohttp.ClientSession() as session:
        for instance in COBALT_INSTANCES:
            try:
                async with session.post(instance, json=payload, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        res_data = await response.json()
                        file_url = res_data.get("url")
                        if file_url:
                            return file_url
            except Exception:
                continue
    return None

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    choice = query.data
    url = user_urls.get(chat_id)
    
    if not url:
        await query.edit_message_text("❌ انتهت الجلسة، يرجى إرسال الرابط مجدداً.")
        return
        
    await query.edit_message_text("🔄 جاري كسر تشفير المنصة عبر الأنفاق الرقمية، يرجى الانتظار...")
    is_audio = (choice == "audio")
    quality = "720" if choice == "audio" else choice
    
    direct_file_url = await try_download_from_instances(url, quality, is_audio)
    
    if not direct_file_url:
        await query.edit_message_text("❌ عذراً! جميع محاولات كسر الحظر السحابية فشلت حالياً، يرجى المحاولة لاحقاً أو تجربة رابط آخر.")
        return

    await query.edit_message_text("🚀 تم اختراق الحظر بنجاح! جاري معالجة وحفظ الملف سحابياً...")
    fn = f"{chat_id}_hadi." + ("mp3" if is_audio else "mp4")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(direct_file_url) as file_resp:
                if file_resp.status == 200:
                    with open(fn, "wb") as f:
                        async for chunk in file_resp.content.iter_chunked(1024 * 1024):
                            f.write(chunk)
                    
                    await query.edit_message_text("⚡ اكتملت المعالجة! جاري الرفع المباشر لـ تيليجرام...")
                    with open(fn, 'rb') as f:
                        if is_audio:
                            await context.bot.send_audio(chat_id=chat_id, audio=f, caption="🎵 تم فصل وتحويل الصوت بنجاح - الهادي سوفت")
                        else:
                            await context.bot.send_video(chat_id=chat_id, video=f, caption="🎬 تم كسر الحظر وسحب الفيديو بنجاح - الهادي سوفت")
                    
                    if os.path.exists(fn): os.remove(fn)
                    user_urls.pop(chat_id, None)
                else:
                    await query.edit_message_text("❌ فشل السيرفر في قراءة دفق البيانات الأخير.")
    except Exception as e:
        if os.path.exists(fn): os.remove(fn)
        await query.edit_message_text("❌ حدث خطأ أثناء رفع الملف، تأكد من أن الحجم لا يتجاوز سعة التيليجرام المجانية.")

async def main():
    # تشغيل خادم ويب وهمي لمنع خروج المنصة
    threading.Thread(target=start_dummy_server, daemon=True).start()
    
    # بناء وتأسيس البوت بشكل متزامن صحيح لمنع تعارض الخيوط
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))
    app.add_handler(CallbackQueryHandler(button_click))
    
    # تهيئة وتحديث محرك الـ Polling يدوياً لحل مشكلة الـ Runtime RuntimeError
    await app.initialize()
    await app.updater.start_polling()
    await app.start()
    
    print("🚀 AlhadiSoft Anti-Ban Engine successfully initialized on Render!")
    
    # إبقاء البوت حياً ومتزامناً مع السيرفر السحابي دون انقطاع
    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        await app.updater.stop()
        await app.stop()

if __name__ == '__main__':
    # تشغيل الحلقة الأساسية لـ asyncio بشكل متوافق وآمن
    try:
        asyncio.run(main())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    
