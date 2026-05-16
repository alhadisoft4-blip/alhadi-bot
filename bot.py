import os
import asyncio
import http.server
import socketserver
import threading
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import TelegramError
import yt_dlp

TOKEN = '8914679676:AAEeV07KSkz_w5y-qbESc0BTFxB9d5LOvhA'
CHANNEL_ID = '@AlhadiSoft'
CHANNEL_INVITE_LINK = 'https://t.me/+BIHVdkbZ_qY5OTM0'

user_urls = {}

# الإعدادات الاحترافية الشاملة لمحاكاة هواتف الآيفون والأندرويد لتجنب كشف السيرفر
PROXY_OPTIONS = {
    'quiet': True,
    'geo_bypass': True,
    'nocheckcertificate': True,
    'restrictfilenames': True,
    'extractor_args': {
        'youtube': {
            'player_client': ['ios', 'android', 'web'],
            'skip': ['dash', 'hls']
        }
    },
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
        'Accept': '*/*',
        'Accept-Language': 'ar-YE,ar;q=0.9,en-US;q=0.8,en;q=0.7',
    }
}

def start_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"Web server routing active on port {port}")
            httpd.serve_forever()
    except Exception as e:
        print(f"Web server notice: {e}")

async def is_subscribed(user_id: int, bot) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        return False
    except TelegramError:
        return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await is_subscribed(user_id, context.bot):
        keyboard = [[InlineKeyboardButton("📢 اشترك في القناة هنا", url=CHANNEL_INVITE_LINK)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "⚠️ عذراً! يجب عليك الاشتراك في قناة المؤسسة أولاً لتتمكن من استخدام البوت مجاناً.\n\n"
            "👇 اشترك عبر الرابط أدناه ثم أرسل /start مجدداً للتحقق والتشغيل:",
            reply_markup=reply_markup
        )
        return

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
        msg = await update.message.reply_text("⏳ نرجوا الانتظار طلبك قيد التقدم...")
        user_urls[chat_id] = text
        
        buttons = [
            [InlineKeyboardButton("🎬 جودة عالية (Best)", callback_data="high"), InlineKeyboardButton("🎬 جودة متوسطة (Medium)", callback_data="mid")],
            [InlineKeyboardButton("🎬 جودة عادية (Normal)", callback_data="low"), InlineKeyboardButton("🎬 جودة ضعيفة (Worst)", callback_data="worst")],
            [InlineKeyboardButton("🎵 تحويله إلى صوت MP3", callback_data="audio")]
        ]

        # الخيار الأول: الفحص السريع عبر الخادم الخارجي الذكي لتجنب ضغط الـ IP الخاص بريندر
        api_url = f"https://api.cobalt.tools/api/json"
        payload = {"url": text, "filenamePattern": "basic"}
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload, headers=headers, timeout=8) as response:
                    if response.status == 200:
                        res_data = await response.json()
                        if "url" in res_data or res_data.get("status") == "stream":
                            await msg.delete()
                            await update.message.reply_text("📌 تم فحص الرابط ومعالجته بنجاح!\n\n👇 اختر الجودة أو الصيغة المناسبة لبدء الرفع المباشر:", reply_markup=InlineKeyboardMarkup(buttons))
                            return
        except Exception:
            pass # في حال حدوث ضغط على السيرفر الخارجي، يمر الكود فوراً وبسلاسة للمحرك الاحتياطي الداخلي المطور بالأسفل

        # الخيار الثاني التلقائي (المحرك الداخلي المطور بمحاكاة هواتف iOS الصارمة):
        loop = asyncio.get_running_loop()
        try:
            with yt_dlp.YoutubeDL(PROXY_OPTIONS) as ydl:
                info = await loop.run_in_executor(None, lambda: ydl.extract_info(text, download=False))
            title = info.get('title', 'Video')
            await msg.delete()
            await update.message.reply_text(f"📌 {title}\n\n👇 اختر الجودة أو الصيغة المناسبة للتحميل:", reply_markup=InlineKeyboardMarkup(buttons))
        except Exception as e:
            print(f"Final Extraction Error: {e}")
            await msg.edit_text("❌ تعذر جلب تفاصيل هذا الفيديو حالياً بسبب قيود الحماية. يرجى المحاولة مرة أخرى أو تجربة رابط آخر بعد قليل.")
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
        
    await query.edit_message_text("📥 جاري سحب واستخراج الملف عبر المحرك السحابي الآمن، يرجى الانتظار...")
    is_audio = (choice == "audio")
    
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

    loop = asyncio.get_running_loop()
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            fn = ydl.prepare_filename(info)
            fn = os.path.splitext(fn)[0] + ('.mp3' if is_audio else '.mp4')
            
        await query.edit_message_text("🚀 اكتمل المعالجة بنجاح! جاري الرفع الفوري إلى تيليجرام...")
        with open(fn, 'rb') as f:
            if is_audio:
                await context.bot.send_audio(chat_id=chat_id, audio=f, caption="🎵 تم تحويل وفصل الصوت بنجاح - مؤسسة الهادي سوفت")
            else:
                await context.bot.send_video(chat_id=chat_id, video=f, caption="🎬 تم إحضار الفيديو بنجاح بالجودة المطلوبة - مؤسسة الهادي سوفت")
        if os.path.exists(fn): 
            os.remove(fn)
        user_urls.pop(chat_id, None)
    except Exception as e:
        print(f"Final Download Error: {e}")
        await query.edit_message_text("❌ نعتذر، إما أن حجم الملف يتجاوز حد الـ 50 ميجا المتاح مجاناً للبوت، أو أن جودة الفيديو هذه غير متاحة للرابط.")

async def main():
    threading.Thread(target=start_dummy_server, daemon=True).start()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_buttons))
    app.add_handler(CallbackQueryHandler(button_click))
    
    print("Bot startup sequence initialized successfully...")
    
    async with app:
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        while True:
            await asyncio.sleep(3600)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
