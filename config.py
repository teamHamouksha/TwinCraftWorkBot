import os

# إعدادات البوت
# يفضل دائمًا استخدام متغيرات البيئة لحماية بياناتك الحساسة
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE") # استبدل 'YOUR_BOT_TOKEN_HERE' بتوكن البوت الخاص بك
GROUP_ID = int(os.getenv("GROUP_ID", "-100YOUR_GROUP_CHAT_ID"))  # استبدل بمعرف مجموعة التليجرام الخاصة بك (يجب أن يبدأ بـ -100)
ADMIN_ID = int(os.getenv("ADMIN_ID", "YOUR_ADMIN_ID_HERE"))      # استبدل بمعرف التليجرام الخاص بالمشرف

# مسار قاعدة البيانات
DB_NAME = "bot_data.db"

# حد إرسال الفيديوهات الطويلة بالأيام
LONG_VIDEO_COOLDOWN_DAYS = 3
