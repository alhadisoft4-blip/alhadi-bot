import os, asyncio, http.server, socketserver, threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import TelegramError
import yt_dlp

TOKEN = '8914679676:AAEbKf4zukBYg6Ibd7VsDSOSFPWCinPKRig'
CHANNEL_ID = '@AlhadiSoft'  # اسم مستخدم القناة العام بدون الرابط للتحقق من الاشتراك
CHANNEL_INVITE_LINK = 'https://t.me/+BIHVdkbZ_qY5OTM0'

user_urls = {}

PROXY_OPTIONS = {
    'quiet': True,
    'skip_download': True,
    'geo_bypass': True,
    'nocheckcertificate': True,
    'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
    'restrictfilenames': True
}

# خادم وهمي لضمان استقرار السيرفر السحابي ريندر
def start_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

# دالة برمجية للتحقق مما إذا كان المستخدم مشتركاً في القناة أم لا
async def is_subscribed(user_id: int, bot) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except TelegramError:
        # في حال لم يتمكن البوت من فحص الحساب (مثلاً البوت ليس مشرفاً بالقناة)، سيمرر الطلب كإجراء احتياطي
        return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # التحقق من الاشتراك عند الضغط على Start
    if not await is_subscribed(user_id, context.bot):
        keyboard = [[InlineKeyboardButton("📢 اشترك في القناة هنا", url=CHANNEL_INVITE_LINK)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚠️ عذراً! يجب عليك الاشتراك في قناة المؤسسة أولاً لتتمكن من استخدام البوت مجاناً.\n\n"
            "👇 اشترك عبر الرابط أدناه ثم أرسل /start مجدداً للتحقق والتشغيل:",
            reply_markup=reply_markup
        )
        return

    # الأزرار السفلية بعد التعديل (حذف الرقم وإضافة خدماتنا)
    reply_keyboard = [
        [KeyboardButton("🟢 Start")],
        [KeyboardButton("💼 خدماتنا"), KeyboardButton("👥 فريق الدعم الهادي سوفت")]
    ]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text(
        "🚀 أهلاً بك مجدداً في بوت التحميل لمؤسسة الهادي سوفت!\n\n👇 استخدم الأزرار للتنقل أو أرسل رابط الفيديو مباشرة لبدء التحميل.",
        reply_markup=markup
    )

async def handle_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = update.message.chat_id
    user_id = update.effective_user.id
    
    # منع غير المشتركين من استخدام الأزرار والروابط
    if not await is_subscribed(user_id, context.bot):
        keyboard = [[InlineKeyboardButton("📢 اشترك في القناة هنا", url=CHANNEL_INVITE_LINK)]]
        await update.message.reply_text(
            "⚠️ يرجى الاشتراك في القناة أولاً لتفعيل خدمات البوت:\n" + CHANNEL_INVITE_LINK,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if text == "🟢 Start":
        await update.message.reply_text("🔄 البوت نشط وجاهز تماماً، أرسل رابط الفيديو المُراد تحميله الآن.")
        return
    elif text == "💼 خدماتنا":
        await update.message.reply_text("🛠️ **خدمات مؤسسة الهادي سوفت:**\n\n👈 تطوير وترقية البوتات والأنظمة البرمجية بأحدث التقنيات السحابية العالمية.")
        return
    elif text == "👥 فريق الدعم الهادي سوفت":
        await update.message.reply_text(
            "👋 نحن فريق الهادي سوفت للبرمجيات، أخبرنا كيف يمكننا مساعدتك؟\n\n"
            "📥 للتواصل معنا مباشرة عبر الرابط التالي:\n"
            "👉 t.me/AlhadiSoft"
        )
        return

    if text.startswith("http://") or text.startswith("https://"):
        # نص الانتظار الجديد عند طلب إحضار الفيديو
        msg = await update.message.reply_text("⏳ نرجوا الانتظار طلبك قيد التقدم...")
        loop = asyncio.get_event_loop()
        try:
            with yt_dlp.YoutubeDL(PROXY_OPTIONS) as ydl:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(text, download=False))
            title = info.get('title', 'Video')
            user_urls[chat_id] = text
            
            # خيارات الجودات المطلوبة الجديدة (عالية، متوسطة، عادية، ضعيفة + صوت)
            buttons = [
                [InlineKeyboardButton("🎬 جودة عالية (Best)", callback_data="high"), InlineKeyboardButton("🎬 جودة متوسطة (Medium)", callback_data="mid")],
                [InlineKeyboardButton("🎬 جودة عادية (Normal)", callback_data="low"), InlineKeyboardButton("🎬 جودة ضعيفة (Worst)", callback_data="worst")],
                [InlineKeyboardButton("🎵 تحويله إلى صوت MP3", callback_data="audio")]
            ]
            await msg.delete()
            await update.message.reply_text(f"📌 {title}\n\n👇 اختر الجودة أو الصيغة المناسبة للتحميل المعجل:", reply_markup=InlineKeyboardMarkup(buttons))
        except Exception:
            await msg.edit_text("❌ تعذر فحص الرابط. تأكد من صلاحية الفيديو أو جرب رابطاً آخر.")
    else:
        await update.message.reply_text("⚠️ يرجى إرسال رابط فيديو صحيح أو النقر على أحد أزرار الخدمات.")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id, choice = query.message.chat_id, query.data
    url = user_urls.get(chat_id)
    
    if not url:
        await query.edit_message_text("❌ انتهت الجلسة البرمجية الحالية، يرجى إرسال الرابط مجدداً.")
        return
        
    await query.edit_message_text("📥 جاري تحميل الملف ومعالجته عبر السيرفر، يرجى الانتظار...")
    is_audio = (choice == "audio")
    
    # تحديد الجودات برمجياً بناءً على اختيار المستخدم الجديد
    if is_audio:
        fmt = 'bestaudio/best'
    elif choice == "high":
        fmt = 'bestvideo+bestaudio/best'
    elif choice == "mid":
        fmt = 'bestvideo[height<=720]+bestaudio/best'
    elif choice == "low":
        fmt = 'bestvideo[height<=480]+bestaudio/best'
    else:
        fmt = 'worstvideo+worstaudio/worst'
    
    opts = {
        **PROXY_OPTIONS,
        'format': fmt, 
        'outtmpl': f'{chat_id}_file.%(ext)s', 
        'max_filesize': 48*1024*1024,
        'skip_download': False 
    }
    if is_audio:
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
    else:
        opts['merge_output_format'] = 'mp4'

    loop = asyncio.get_event_loop()
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            fn = ydl.prepare_filename(info)
            fn = os.path.splitext(fn)[0] + ('.mp3' if is_audio else '.mp4')
            
        await query.edit_message_text("🚀 اكتمل التحميل! جاري الرفع والتهيئة داخل تيليجرام...")
        with open(fn, 'rb') as f:
            if is_audio:
                await context.bot.send_audio(chat_id=chat_id, audio=f, caption="🎵 تم تحويل وفصل الصوت بنجاح - مؤسسة الهادي سوفت")
            else:
                await context.bot.send_video(chat_id=chat_id, video=f, caption="🎬 تم إحضار الفيديو بنجاح بالجودة المطلوبة - مؤسسة الهادي سوفت")
        if os.path.exists(fn): 
            os.remove(fn)
        user_urls.pop(chat_id, None)
    except Exception:
        await query.edit_message_text("❌ نعتذر، حجم هذا الملف المحدد يتجاوز السعة المجانية المتاحة للبوت (50 ميجا).")

def main():
    threading.Thread(target=start_dummy_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))
    app.add_handler(CallbackQueryHandler(button_click))
    print("Bot is running successfully with new features...")
    app.run_polling()

if __name__ == '__main__':
    main()
    
