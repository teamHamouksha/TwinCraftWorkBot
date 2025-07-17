from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# الكيبورد الرئيسي
main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎞️ فيديوهات 1 دقيقة"), KeyboardButton(text="🎬 تجميعة فيديو 10 دقايق")],
        [KeyboardButton(text="📊 إحصائياتي"), KeyboardButton(text="💢 مشكلة")],
        [KeyboardButton(text="❓ استفسار"), KeyboardButton(text="📋 عن الشغل و تفاصيله")],
        [KeyboardButton(text="🎁 جوايز و هداية للملتزمين")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# كيبورد الإحصائيات الفرعي
stats_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="اليوم"), KeyboardButton(text="آخر 30 يوم")],
        [KeyboardButton(text="الرجوع للقائمة الرئيسية")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# الأزرار المدمجة لرسالة "عن الشغل وتفاصيله"
about_work_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔘 أنا موافق على الشروط وعايز أبدأ فورًا", callback_data="start_work_agreement")],
        [InlineKeyboardButton(text="🔘 أنا شغال فعلًا معاكم وملتزم", callback_data="already_working")]
    ]
)
