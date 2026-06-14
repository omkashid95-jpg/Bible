from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float, Date, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String, nullable=True)
    country_code = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    profile_image = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    primary_language = Column(String, default="en")
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    education = Column(String, nullable=True)
    total_points = Column(Integer, default=0)
    total_score = Column(Integer, default=0)
    current_rank = Column(Integer, nullable=True)
    current_level = Column(Integer, default=1)
    daily_streak = Column(Integer, default=0)
    is_guest = Column(Boolean, default=False)
    is_email_verified = Column(Boolean, default=False)
    is_phone_verified = Column(Boolean, default=False)
    is_onboarding_completed = Column(Boolean, default=False, server_default="0")
    status = Column(String, default="active")
    role = Column(String, default="user") # 'admin' or 'user'
    is_active = Column(Boolean, default=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    attempts = relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")
    languages = relationship("UserLanguage", back_populates="user", cascade="all, delete-orphan")
    expertise = relationship("UserExpertise", back_populates="user", uselist=False, cascade="all, delete-orphan")
    bible_versions = relationship("UserBibleVersion", back_populates="user", cascade="all, delete-orphan")

class UserExpertise(Base):
    __tablename__ = "user_expertise"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    preferred_language = Column(String, nullable=True)
    education = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user = relationship("User", back_populates="expertise")

class UserBibleVersion(Base):
    __tablename__ = "user_bible_versions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    bible_version = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="bible_versions")

class UserLanguage(Base):
    __tablename__ = "user_languages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    language_name = Column(String, nullable=False)
    is_primary = Column(Boolean, default=False)
    can_read = Column(Boolean, default=False)
    can_write = Column(Boolean, default=False)
    can_speak = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user = relationship("User", back_populates="languages")

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String)
    icon_url = Column(String, nullable=True)
    image_url = Column(String, nullable=True)
    status = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    questions = relationship("Question", back_populates="category", cascade="all, delete-orphan")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"))
    text = Column(String, nullable=False)
    option_a = Column(String, nullable=False)
    option_b = Column(String, nullable=False)
    option_c = Column(String, nullable=False)
    option_d = Column(String, nullable=False)
    correct_option = Column(String, nullable=False)
    difficulty = Column(String, default="medium") # easy, medium, hard
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    category = relationship("Category", back_populates="questions")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    score = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user = relationship("User", back_populates="attempts")
    category = relationship("Category")

class Language(Base):
    __tablename__ = "languages"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    code = Column(String, unique=True, index=True, nullable=False)

class BibleVersion(Base):
    __tablename__ = "bible_versions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    short_name = Column(String, unique=True, index=True, nullable=False)

class AgeGroup(Base):
    __tablename__ = "age_groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

class DifficultyLevel(Base):
    __tablename__ = "difficulty_levels"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)

class QuizSession(Base):
    __tablename__ = "quiz_sessions"
    id = Column(Integer, primary_key=True, index=True)
    session_uuid = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    language_id = Column(Integer, ForeignKey("languages.id"))
    bible_version_id = Column(Integer, ForeignKey("bible_versions.id"))
    mode = Column(String, nullable=False) # single, group
    total_questions = Column(Integer, default=10)
    current_question_index = Column(Integer, default=0)
    score = Column(Integer, default=0)
    status = Column(String, default="started")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    id = Column(Integer, primary_key=True, index=True)
    question_uuid = Column(String, unique=True, index=True, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    language_id = Column(Integer, ForeignKey("languages.id"))
    bible_version_id = Column(Integer, ForeignKey("bible_versions.id"))
    question = Column(String, nullable=False)
    answer_reason = Column(String, nullable=True)
    bible_reference = Column(String, nullable=True)
    difficulty_level = Column(String, default="medium")
    status = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    options = relationship("QuizOption", back_populates="question", cascade="all, delete-orphan")

class QuizOption(Base):
    __tablename__ = "quiz_options"
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("quiz_questions.id"))
    option_text = Column(String, nullable=False)
    is_correct = Column(Boolean, default=False)

    question = relationship("QuizQuestion", back_populates="options")

class QuizAnswer(Base):
    __tablename__ = "quiz_answers"
    id = Column(Integer, primary_key=True, index=True)
    answer_uuid = Column(String, unique=True, index=True, nullable=False)
    session_uuid = Column(String, index=True, nullable=False) # Maps to quiz_sessions.session_uuid
    user_id = Column(Integer, ForeignKey("users.id"))
    question_uuid = Column(String, index=True, nullable=False) # Maps to quiz_questions.question_uuid
    selected_option_id = Column(Integer, nullable=False)
    is_correct = Column(Boolean, default=False)
    points_earned = Column(Integer, default=0)
    time_taken_seconds = Column(Integer, default=0)
    answered_at = Column(DateTime(timezone=True), server_default=func.now())

class QuizHistory(Base):
    __tablename__ = "quiz_history"
    id = Column(Integer, primary_key=True, index=True)
    history_uuid = Column(String, unique=True, index=True, nullable=False)
    session_uuid = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    score = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    accuracy_percentage = Column(Float, default=0.0)
    points_earned = Column(Integer, default=0)
    xp_earned = Column(Integer, default=0)
    completed_at = Column(DateTime(timezone=True), server_default=func.now())

class QuizSubmission(Base):
    __tablename__ = "quiz_submissions"
    id = Column(Integer, primary_key=True, index=True)
    submission_uuid = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    language_id = Column(Integer, ForeignKey("languages.id"))
    bible_version_id = Column(Integer, ForeignKey("bible_versions.id"))
    question = Column(String, nullable=False)
    option_a = Column(String, nullable=False)
    option_b = Column(String, nullable=False)
    option_c = Column(String, nullable=False)
    option_d = Column(String, nullable=False)
    correct_option = Column(String, nullable=False)
    answer_explanation = Column(String, nullable=False)
    bible_reference = Column(String, nullable=False)
    difficulty_level = Column(String, nullable=False)
    age_group_id = Column(Integer, ForeignKey("age_groups.id"))
    review_status = Column(String, default="pending")
    review_comment = Column(String, nullable=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class QuizTranslation(Base):
    __tablename__ = "quiz_translations"
    id = Column(Integer, primary_key=True, index=True)
    translation_uuid = Column(String, unique=True, index=True, nullable=False)
    quiz_uuid = Column(String, index=True, nullable=False)
    translator_user_id = Column(Integer, ForeignKey("users.id"))
    source_language_id = Column(Integer, ForeignKey("languages.id"))
    target_language_id = Column(Integer, ForeignKey("languages.id"))
    translated_question = Column(String, nullable=False)
    translated_option_a = Column(String, nullable=False)
    translated_option_b = Column(String, nullable=False)
    translated_option_c = Column(String, nullable=False)
    translated_option_d = Column(String, nullable=False)
    translated_correct_option = Column(String, nullable=False)
    translated_answer_explanation = Column(String, nullable=False)
    review_status = Column(String, default="pending")
    review_comment = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class LiveQuizTranslation(Base):
    __tablename__ = "live_quiz_translations"
    id = Column(Integer, primary_key=True, index=True)
    live_translation_uuid = Column(String, unique=True, index=True, nullable=False)
    quiz_uuid = Column(String, index=True, nullable=False)
    translator_user_id = Column(Integer, ForeignKey("users.id"))
    target_language_id = Column(Integer, ForeignKey("languages.id"))
    translated_question = Column(String, nullable=False)
    translated_option_a = Column(String, nullable=False)
    translated_option_b = Column(String, nullable=False)
    translated_option_c = Column(String, nullable=False)
    translated_option_d = Column(String, nullable=False)
    translated_correct_option = Column(String, nullable=False)
    translated_answer_explanation = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class QuizCorrection(Base):
    __tablename__ = "quiz_corrections"
    id = Column(Integer, primary_key=True, index=True)
    correction_uuid = Column(String, unique=True, index=True, nullable=False)
    quiz_uuid = Column(String, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    correction_type = Column(String, nullable=False)
    current_value = Column(String, nullable=False)
    suggested_value = Column(String, nullable=False)
    user_comment = Column(String, nullable=True)
    review_status = Column(String, default="pending")
    review_comment = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class LeaderboardRanking(Base):
    __tablename__ = "leaderboard_rankings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    rank = Column(Integer, index=True)
    total_points = Column(Integer, default=0)
    current_level = Column(Integer, default=1)
    daily_streak = Column(Integer, default=0)
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class DailyLeaderboard(Base):
    __tablename__ = "daily_leaderboard"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    points_today = Column(Integer, default=0)
    quizzes_completed_today = Column(Integer, default=0)
    accuracy_percentage = Column(Float, default=0.0)
    rank = Column(Integer, index=True)
    leaderboard_date = Column(Date, index=True, default=func.current_date())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class BlacklistedToken(Base):
    __tablename__ = "blacklisted_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False)
    blacklisted_at = Column(DateTime(timezone=True), server_default=func.now())

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    group_uuid = Column(String, unique=True, index=True, nullable=False)
    group_name = Column(String, nullable=False)
    group_description = Column(String, nullable=True)
    admin_user_id = Column(Integer, ForeignKey("users.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    language_id = Column(Integer, ForeignKey("languages.id"))
    bible_version_id = Column(Integer, ForeignKey("bible_versions.id"))
    max_members = Column(Integer, default=50)
    current_members = Column(Integer, default=1)
    group_type = Column(String, default="public")
    invite_code = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, default="active")
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class GroupMember(Base):
    __tablename__ = "group_members"
    id = Column(Integer, primary_key=True, index=True)
    member_uuid = Column(String, unique=True, index=True, nullable=False)
    group_uuid = Column(String, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    role = Column(String, default="member") # admin, member
    status = Column(String, default="active")
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

class GroupInvitation(Base):
    __tablename__ = "group_invitations"
    id = Column(Integer, primary_key=True, index=True)
    invitation_uuid = Column(String, unique=True, index=True, nullable=False)
    group_uuid = Column(String, index=True, nullable=False)
    sender_user_id = Column(Integer, ForeignKey("users.id"))
    receiver_user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="pending") # pending, accepted, rejected, expired
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class GroupScore(Base):
    __tablename__ = "group_scores"
    id = Column(Integer, primary_key=True, index=True)
    group_uuid = Column(String, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    score = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    wrong_answers = Column(Integer, default=0)
    accuracy_percentage = Column(Float, default=0.0)
    points_earned = Column(Integer, default=0)
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    notification_uuid = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    notification_type = Column(String, nullable=False)
    reference_uuid = Column(String, nullable=True)
    is_read = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class Reward(Base):
    __tablename__ = "rewards"
    id = Column(Integer, primary_key=True, index=True)
    reward_uuid = Column(String, unique=True, index=True, nullable=False)
    reward_name = Column(String, nullable=False)
    reward_description = Column(String, nullable=True)
    reward_type = Column(String, nullable=False)
    points_required = Column(Integer, nullable=False)
    reward_value = Column(String, nullable=True)
    status = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class RewardClaim(Base):
    __tablename__ = "reward_claims"
    id = Column(Integer, primary_key=True, index=True)
    claim_uuid = Column(String, unique=True, index=True, nullable=False)
    reward_uuid = Column(String, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"))
    claim_status = Column(String, default="claimed")
    claimed_at = Column(DateTime(timezone=True), server_default=func.now())

class Referral(Base):
    __tablename__ = "referrals"
    id = Column(Integer, primary_key=True, index=True)
    referral_uuid = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    referral_code = Column(String, unique=True, index=True, nullable=False)
    referral_link = Column(String, nullable=False)
    total_referrals = Column(Integer, default=0)
    successful_referrals = Column(Integer, default=0)
    pending_referrals = Column(Integer, default=0)
    total_rewards_earned = Column(Integer, default=0)
    total_points_earned = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class ReferralHistory(Base):
    __tablename__ = "referral_history"
    id = Column(Integer, primary_key=True, index=True)
    history_uuid = Column(String, unique=True, index=True, nullable=False)
    referrer_user_id = Column(Integer, ForeignKey("users.id"))
    referred_user_id = Column(Integer, ForeignKey("users.id"))
    reward_points = Column(Integer, default=0)
    status = Column(String, default="pending")
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    rewarded_at = Column(DateTime(timezone=True), nullable=True)
    
    referrer = relationship("User", foreign_keys=[referrer_user_id])
    referred = relationship("User", foreign_keys=[referred_user_id])

class Achievement(Base):
    __tablename__ = "achievements"
    id = Column(Integer, primary_key=True, index=True)
    achievement_uuid = Column(String, unique=True, index=True, nullable=False)
    achievement_name = Column(String, nullable=False)
    achievement_description = Column(String, nullable=False)
    achievement_icon = Column(String, nullable=True)
    achievement_type = Column(String, nullable=False)
    required_value = Column(Integer, default=0)
    reward_type = Column(String, default="badge")
    reward_name = Column(String, default="Standard Badge")
    reward_points = Column(Integer, default=0)
    status = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("admins.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class UserAchievement(Base):
    __tablename__ = "user_achievements"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    achievement_uuid = Column(String, index=True, nullable=False)
    earned_at = Column(DateTime(timezone=True), server_default=func.now())

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    admin_uuid = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="content_admin")
    status = Column(Boolean, default=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class SystemSetting(Base):
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String, unique=True, index=True, nullable=False)
    setting_value = Column(JSON, nullable=False)
    description = Column(String, nullable=True)
    updated_by = Column(Integer, ForeignKey("admins.id"))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    audit_uuid = Column(String, unique=True, index=True, nullable=False)
    admin_id = Column(Integer, ForeignKey("admins.id"))
    action_type = Column(String, nullable=False)
    entity_type = Column(String, nullable=True)
    entity_uuid = Column(String, nullable=True)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    admin = relationship("Admin")
