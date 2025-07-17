import datetime
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InputMediaVideo, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import GROUP_ID, ADMIN_ID, LONG_VIDEO_COOLDOWN_DAYS
from database import Database
from keyboards import main_menu_keyboard, stats_keyboard, about_work_inline_keyboard
import messages as msg_texts

# تهيئة قاعدة البيانات
db = Database()

# راوتر لمعالجة الرسائل
router = Router()

# تعريف حالات FSM للتسجيل
class RegistrationStates(StatesGroup):
    getting_name = State()
    getting_channel = State()
    getting_age = State() # حالة جديدة للعمر

# تعريف حالات FSM للمشكلة والاستفسار
class IssueQuestionStates(StatesGroup):
    waiting_for_issue = State()
    waiting_for_question = State()

# --- وظائف مساعدة ---
async def send_to_group(bot, video_file: FSInputFile, caption: str):
    """إرسال الفيديو إلى المجموعة المحددة (تم إهمال هذه الدالة حيث سيتم استخدام message.bot.send_video مباشرة لتحويل الفايل_آي_دي)."""
    pass # لم تعد تستخدم، فقط للحفاظ على الهيكل السابق إذا كانت هناك مراجع لها.

# --- معالج أمر /start ---
@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = db.get_user(user_id)

    if user:
        await message.answer(msg_texts.MSG_WELCOME_BACK, reply_markup=main_menu_keyboard)
        await state.clear()
    else:
        await message.answer(msg_texts.MSG_WELCOME_NEW_USER)
        await state.set_state(RegistrationStates.getting_name)

# --- معالج استلام الاسم (للتسجيل) ---
@router.message(StateFilter(RegistrationStates.getting_name))
async def get_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer(msg_texts.MSG_GET_AGE)
    await state.set_state(RegistrationStates.getting_age)

# --- معالج استلام العمر (للتسجيل) ---
@router.message(StateFilter(RegistrationStates.getting_age))
async def get_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        if age <= 0:
            raise ValueError
        await state.update_data(age=age)
        await message.answer(msg_texts.MSG_GET_CHANNEL)
        await state.set_state(RegistrationStates.getting_channel)
    except ValueError:
        await message.answer(msg_texts.MSG_INVALID_AGE)

# --- معالج استلام اسم القناة (للتسجيل) ---
@router.message(StateFilter(RegistrationStates.getting_channel))
async def get_channel(message: Message, state: FSMContext):
    user_data = await state.get_data()
    name = user_data.get("name")
    age = user_data.get("age")
    channel_name = message.text
    user_id = message.from_user.id

    if db.add_user(user_id, name, age, channel_name):
        await message.answer(msg_texts.MSG_REGISTRATION_SUCCESS, reply_markup=main_menu_keyboard)
    else:
        await message.answer(msg_texts.MSG_ALREADY_REGISTERED, reply_markup=main_menu_keyboard)
    await state.clear()

# --- معالج الفيديوهات القصيرة (1 دقيقة) ---
@router.message(F.text == "🎞️ فيديوهات 1 دقيقة")
async def handle_short_video_button(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        await message.answer(msg_texts.MSG_NOT_REGISTERED)
        await state.clear()
        return

    await message.answer(msg_texts.MSG_SHORT_VIDEO_REQUEST)
    await state.set_state("waiting_for_short_video") # حالة مؤقتة لاستقبال الفيديو

@router.message(F.video, StateFilter("waiting_for_short_video"))
async def process_short_video(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        await message.answer(msg_texts.MSG_NOT_REGISTERED)
        await state.clear()
        return

    # لا يوجد تحقق من مدة الفيديو القصير هنا - يتم تحويله مباشرة

    # تسجيل الفيديو في قاعدة البيانات
    db.record_video(user_id, 'short', 1)

    # الحصول على عدد الفيديوهات اليومية والأسبوعية
    short_videos_today = db.get_today_videos_count(user_id, 'short')
    short_videos_weekly = db.get_weekly_videos_count(user_id, 'short')
    long_videos_today_for_caption = db.get_today_videos_count(user_id, 'long') # لغرض الكابشن فقط
    long_videos_weekly_for_caption = db.get_weekly_videos_count(user_id, 'long') # لغرض الكابشن فقط

    # بناء الكابشن
    caption = (f"**فيديو قصير (1 دقيقة)**\n\n"
               f"**اسم المستخدم:** {user.name}\n"
               f"**اسم القناة:** {user.channel_name}\n"
               f"**تاريخ الإرسال:** {datetime.date.today().strftime('%Y-%m-%d')}\n"
               f"**فيديوهات قصيرة اليوم:** {short_videos_today}\n"
               f"**فيديوهات قصيرة الأسبوع:** {short_videos_weekly}\n"
               f"**فيديوهات طويلة اليوم:** {long_videos_today_for_caption}\n" # إضافة عدد الفيديوهات الطويلة في كابشن القصير
               f"**فيديوهات طويلة الأسبوع:** {long_videos_weekly_for_caption}") # إضافة عدد الفيديوهات الطويلة في كابشن القصير

    # إعادة توجيه الفيديو إلى المجموعة مع الكابشن
    try:
        await message.bot.send_video(chat_id=GROUP_ID, video=message.video.file_id, caption=caption, parse_mode='Markdown')
        await message.answer("✅ تم استلام الفيديو القصير وإرساله للمجموعة.")
    except Exception as e:
        await message.answer(f"حدث خطأ أثناء إرسال الفيديو للمجموعة: {e}")

    # رسائل تحفيزية بناءً على عدد الفيديوهات القصيرة اليومية
    if short_videos_today < 3:
        await message.answer(msg_texts.MSG_SHORT_VIDEO_COUNT.format(count=short_videos_today))
    elif short_videos_today == 3:
        await message.answer(msg_texts.MSG_SHORT_VIDEO_COMPLETED)
    elif short_videos_today > 3:
        await message.answer(msg_texts.MSG_SHORT_VIDEO_OVER_REQUIRED_COUNT.format(count=short_videos_today))

    # لا مسح للحالة هنا إذا كان المستخدم سيرسل المزيد في نفس السياق
    # await state.clear() # يمكن مسحها إذا كان المطلوب أن ينتهي كل إرسال بحالة جديدة

# --- معالج الفيديوهات الطويلة (10 دقائق أو أكثر) ---
@router.message(F.text == "🎬 تجميعة فيديو 10 دقايق")
async def handle_long_video_button(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        await message.answer(msg_texts.MSG_NOT_REGISTERED)
        await state.clear()
        return

    # التحقق من المدة الزمنية بين إرسال الفيديوهات الطويلة
    if user.last_long_video_sent:
        time_diff = datetime.datetime.now() - user.last_long_video_sent
        if time_diff.days < LONG_VIDEO_COOLDOWN_DAYS:
            remaining_days = LONG_VIDEO_COOLDOWN_DAYS - time_diff.days
            await message.answer(msg_texts.MSG_LONG_VIDEO_COOLDOWN.format(remaining_days, user.last_long_video_sent.strftime('%Y-%m-%d')))
            await state.clear()
            return

    await message.answer(msg_texts.MSG_LONG_VIDEO_REQUEST.format(LONG_VIDEO_COOLDOWN_DAYS)) # رسالة تطلب فيديو كل 3 أيام عند الضغط
    await state.set_state("waiting_for_long_video") # حالة مؤقتة لاستقبال الفيديو

@router.message(F.video, StateFilter("waiting_for_long_video"))
async def process_long_video(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        await message.answer(msg_texts.MSG_NOT_REGISTERED)
        await state.clear()
        return

    video_duration = message.video.duration
    # يعتبر الفيديو طويلًا إذا كانت مدته 5 دقائق (300 ثانية) أو أكثر
    if video_duration < 300: # تم تغيير الحد الأدنى للمدة إلى 300 ثانية (5 دقائق)
        await message.answer(msg_texts.MSG_INVALID_LONG_VIDEO)
        return

    # تسجيل الفيديو في قاعدة البيانات
    db.record_video(user_id, 'long', 10)
    db.update_last_long_video_sent(user_id)

    # الحصول على عدد الفيديوهات اليومية والأسبوعية
    short_videos_today_for_caption = db.get_today_videos_count(user_id, 'short') # لغرض الكابشن فقط
    short_videos_weekly_for_caption = db.get_weekly_videos_count(user_id, 'short') # لغرض الكابشن فقط
    long_videos_today = db.get_today_videos_count(user_id, 'long')
    long_videos_weekly = db.get_weekly_videos_count(user_id, 'long')

    # بناء الكابشن
    caption = (f"**فيديو طويل (5 دقائق أو أكثر)**\n\n"
               f"**اسم المستخدم:** {user.name}\n"
               f"**اسم القناة:** {user.channel_name}\n"
               f"**تاريخ الإرسال:** {datetime.date.today().strftime('%Y-%m-%d')}\n"
               f"**فيديوهات قصيرة اليوم:** {short_videos_today_for_caption}\n"
               f"**فيديوهات قصيرة الأسبوع:** {short_videos_weekly_for_caption}\n"
               f"**فيديوهات طويلة اليوم:** {long_videos_today}\n"
               f"**فيديوهات طويلة الأسبوع:** {long_videos_weekly}")

    # إعادة توجيه الفيديو إلى المجموعة مع الكابشن
    try:
        await message.bot.send_video(chat_id=GROUP_ID, video=message.video.file_id, caption=caption, parse_mode='Markdown')
        await message.answer("✅ تم استلام الفيديو الطويل وإرساله للمجموعة.")
    except Exception as e:
        await message.answer(f"حدث خطأ أثناء إرسال الفيديو للمجموعة: {e}")

    await state.clear() # مسح الحالة بعد استقبال الفيديو

# --- معالج الإحصائيات الشخصية ---
@router.message(F.text == "📊 إحصائياتي")
async def handle_stats_button(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        await message.answer(msg_texts.MSG_NOT_REGISTERED)
        await state.clear()
        return

    await message.answer(msg_texts.MSG_CHOOSE_STATS_PERIOD, reply_markup=stats_keyboard)
    await state.set_state("waiting_for_stats_choice")

@router.message(F.text == "اليوم", StateFilter("waiting_for_stats_choice"))
async def show_today_stats(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        await message.answer(msg_texts.MSG_NOT_REGISTERED)
        await state.clear()
        return

    short_count = db.get_today_videos_count(user_id, 'short')
    long_count = db.get_today_videos_count(user_id, 'long')

    session = db.get_session()
    today = datetime.date.today()
    videos_today = session.query(db.Video).filter(
        db.Video.user_id == user_id,
        func.DATE(db.Video.sent_at) == today
    ).all()
    session.close()
    points_today = sum(video.points_earned for video in videos_today)

    await message.answer(msg_texts.MSG_STATS_TODAY.format(short_count=short_count, long_count=long_count, points_today=points_today),
                         reply_markup=main_menu_keyboard)
    await state.clear()

@router.message(F.text == "آخر 30 يوم", StateFilter("waiting_for_stats_choice"))
async def show_30_days_stats(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        await message.answer(msg_texts.MSG_NOT_REGISTERED)
        await state.clear()
        return

    videos_last_30_days = db.get_user_videos_in_last_30_days(user_id)

    short_total = sum(1 for v in videos_last_30_days if v.type == 'short')
    long_total = sum(1 for v in videos_last_30_days if v.type == 'long')
    points_total = sum(v.points_earned for v in videos_last_30_days)

    await message.answer(msg_texts.MSG_STATS_LAST_30_DAYS.format(short_total=short_total, long_total=long_total, points_total=points_total),
                         reply_markup=main_menu_keyboard)
    await state.clear()

@router.message(F.text == "الرجوع للقائمة الرئيسية", StateFilter("waiting_for_stats_choice"))
async def back_to_main_menu_from_stats(message: Message, state: FSMContext):
    await message.answer(msg_texts.MSG_WELCOME_BACK, reply_markup=main_menu_keyboard)
    await state.clear()

# --- معالج زر (💢 مشكلة) ---
@router.message(F.text == "💢 مشكلة")
async def handle_issue_button(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        await message.answer(msg_texts.MSG_NOT_REGISTERED)
        await state.clear()
        return
    await message.answer(msg_texts.MSG_REPORT_ISSUE)
    await state.set_state(IssueQuestionStates.waiting_for_issue)

@router.message(StateFilter(IssueQuestionStates.waiting_for_issue))
async def process_issue(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        await message.answer(msg_texts.MSG_NOT_REGISTERED)
        await state.clear()
        return

    issue_text = message.text
    caption = (f"💢 **مشكلة من مستخدم**\n\n"
               f"**اسم المستخدم:** {user.name}\n"
               f"**اسم القناة:** {user.channel_name}\n"
               f"**التاريخ:** {datetime.date.today().strftime('%Y-%m-%d')}\n\n"
               f"**المشكلة:**\n{issue_text}")
    try:
        await message.bot.send_message(chat_id=GROUP_ID, text=caption, parse_mode='Markdown')
        await message.answer(msg_texts.MSG_ISSUE_RECEIVED, reply_markup=main_menu_keyboard)
    except Exception as e:
        await message.answer(f"حدث خطأ أثناء إرسال المشكلة للمجموعة: {e}")
    await state.clear()

# --- معالج زر (❓ استفسار) ---
@router.message(F.text == "❓ استفسار")
async def handle_question_button(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        await message.answer(msg_texts.MSG_NOT_REGISTERED)
        await state.clear()
        return
    await message.answer(msg_texts.MSG_ASK_QUESTION)
    await state.set_state(IssueQuestionStates.waiting_for_question)

@router.message(StateFilter(IssueQuestionStates.waiting_for_question))
async def process_question(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        await message.answer(msg_texts.MSG_NOT_REGISTERED)
        await state.clear()
        return

    question_text = message.text
    caption = (f"❓ **استفسار من مستخدم**\n\n"
               f"**اسم المستخدم:** {user.name}\n"
               f"**اسم القناة:** {user.channel_name}\n"
               f"**التاريخ:** {datetime.date.today().strftime('%Y-%m-%d')}\n\n"
               f"**الاستفسار:**\n{question_text}")
    try:
        await message.bot.send_message(chat_id=GROUP_ID, text=caption, parse_mode='Markdown')
        await message.answer(msg_texts.MSG_QUESTION_RECEIVED, reply_markup=main_menu_keyboard)
    except Exception as e:
        await message.answer(f"حدث خطأ أثناء إرسال الاستفسار للمجموعة: {e}")
    await state.clear()

# --- معالج زر (📋 عن الشغل و تفاصيله) ---
@router.message(F.text == "📋 عن الشغل و تفاصيله")
async def handle_about_work_button(message: Message):
    await message.answer(msg_texts.MSG_ABOUT_WORK, parse_mode='Markdown', reply_markup=about_work_inline_keyboard)

@router.callback_query(F.data == "start_work_agreement")
async def process_start_work_agreement(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    user = db.get_user(user_id)

    if not user:
        await callback_query.message.answer(msg_texts.MSG_NOT_REGISTERED, reply_markup=main_menu_keyboard)
        await callback_query.answer()
        return

    agreement_message_to_group = msg_texts.MSG_AGREEMENT_TO_GROUP.format(
        name=user.name,
        age=user.age if user.age else "غير محدد", # التعامل مع العمر إذا لم يكن متاحًا
        channel_name=user.channel_name,
        date=datetime.date.today().strftime('%Y-%m-%d')
    )
    try:
        await callback_query.bot.send_message(chat_id=GROUP_ID, text=agreement_message_to_group, parse_mode='Markdown')
        await callback_query.answer("تم إبلاغ المجموعة بموافقتك على الشروط! 🎉")
    except Exception as e:
        await callback_query.answer(f"حدث خطأ أثناء إرسال رسالة الموافقة للمجموعة: {e}")

@router.callback_query(F.data == "already_working")
async def process_already_working(callback_query: CallbackQuery):
    await callback_query.message.answer(msg_texts.MSG_ALREADY_WORKING_MOTIVATION, parse_mode='Markdown', reply_markup=main_menu_keyboard)
    await callback_query.answer("رسالة تحفيزية!")


# --- معالج زر (🎁 جوايز و هداية للملتزمين) ---
@router.message(F.text == "🎁 جوايز و هداية للملتزمين")
async def handle_gifts_button(message: Message):
    await message.answer(msg_texts.MSG_GIFTS_PROMO, parse_mode='Markdown')

# --- معالج أمر المشرف /تقرير_النشاط ---
@router.message(Command("تقرير_النشاط"))
async def admin_report_command(message: Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer(msg_texts.MSG_ADMIN_ONLY)
        return

    all_users = db.get_all_users()
    total_users = len(all_users)
    total_short_videos_all = db.get_total_videos_count('short')
    total_long_videos_all = db.get_total_videos_count('long')

    users_details_list = []
    if all_users:
        # ترتيب المستخدمين حسب النقاط لكل المستخدمين في التقرير المفصل
        sorted_users = sorted(all_users, key=lambda user: user.points, reverse=True)
        for i, user in enumerate(sorted_users):
            user_short_videos = db.get_total_short_videos_sent_by_user(user.user_id)
            user_long_videos = db.get_total_long_videos_sent_by_user(user.user_id)
            last_long_video_date = user.last_long_video_sent.strftime('%Y-%m-%d %H:%M') if user.last_long_video_sent else "لا يوجد"
            users_details_list.append(
                f"**{i+1}. الاسم:** {user.name}\n"
                f"   **العمر:** {user.age if user.age else 'غير محدد'}\n"
                f"   **القناة:** {user.channel_name}\n"
                f"   **النقاط:** {user.points}\n"
                f"   **فيديوهات قصيرة إجمالاً:** {user_short_videos}\n"
                f"   **فيديوهات طويلة إجمالاً:** {user_long_videos}\n"
                f"   **آخر فيديو طويل:** {last_long_video_date}\n"
                f"   ---"
            )
    else:
        users_details_list.append(msg_texts.MSG_NO_USERS_DATA)

    report = msg_texts.MSG_FULL_REPORT_SUMMARY.format(
        total_users=total_users,
        total_short_videos=total_short_videos_all,
        total_long_videos=total_long_videos_all,
        users_details="\n".join(users_details_list)
    )
    await message.answer(report, parse_mode='Markdown')

# --- معالج أي رسالة أخرى لا تتطابق مع الأوامر أو حالات FSM ---
@router.message()
async def echo_message(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        return # إذا كان المستخدم في حالة FSM، لا تفعل شيئاً هنا

    # إذا لم يكن في حالة FSM، وكان مسجلاً، أعد له القائمة الرئيسية
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        await message.answer(msg_texts.MSG_NOT_REGISTERED) # لا نرسل كيبورد هنا ليضطر لـ /start
    else:
        await message.answer(msg_texts.MSG_WELCOME_BACK, reply_markup=main_menu_keyboard)
