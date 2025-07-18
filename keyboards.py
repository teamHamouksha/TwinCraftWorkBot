from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_ID # لاستخدامها في بناء الكيبورد بشكل ديناميكي

# الكيبورد الرئيسي
# سيتم تعديلها في الهاندلر لإضافة زر المشرف بشكل ديناميكي
main_menu_keyboard_base = [
    [KeyboardButton(text="🎞️ فيديوهات 1 دقيقة"), KeyboardButton(text="🎬 تجميعة فيديو 10 دقايق")],
    [KeyboardButton(text="📊 إحصائياتي"), KeyboardButton(text="💢 مشكلة")],
    [KeyboardButton(text="❓ استفسار"), KeyboardButton(text="📋 عن الشغل و تفاصيله")],
    [KeyboardButton(text="🎁 جوايز و هداية للملتزمين")]
]

def get_main_menu_keyboard(user_id: int):
    keyboard = list(main_menu_keyboard_base) # عمل نسخة عشان منعدلش على الأساسي
    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton(text="⚙️ للمشرفين فقط")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=False)

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

# كيبورد قائمة المشرفين
admin_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✉️ رسالة للمستخدمين")],
        [KeyboardButton(text="📈 بيانات وإحصائيات المستخدمين")],
        [KeyboardButton(text="✅ ملتزم ولا غير ملتزم")],
        [KeyboardButton(text="الرجوع للقائمة الرئيسية")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# كيبورد قائمة الالتزام للمشرف
commitment_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="☀️ الشغل اليومي")],
        [KeyboardButton(text="🗓️ الشغل الاسبوعي")],
        [KeyboardButton(text="⭐ الشغل الشهري")],
        [KeyboardButton(text="الرجوع لقائمة المشرف")]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)
