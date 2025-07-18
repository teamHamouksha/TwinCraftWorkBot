import datetime
from aiogram import Router, F, Bot
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InputMediaVideo, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import GROUP_ID, ADMIN_ID, LONG_VIDEO_COOLDOWN_DAYS, REQUIRED_SHORT_VIDEOS_DAILY
from database import Database
from keyboards import get_main_menu_keyboard, stats_keyboard, about_work_inline_keyboard, admin_menu_keyboard, commitment_menu_keyboard
import messages as msg_texts

# تهيئة قاعدة البيانات
db = Database()

# راوتر لمعالجة الرسائل
router = Router()

# تعريف حالات FSM للتسجيل
class RegistrationStates(StatesGroup):
    getting_name = State()
    getting_age = State()
    getting_channel = State()

# تعريف حالات FSM للمشكلة والاستفسار
class IssueQuestionStates(StatesGroup):
    waiting_for_issue = State()
    waiting_for_question = State()

# تعريف حالات FSM للمشرف
class AdminStates(StatesGroup):
    in_admin_panel = State()
    waiting_for_broadcast_message = State()
    in_commitment_menu = State()

# --- وظائف مساعدة ---
def is_admin(user_id: int) -> bool:
    """التحقق مما إذا كان المستخدم مشرفاً."""
    return user_id == ADMIN_ID

async def _get_user_stats_for_caption(user_id: int):
    """جلب إحصائيات المستخدم اللازمة لتنسيق الكابشن الموحد."""
    user = db.get_user(user_id)
    if not user:
        return None, None, None, None, None, None # ارجع قيم None إذا لم يتم العثور على المستخدم

    short_today = db.get_today_videos_count(user_id, 'short')
    short_weekly = db.get_weekly_videos_count(user_id, 'short')
    long_today = db.get_today_videos_count(user_id, 'long')
    long_weekly = db.get_weekly_videos_count(user_id, 'long')
    
    return user, short_today, short_weekly, long_today, long_weekly

async def _generate_standard_group_caption(user_id: int, type_label: str, additional_info: str = ""):
    """توليد الكابشن الموحد لرسائل المجموعة."""
    user, short_today, short_weekly, long_today, long_weekly = await _get_user_stats_for_caption(user_id)
    
    if not user:
        return "بيانات المستخدم غير متوفرة."

    return msg_texts.GROUP_CAPTION_FORMAT.format(
        type_label=type_label,
        name=user.name,
        channel_name=user.channel_name,
        points=user.points,
        short_today=short_today,
        short_weekly=short_weekly,
        long_today=long_today,
        long_weekly=long_weekly,
        send_date=datetime.date.today().strftime('%Y-%m-%d'),
        additional_info=additional_info # لإضافة تفاصيل المشكلة/الاستفسار
    )

# --- معالج أمر /start ---
@router.message(Command("start"))
async def start_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = db.get_user(user_id)

    if user:
        await message.answer(msg_texts.MSG_WELCOME_BACK, reply_markup=get_main_menu_keyboard(user_id))
        await state.clear()
    else:
        await message.answer(msg_texts.MSG_WELCOME_NEW_USER)
        await state.set_state(RegistrationStates.getting_name)

# --- معالج استلام الاسم (للتسجيل) ---
@router.message(StateFilter(RegistrationStates.getting_name))
async def get_name(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("الرجاء إدخال اسم صحيح.")
        return
    await state.update_data(name=message.text)
    await message.answer(msg_texts.MSG_GET_AGE)
    await state.set_state(RegistrationStates.getting_age)

# --- معالج استلام العمر (للتسجيل) ---
@router.message(StateFilter(RegistrationStates.getting_age))
async def get_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        if age <= 0 or age > 120: # حدود منطقية للعمر
            raise ValueError
        await state.update_data(age=age)
        await message.answer(msg_texts.MSG_GET_CHANNEL)
        await state.set_state(RegistrationStates.getting_channel)
    except ValueError:
        await message.answer(msg_texts.MSG_INVALID_AGE)

# --- معالج استلام اسم القناة (للتسجيل) ---
@router.message(StateFilter(RegistrationStates.getting_channel))
async def get_channel(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("الرجاء إدخال اسم قناة صحيح.")
        return
    user_data = await state.get_data()
    name = user_data.get("name")
    age = user_data.get("age")
    channel_name = message.text
    user_id = message.from_user.id

    if db.add_user(user_id, name, age, channel_name):
        await message.answer(msg_texts.MSG_REGISTRATION_SUCCESS, reply_markup=get_main_menu_keyboard(user_id))
    else:
        await message.answer(msg_texts.MSG_ALREADY_REGISTERED, reply_markup=get_main_menu_keyboard(user_id))
    await state.clear()

# --- معالج زر الرجوع للقائمة الرئيسية (من أي مكان) ---
@router.message(F.text == "الرجوع للقائمة الرئيسية")
async def back_to_main_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(msg_texts.MSG_WELCOME_BACK, reply_markup=get_main_menu_keyboard(message.from_user.id))

# --- معالج الفيديوهات القصيرة (1 دقيقة) ---
@router.message(F.text == "🎞️ فيديوهات 1 دقيقة")
async def handle_short_video_button(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        await message.answer(msg_texts.MSG_NOT_REGISTERED)
        await state.clear()
        return

    await message.answer(msg_texts.MSG_SHORT_VIDEO_REQUEST.format(required_count=REQUIRED_SHORT_VIDEOS_DAILY))
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
    db.update_last_activity(user_id) # تحديث آخر نشاط

    # بناء الكابشن الموحد للمجموعة
    caption = await _generate_standard_group_caption(
        user_id, 
        type_label="فيديو قصير (1 دقيقة)"
    )

    # إعادة توجيه الفيديو إلى المجموعة مع الكابشن
    try:
        await message.bot.send_video(chat_id=GROUP_ID, video=message.video.file_id, caption=caption, parse_mode='Markdown')
        await message.answer("✅ تم استلام الفيديو القصير وإرساله للمجموعة.")
    except Exception as e:
        await message.answer(f"حدث خطأ أثناء إرسال الفيديو للمجموعة: {e}")
        # يمكن تسجيل الخطأ في اللوج
        print(f"Error sending short video to group: {e}")


    # رسائل تحفيزية بناءً على عدد الفيديوهات القصيرة اليومية
    short_videos_today = db.get_today_videos_count(user_id, 'short')
    if short_videos_today < REQUIRED_SHORT_VIDEOS_DAILY:
        await message.answer(msg_texts.MSG_SHORT_VIDEO_COUNT.format(count=short_videos_today, required_count=REQUIRED_SHORT_VIDEOS_DAILY))
    elif short_videos_today == REQUIRED_SHORT_VIDEOS_DAILY:
        await message.answer(msg_texts.MSG_SHORT_VIDEO_COMPLETED.format(required_count=REQUIRED_SHORT_VIDEOS_DAILY))
    elif short_videos_today > REQUIRED_SHORT_VIDEOS_DAILY:
        await message.answer(msg_texts.MSG_SHORT_VIDEO_OVER_REQUIRED_COUNT.format(count=short_videos_today))

    # لا يتم مسح الحالة هنا لتمكين المستخدم من إرسال فيديوهات متتالية

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

    await message.answer(msg_texts.MSG_LONG_VIDEO_REQUEST.format(LONG_VIDEO_COOLDOWN_DAYS))
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
    if video_duration < 300:
        await message.answer(msg_texts.MSG_INVALID_LONG_VIDEO)
        return

    # تسجيل الفيديو في قاعدة البيانات
    db.record_video(user_id, 'long', 10)
    db.update_last_long_video_sent(user_id)
    db.update_last_activity(user_id) # تحديث آخر نشاط

    # بناء الكابشن الموحد للمجموعة
    caption = await _generate_standard_group_caption(
        user_id, 
        type_label="فيديو طويل (10 دقائق أو أكثر)" # النص الظاهر 10 دقائق، لكن التحقق 5 دقائق
    )

    # إعادة توجيه الفيديو إلى المجموعة مع الكابشن
    try:
        await message.bot.send_video(chat_id=GROUP_ID, video=message.video.file_id, caption=caption, parse_mode='Markdown')
        await message.answer("✅ تم استلام الفيديو الطويل وإرساله للمجموعة.")
    except Exception as e:
        await message.answer(f"حدث خطأ أثناء إرسال الفيديو للمجموعة: {e}")
        print(f"Error sending long video to group: {e}")

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

    await message.answer(
        msg_texts.MSG_STATS_TODAY.format(
            short_count=short_count, 
            long_count=long_count, 
            points_today=points_today,
            motivation_msg=msg_texts.MSG_STATS_MOTIVATION
        ),
        reply_markup=get_main_menu_keyboard(user_id)
    )
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

    await message.answer(
        msg_texts.MSG_STATS_LAST_30_DAYS.format(
            short_total=short_total, 
            long_total=long_total, 
            points_total=points_total,
            motivation_msg=msg_texts.MSG_STATS_MOTIVATION
        ),
        reply_markup=get_main_menu_keyboard(user_id)
    )
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
    db.update_last_activity(user_id) # تحديث آخر نشاط

    # بناء الكابشن الموحد للمجموعة
    additional_info = f"**المشكلة:**\n{issue_text}"
    caption = await _generate_standard_group_caption(
        user_id,
        type_label="💢 مشكلة من مستخدم",
        additional_info=additional_info
    )
    
    try:
        await message.bot.send_message(chat_id=GROUP_ID, text=caption, parse_mode='Markdown')
        await message.answer(msg_texts.MSG_ISSUE_RECEIVED_CONFIRMATION, reply_markup=get_main_menu_keyboard(user_id))
    except Exception as e:
        await message.answer(f"حدث خطأ أثناء إرسال المشكلة: {e}")
        print(f"Error sending issue to group: {e}")
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
    db.update_last_activity(user_id) # تحديث آخر نشاط

    # بناء الكابشن الموحد للمجموعة
    additional_info = f"**الاستفسار:**\n{question_text}"
    caption = await _generate_standard_group_caption(
        user_id,
        type_label="❓ استفسار من مستخدم",
        additional_info=additional_info
    )

    try:
        await message.bot.send_message(chat_id=GROUP_ID, text=caption, parse_mode='Markdown')
        await message.answer(msg_texts.MSG_QUESTION_RECEIVED_CONFIRMATION, reply_markup=get_main_menu_keyboard(user_id))
    except Exception as e:
        await message.answer(f"حدث خطأ أثناء إرسال الاستفسار: {e}")
        print(f"Error sending question to group: {e}")
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
        await callback_query.message.answer(msg_texts.MSG_NOT_REGISTERED, reply_markup=get_main_menu_keyboard(user_id))
        await callback_query.answer()
        return

    # بناء الكابشن الموحد للمجموعة
    additional_info = msg_texts.MSG_AGREEMENT_TO_GROUP.format(
        name=user.name,
        age=user.age if user.age else "غير محدد",
        channel_name=user.channel_name,
        date=datetime.date.today().strftime('%Y-%m-%d')
    )
    # ملاحظة: هذا الكابشن لن يتبع التنسيق الكامل لعدم وجود بيانات الفيديو هنا، ولكن سأحاول جعله متوافقاً قدر الإمكان
    # أو يمكن إرسالها كرسالة نصية عادية للمجموعة دون الحاجة لبيانات الفيديو
    
    caption_for_group = (
        f"**عميل جديد وافق على الشروط وبدأ العمل!**\n\n"
        f"**اسم المستخدم:** {user.name}\n"
        f"**اسم القناة:** {user.channel_name}\n"
        f"**عدد النقاط:** {user.points}\n"
        f"**تاريخ الموافقة:** {datetime.date.today().strftime('%Y-%m-%d')}"
    )

    try:
        await callback_query.bot.send_message(chat_id=GROUP_ID, text=caption_for_group, parse_mode='Markdown')
        await callback_query.answer("تم إبلاغ المجموعة بموافقتك على الشروط! 🎉")
    except Exception as e:
        await callback_query.answer(f"حدث خطأ أثناء إرسال رسالة الموافقة للمجموعة: {e}")

@router.callback_query(F.data == "already_working")
async def process_already_working(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    await callback_query.message.answer(msg_texts.MSG_ALREADY_WORKING_MOTIVATION, parse_mode='Markdown', reply_markup=get_main_menu_keyboard(user_id))
    await callback_query.answer("رسالة تحفيزية!")


# --- معالج زر (🎁 جوايز و هداية للملتزمين) ---
@router.message(F.text == "🎁 جوايز و هداية للملتزمين")
async def handle_gifts_button(message: Message):
    await message.answer(msg_texts.MSG_GIFTS_PROMO, parse_mode='Markdown', reply_markup=get_main_menu_keyboard(message.from_user.id))

# --- لوحة المشرفين فقط ---
@router.message(F.text == "⚙️ للمشرفين فقط")
async def admin_panel_button(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer(msg_texts.MSG_ADMIN_ONLY)
        return
    await message.answer(msg_texts.MSG_ADMIN_MENU, reply_markup=admin_menu_keyboard)
    await state.set_state(AdminStates.in_admin_panel)

# --- رسالة للمستخدمين (Broadcast) ---
@router.message(F.text == "✉️ رسالة للمستخدمين", StateFilter(AdminStates.in_admin_panel))
async def admin_broadcast_prompt(message: Message, state: FSMContext):
    await message.answer(msg_texts.MSG_BROADCAST_PROMPT, reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="إلغاء الإرسال")]], resize_keyboard=True))
    await state.set_state(AdminStates.waiting_for_broadcast_message)

@router.message(StateFilter(AdminStates.waiting_for_broadcast_message), F.text == "إلغاء الإرسال")
async def cancel_broadcast(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("✅ تم إلغاء عملية الإرسال.", reply_markup=admin_menu_keyboard)
    await state.set_state(AdminStates.in_admin_panel)

@router.message(StateFilter(AdminStates.waiting_for_broadcast_message))
async def admin_broadcast_message(message: Message, state: FSMContext, bot: Bot):
    await state.clear() # مسح الحالة بعد استلام الرسالة
    
    all_users = db.get_all_users()
    sent_count = 0
    failed_count = 0

    for user in all_users:
        if user.user_id == ADMIN_ID: # لا ترسل الرسالة للمشرف نفسه مرة أخرى
            continue
        try:
            if message.text:
                await bot.send_message(chat_id=user.user_id, text=message.text, parse_mode='Markdown')
            elif message.photo:
                await bot.send_photo(chat_id=user.user_id, photo=message.photo[-1].file_id, caption=message.caption, parse_mode='Markdown')
            elif message.video:
                await bot.send_video(chat_id=user.user_id, video=message.video.file_id, caption=message.caption, parse_mode='Markdown')
            elif message.audio:
                await bot.send_audio(chat_id=user.user_id, audio=message.audio.file_id, caption=message.caption, parse_mode='Markdown')
            elif message.document:
                await bot.send_document(chat_id=user.user_id, document=message.document.file_id, caption=message.caption, parse_mode='Markdown')
            else:
                # Handle other types if necessary, or just skip
                pass
            sent_count += 1
            await asyncio.sleep(0.05) # تأخير بسيط لتجنب حدود معدل تليجرام
        except Exception as e:
            failed_count += 1
            print(f"Failed to send broadcast to user {user.user_id}: {e}")
            # ممكن تسجل المستخدمين اللي فشلت في إرسال الرسالة لهم هنا

    if sent_count > 0:
        await message.answer(msg_texts.MSG_BROADCAST_SUCCESS.format(count=sent_count), reply_markup=admin_menu_keyboard)
    if failed_count > 0:
        await message.answer(msg_texts.MSG_BROADCAST_FAILED.format(failed_count=failed_count), reply_markup=admin_menu_keyboard)
    
    await state.set_state(AdminStates.in_admin_panel) # الرجوع لحالة لوحة المشرف

# --- بيانات وإحصائيات المستخدمين (للمشرف) ---
@router.message(F.text == "📈 بيانات وإحصائيات المستخدمين", StateFilter(AdminStates.in_admin_panel))
async def admin_users_stats_report(message: Message):
    all_users = db.get_all_users()
    total_users = len(all_users)
    total_short_videos_all = db.get_total_videos_count('short')
    total_long_videos_all = db.get_total_videos_count('long')

    users_details_list = []
    if all_users:
        sorted_users = sorted(all_users, key=lambda user: user.points, reverse=True) # الترتيب حسب النقاط
        for i, user in enumerate(sorted_users):
            user_short_videos = db.get_total_short_videos_sent_by_user(user.user_id)
            user_long_videos = db.get_total_long_videos_sent_by_user(user.user_id)
            
            last_video = db.get_last_video_sent_details(user.user_id)
            last_video_details = "لا يوجد"
            if last_video:
                last_video_type = "قصير" if last_video.type == 'short' else "طويل"
                last_video_details = f"{last_video_type} في {last_video.sent_at.strftime('%Y-%m-%d %H:%M')}"

            users_details_list.append(
                msg_texts.MSG_USER_REPORT_DETAIL.format(
                    index=i+1,
                    name=user.name,
                    user_id=user.user_id,
                    age=user.age if user.age else 'غير محدد',
                    channel_name=user.channel_name,
                    points=user.points,
                    reg_date=user.registration_date.strftime('%Y-%m-%d %H:%M'),
                    total_short=user_short_videos,
                    total_long=user_long_videos,
                    last_video_details=last_video_details
                )
            )
    else:
        users_details_list.append(msg_texts.MSG_NO_USERS_DATA)

    report = msg_texts.MSG_ALL_USERS_REPORT_HEADER.format(
        total_users=total_users,
        total_short_videos=total_short_videos_all,
        total_long_videos=total_long_videos_all
    ) + "\n".join(users_details_list)

    # يمكن أن يكون التقرير طويلاً، لذا نقسمه إلى رسائل
    chunk_size = 4000 # حد أقصى للرسالة في تليجرام
    for i in range(0, len(report), chunk_size):
        await message.answer(report[i:i+chunk_size], parse_mode='Markdown')

# --- ملتزم ولا غير ملتزم (للمشرف) ---
@router.message(F.text == "✅ ملتزم ولا غير ملتزم", StateFilter(AdminStates.in_admin_panel))
async def admin_commitment_menu(message: Message, state: FSMContext):
    await message.answer(msg_texts.MSG_COMMITMENT_MENU, reply_markup=commitment_menu_keyboard)
    await state.set_state(AdminStates.in_commitment_menu)

# --- معالج الرجوع لقائمة المشرف من قائمة الالتزام ---
@router.message(F.text == "الرجوع لقائمة المشرف", StateFilter(AdminStates.in_commitment_menu))
async def back_to_admin_menu_from_commitment(message: Message, state: FSMContext):
    await message.answer(msg_texts.MSG_ADMIN_MENU, reply_markup=admin_menu_keyboard)
    await state.set_state(AdminStates.in_admin_panel)

# --- الشغل اليومي للمشرف ---
@router.message(F.text == "☀️ الشغل اليومي", StateFilter(AdminStates.in_commitment_menu))
async def admin_daily_commitment_report(message: Message):
    today = datetime.date.today()
    users_data = db.get_users_by_activity_in_period(today, today)

    report_parts = [msg_texts.MSG_COMMITMENT_REPORT_HEADER.format(period="لليوم")]
    
    if not users_data:
        report_parts.append(msg_texts.MSG_NO_COMMITMENT_DATA_FOR_PERIOD)
    else:
        for i, data in enumerate(users_data):
            user = data['user']
            commitment_status = ""
            if data['short_videos_count'] >= REQUIRED_SHORT_VIDEOS_DAILY:
                commitment_status = msg_texts.MSG_USER_MET_TARGET.format(
                    count=data['short_videos_count'], 
                    required_count=REQUIRED_SHORT_VIDEOS_DAILY
                )
            elif data['has_activity_in_period']: # لو عنده أي نشاط بس مكملش المطلوب
                commitment_status = msg_texts.MSG_USER_MISSED_TARGET.format(
                    count=data['short_videos_count'], 
                    required_count=REQUIRED_SHORT_VIDEOS_DAILY
                )
            else: # لو مفيش أي نشاط أصلاً
                commitment_status = msg_texts.MSG_USER_NO_ACTIVITY
            
            report_parts.append(
                msg_texts.MSG_COMMITMENT_USER_DETAIL.format(
                    index=i+1,
                    name=user.name,
                    channel_name=user.channel_name,
                    age=user.age if user.age else 'غير محدد',
                    reg_date=data['registration_date_str'],
                    points=data['points_earned'],
                    short_count=data['short_videos_count'],
                    long_count=data['long_videos_count'],
                    period_text="لليوم",
                    commitment_status=commitment_status
                )
            )
    
    full_report = "\n".join(report_parts)
    chunk_size = 4000
    for i in range(0, len(full_report), chunk_size):
        await message.answer(full_report[i:i+chunk_size], parse_mode='Markdown')

# --- الشغل الاسبوعي للمشرف ---
@router.message(F.text == "🗓️ الشغل الاسبوعي", StateFilter(AdminStates.in_commitment_menu))
async def admin_weekly_commitment_report(message: Message):
    today = datetime.date.today()
    start_of_week = today - datetime.timedelta(days=today.weekday())
    users_data = db.get_users_by_activity_in_period(start_of_week, today)

    report_parts = [msg_texts.MSG_COMMITMENT_REPORT_HEADER.format(period="للأسبوع")]
    
    if not users_data:
        report_parts.append(msg_texts.MSG_NO_COMMITMENT_DATA_FOR_PERIOD)
    else:
        for i, data in enumerate(users_data):
            user = data['user']
            commitment_status = ""
            # للالتزام الأسبوعي، ممكن نتحقق من متوسط الأداء أو إجمالي الفيديوهات القصيرة
            # هنا نفترض الالتزام بإجمالي الشورتات خلال الأسبوع
            required_weekly_shorts = REQUIRED_SHORT_VIDEOS_DAILY * (today.weekday() + 1) # المطلوب لليوم الحالي من الأسبوع
            
            if data['short_videos_count'] >= required_weekly_shorts:
                commitment_status = msg_texts.MSG_USER_MET_TARGET.format(
                    count=data['short_videos_count'], 
                    required_count=required_weekly_shorts
                )
            elif data['has_activity_in_period']:
                 commitment_status = msg_texts.MSG_USER_MISSED_TARGET.format(
                    count=data['short_videos_count'], 
                    required_count=required_weekly_shorts
                )
            else:
                commitment_status = msg_texts.MSG_USER_NO_ACTIVITY

            report_parts.append(
                msg_texts.MSG_COMMITMENT_USER_DETAIL.format(
                    index=i+1,
                    name=user.name,
                    channel_name=user.channel_name,
                    age=user.age if user.age else 'غير محدد',
                    reg_date=data['registration_date_str'],
                    points=data['points_earned'],
                    short_count=data['short_videos_count'],
                    long_count=data['long_videos_count'],
                    period_text="للأسبوع",
                    commitment_status=commitment_status
                )
            )
    
    full_report = "\n".join(report_parts)
    chunk_size = 4000
    for i in range(0, len(full_report), chunk_size):
        await message.answer(full_report[i:i+chunk_size], parse_mode='Markdown')

# --- الشغل الشهري للمشرف ---
@router.message(F.text == "⭐ الشغل الشهري", StateFilter(AdminStates.in_commitment_menu))
async def admin_monthly_commitment_report(message: Message):
    today = datetime.date.today()
    start_of_month = today.replace(day=1)
    users_data = db.get_users_by_activity_in_period(start_of_month, today)

    report_parts = [msg_texts.MSG_COMMITMENT_REPORT_HEADER.format(period="للشهر")]
    
    if not users_data:
        report_parts.append(msg_texts.MSG_NO_COMMITMENT_DATA_FOR_PERIOD)
    else:
        for i, data in enumerate(users_data):
            user = data['user']
            commitment_status = ""
            # للالتزام الشهري، نتحقق من إجمالي الشورتات
            # مطلوب يومي * عدد الأيام اللي مرت في الشهر
            required_monthly_shorts = REQUIRED_SHORT_VIDEOS_DAILY * today.day 

            if data['short_videos_count'] >= required_monthly_shorts:
                commitment_status = msg_texts.MSG_USER_MET_TARGET.format(
                    count=data['short_videos_count'], 
                    required_count=required_monthly_shorts
                )
            elif data['has_activity_in_period']:
                commitment_status = msg_texts.MSG_USER_MISSED_TARGET.format(
                    count=data['short_videos_count'], 
                    required_count=required_monthly_shorts
                )
            else:
                commitment_status = msg_texts.MSG_USER_NO_ACTIVITY
            
            report_parts.append(
                msg_texts.MSG_COMMITMENT_USER_DETAIL.format(
                    index=i+1,
                    name=user.name,
                    channel_name=user.channel_name,
                    age=user.age if user.age else 'غير محدد',
                    reg_date=data['registration_date_str'],
                    points=data['points_earned'],
                    short_count=data['short_videos_count'],
                    long_count=data['long_videos_count'],
                    period_text="للشهر",
                    commitment_status=commitment_status
                )
            )
    
    full_report = "\n".join(report_parts)
    chunk_size = 4000
    for i in range(0, len(full_report), chunk_size):
        await message.answer(full_report[i:i+chunk_size], parse_mode='Markdown')

# --- معالج أي رسالة أخرى لا تتطابق مع الأوامر أو حالات FSM ---
@router.message()
async def echo_message(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state:
        return # إذا كان المستخدم في حالة FSM، لا تفعل شيئاً هنا

    user_id = message.from_user.id
    user = db.get_user(user_id)
    if not user:
        await message.answer(msg_texts.MSG_NOT_REGISTERED)
    else:
        await message.answer(msg_texts.MSG_WELCOME_BACK, reply_markup=get_main_menu_keyboard(user_id))
