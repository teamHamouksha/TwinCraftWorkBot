import os

# إعدادات البوت
# يفضل دائمًا استخدام متغيرات البيئة لحماية بياناتك الحساسة
BOT_TOKEN = os.getenv("BOT_TOKEN", "7762679817:AAG4CYtN2Tnxnpeu07r5ew8mszNEFZUR3zg") # استبدل 'YOUR_BOT_TOKEN_HERE' بتوكن البوت الخاص بك
GROUP_ID = int(os.getenv("GROUP_ID", "-1002826113800"))  # استبدل بمعرف مجموعة التليجرام الخاصة بك (يجب أن يبدأ بـ -100)
ADMIN_ID = int(os.getenv("ADMIN_ID", "6660295630"))      # استبدل بمعرف التليجرام الخاص بالمشرف

# مسار قاعدة البيانات
DB_NAME = "bot_data.db"

# حد إرسال الفيديوهات الطويلة بالأيام (فيديو واحد كل 3 أيام)
LONG_VIDEO_COOLDOWN_DAYS = 3

# عدد الفيديوهات القصيرة المطلوبة يومياً (هذا يمكن أن يصبح إعداداً للمشرف مستقبلاً)
REQUIRED_SHORT_VIDEOS_DAILY = 3
