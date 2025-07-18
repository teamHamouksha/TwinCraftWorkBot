import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func, Boolean, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import extract

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
    name = Column(String, nullable=False)
    age = Column(Integer, nullable=True)  # حقل جديد للعمر
    channel_name = Column(String, nullable=False)
    points = Column(Integer, default=0)
    last_long_video_sent = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, default=datetime.datetime.now) # لتتبع آخر نشاط للمستخدم
    registration_date = Column(DateTime, default=datetime.datetime.now)

    def __repr__(self):
        return f"<User(user_id={self.user_id}, name='{self.name}', age={self.age}, channel='{self.channel_name}', points={self.points})>"

class Video(Base):
    __tablename__ = 'videos'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False) # user_id of the telegram user
    type = Column(String, nullable=False) # 'short' or 'long'
    points_earned = Column(Integer, nullable=False)
    sent_at = Column(DateTime, default=datetime.datetime.now)

    def __repr__(self):
        return f"<Video(user_id={self.user_id}, type='{self.type}', points={self.points_earned}, sent_at={self.sent_at})>"

class Database:
    def __init__(self, db_name='bot_data.db'):
        self.engine = create_engine(f'sqlite:///{db_name}')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.Session()

    def add_user(self, user_id: int, name: str, age: int, channel_name: str):
        session = self.get_session()
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            new_user = User(user_id=user_id, name=name, age=age, channel_name=channel_name)
            session.add(new_user)
            session.commit()
            session.close()
            return True
        session.close()
        return False

    def get_user(self, user_id: int):
        session = self.get_session()
        user = session.query(User).filter_by(user_id=user_id).first()
        session.close()
        return user

    def update_user_points(self, user_id: int, points: int):
        session = self.get_session()
        user = session.query(User).filter_by(user_id=user_id).first()
        if user:
            user.points += points
            session.commit()
        session.close()

    def record_video(self, user_id: int, video_type: str, points: int):
        session = self.get_session()
        new_video = Video(user_id=user_id, type=video_type, points_earned=points)
        session.add(new_video)
        session.commit()
        session.close()
        self.update_user_points(user_id, points)
        self.update_last_activity(user_id) # تحديث آخر نشاط

    def update_last_activity(self, user_id: int):
        session = self.get_session()
        user = session.query(User).filter_by(user_id=user_id).first()
        if user:
            user.last_activity = datetime.datetime.now()
            session.commit()
        session.close()

    def get_today_videos_count(self, user_id: int, video_type: str):
        session = self.get_session()
        today = datetime.date.today()
        count = session.query(Video).filter(
            Video.user_id == user_id,
            Video.type == video_type,
            func.DATE(Video.sent_at) == today
        ).count()
        session.close()
        return count

    def get_weekly_videos_count(self, user_id: int, video_type: str):
        session = self.get_session()
        # بداية الأسبوع (الإثنين)
        start_of_week = datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())
        count = session.query(Video).filter(
            Video.user_id == user_id,
            Video.type == video_type,
            Video.sent_at >= start_of_week.strftime('%Y-%m-%d 00:00:00') # التأكد من التوقيت
        ).count()
        session.close()
        return count

    def get_monthly_videos_count(self, user_id: int, video_type: str):
        session = self.get_session()
        today = datetime.date.today()
        start_of_month = today.replace(day=1)
        count = session.query(Video).filter(
            Video.user_id == user_id,
            Video.type == video_type,
            Video.sent_at >= start_of_month.strftime('%Y-%m-%d 00:00:00')
        ).count()
        session.close()
        return count

    def get_user_videos_in_last_30_days(self, user_id: int):
        session = self.get_session()
        thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        videos = session.query(Video).filter(
            Video.user_id == user_id,
            Video.sent_at >= thirty_days_ago
        ).all()
        session.close()
        return videos

    def get_all_users(self):
        session = self.get_session()
        users = session.query(User).all()
        session.close()
        return users

    def update_last_long_video_sent(self, user_id: int):
        session = self.get_session()
        user = session.query(User).filter_by(user_id=user_id).first()
        if user:
            user.last_long_video_sent = datetime.datetime.now()
            session.commit()
        session.close()

    def get_total_videos_count(self, video_type: str = None):
        session = self.get_session()
        if video_type:
            count = session.query(Video).filter_by(type=video_type).count()
        else:
            count = session.query(Video).count()
        session.close()
        return count

    def get_top_active_users(self, limit: int = 5):
        session = self.get_session()
        top_users = session.query(User).order_by(User.points.desc()).limit(limit).all()
        session.close()
        return top_users

    def get_all_videos(self):
        session = self.get_session()
        videos = session.query(Video).order_by(Video.sent_at.desc()).all() # ترتيب حسب الأحدث
        session.close()
        return videos

    def get_total_short_videos_sent_by_user(self, user_id: int):
        session = self.get_session()
        count = session.query(Video).filter_by(user_id=user_id, type='short').count()
        session.close()
        return count

    def get_total_long_videos_sent_by_user(self, user_id: int):
        session = self.get_session()
        count = session.query(Video).filter_by(user_id=user_id, type='long').count()
        session.close()
        return count

    def get_last_video_sent_details(self, user_id: int):
        session = self.get_session()
        last_video = session.query(Video).filter_by(user_id=user_id).order_by(desc(Video.sent_at)).first()
        session.close()
        return last_video

    def get_videos_for_user_in_period(self, user_id: int, start_date: datetime.date, end_date: datetime.date):
        session = self.get_session()
        videos = session.query(Video).filter(
            Video.user_id == user_id,
            func.DATE(Video.sent_at) >= start_date,
            func.DATE(Video.sent_at) <= end_date
        ).all()
        session.close()
        return videos

    def get_users_by_activity_in_period(self, start_date: datetime.date, end_date: datetime.date):
        session = self.get_session()
        # جلب جميع المستخدمين
        all_users = session.query(User).all()
        
        users_data = []
        for user in all_users:
            short_videos_count = session.query(Video).filter(
                Video.user_id == user.user_id,
                Video.type == 'short',
                func.DATE(Video.sent_at) >= start_date,
                func.DATE(Video.sent_at) <= end_date
            ).count()
            
            long_videos_count = session.query(Video).filter(
                Video.user_id == user.user_id,
                Video.type == 'long',
                func.DATE(Video.sent_at) >= start_date,
                func.DATE(Video.sent_at) <= end_date
            ).count()

            points_earned = session.query(func.sum(Video.points_earned)).filter(
                Video.user_id == user.user_id,
                func.DATE(Video.sent_at) >= start_date,
                func.DATE(Video.sent_at) <= end_date
            ).scalar() or 0
            
            # تاريخ تسجيل المستخدم
            registration_date_str = user.registration_date.strftime('%Y-%m-%d %H:%M')

            # التحقق مما إذا كان المستخدم قد أرسل أي فيديوهات خلال الفترة
            has_activity_in_period = (short_videos_count > 0 or long_videos_count > 0)

            users_data.append({
                'user': user,
                'short_videos_count': short_videos_count,
                'long_videos_count': long_videos_count,
                'points_earned': points_earned,
                'registration_date_str': registration_date_str,
                'has_activity_in_period': has_activity_in_period
            })
        
        # الترتيب حسب النقاط المكتسبة في هذه الفترة تنازلياً
        users_data.sort(key=lambda x: x['points_earned'], reverse=True)
        session.close()
        return users_data
