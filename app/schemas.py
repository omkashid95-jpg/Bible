from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# User Schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    phone_number: str
    country_code: str
    password: str

class RegisterResponse(BaseModel):
    success: bool
    message: str
    user_id: str

class LoginRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    password: str

class LoginUser(BaseModel):
    id: str
    full_name: Optional[str] = None
    email: EmailStr
    phone_number: Optional[str] = None

class LoginResponse(BaseModel):
    success: bool
    message: str
    access_token: str
    refresh_token: str
    user: LoginUser

class LogoutResponse(BaseModel):
    success: bool
    message: str

class CurrentUserData(BaseModel):
    id: str
    full_name: Optional[str] = None
    email: EmailStr
    phone_number: Optional[str] = None
    profile_image: Optional[str] = None
    primary_language: Optional[str] = None
    current_rank: Optional[int] = None
    current_level: Optional[int] = None
    total_points: Optional[int] = None
    daily_streak: Optional[int] = None

class CurrentUserResponse(BaseModel):
    success: bool
    user: CurrentUserData

class LanguageDetail(BaseModel):
    language: str
    reading: bool
    writing: bool
    speaking: bool

class LanguageResponseDetail(LanguageDetail):
    is_primary: bool

class UserLanguagesResponse(BaseModel):
    success: bool
    languages: List[LanguageResponseDetail]

class LanguageSelectionRequest(BaseModel):
    user_id: str
    primary_language: str
    languages: List[LanguageDetail]

class LanguageSelectionResponse(BaseModel):
    success: bool
    message: str

class ExpertiseRequest(BaseModel):
    preferred_language: str
    bible_versions: List[str]
    education: str
    age: int

class ExpertiseResponse(BaseModel):
    success: bool
    message: str

class ExpertiseGetResponse(BaseModel):
    preferred_language: Optional[str] = None
    education: Optional[str] = None
    age: Optional[int] = None
    bible_versions: List[str] = []

class OnboardingRequest(BaseModel):
    is_onboarding_completed: bool

class OnboardingResponse(BaseModel):
    success: bool
    message: str

class HomeUserDashboard(BaseModel):
    id: str
    full_name: Optional[str] = None
    profile_image: Optional[str] = None
    rank: Optional[int] = None
    level: Optional[int] = None
    points: Optional[int] = None
    daily_streak: Optional[int] = None

class TodayChallengeDashboard(BaseModel):
    challenge_id: str
    title: str
    description: str
    progress: float

class HomeDashboardResponse(BaseModel):
    user: HomeUserDashboard
    today_challenge: TodayChallengeDashboard

class TodayChallengeDetails(BaseModel):
    challenge_id: str
    title: str
    description: str
    total_questions: int
    reward_points: int

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    profile_image: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str

class ProfileResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    bio: Optional[str] = None
    profile_image: Optional[str] = None
    role: str
    created_at: datetime
    quizzes_attempted: int = 0
    average_score: float = 0.0
    highest_score: int = 0
    favorite_category: Optional[str] = None
    leaderboard_rank: Optional[int] = None

    class Config:
        from_attributes = True

class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Category Schemas
class QuizCategorySchema(BaseModel):
    id: str
    name: str
    image_url: str

class QuizCategoryListResponse(BaseModel):
    categories: List[QuizCategorySchema]

class CategoryDetailData(BaseModel):
    id: int
    uuid: str
    name: str
    description: str
    icon_url: str
    image_url: str
    total_quizzes: int
    total_questions: int
    status: bool

class CategoryDetailResponse(BaseModel):
    success: bool
    data: CategoryDetailData

class CategoryBase(BaseModel):
    name: str = Field(..., example="Old Testament")
    description: Optional[str] = Field(None, example="Questions from the Old Testament")

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class CategoryResponse(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Question Schemas
class QuestionBase(BaseModel):
    text: str = Field(..., example="Who built the ark?")
    option_a: str = Field(..., example="Moses")
    option_b: str = Field(..., example="Noah")
    option_c: str = Field(..., example="Abraham")
    option_d: str = Field(..., example="David")
    correct_option: str = Field(..., example="B")
    difficulty: str = Field("medium", example="easy")

class QuestionCreate(QuestionBase):
    category_id: int

class QuestionUpdate(BaseModel):
    text: Optional[str] = None
    option_a: Optional[str] = None
    option_b: Optional[str] = None
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    correct_option: Optional[str] = None
    difficulty: Optional[str] = None
    category_id: Optional[int] = None

class QuestionResponse(QuestionBase):
    id: int
    category_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Quiz Attempt Schemas
class StartQuizRequest(BaseModel):
    category_id: int
    language_id: int
    bible_version_id: int
    mode: str

class QuizSessionData(BaseModel):
    session_uuid: str
    category_id: int
    language_id: int
    bible_version_id: int
    mode: str
    total_questions: int
    score: int
    status: str

class StartQuizResponse(BaseModel):
    success: bool
    data: QuizSessionData

class QuizOptionSchema(BaseModel):
    option_id: int
    option_text: str

class QuizQuestionPayload(BaseModel):
    question_uuid: str
    question_number: int
    total_questions: int
    question: str
    options: List[QuizOptionSchema]

class QuizQuestionResponse(BaseModel):
    success: bool
    data: QuizQuestionPayload

class NextQuestionResponse(BaseModel):
    success: bool
    quiz_completed: bool
    data: Optional[QuizQuestionPayload] = None
    message: Optional[str] = None

class QuizResultData(BaseModel):
    session_uuid: str
    score: int
    total_questions: int
    correct_answers: int
    wrong_answers: int
    accuracy_percentage: float
    total_points_earned: int
    xp_earned: int
    current_level: int
    rank_change: int
    total_time_seconds: int
    completed_at: datetime

class QuizResultResponse(BaseModel):
    success: bool
    data: QuizResultData

class QuizReviewItem(BaseModel):
    question_uuid: str
    question: str
    selected_option: str
    correct_option: str
    is_correct: bool
    answer_explanation: str
    bible_reference: str

class QuizReviewResponse(BaseModel):
    success: bool
    data: List[QuizReviewItem]

class PaginationMeta(BaseModel):
    page: int
    limit: int
    total_records: int
    total_pages: int

class QuizHistoryItem(BaseModel):
    history_uuid: str
    session_uuid: str
    category_name: str
    score: int
    total_questions: int
    accuracy_percentage: float
    points_earned: int
    completed_at: datetime

class QuizHistoryResponse(BaseModel):
    success: bool
    data: List[QuizHistoryItem]
    pagination: PaginationMeta

class MasterCategory(BaseModel):
    id: int
    name: str

class MasterLanguage(BaseModel):
    id: int
    name: str
    code: str

class MasterBibleVersion(BaseModel):
    id: int
    name: str
    short_name: str

class MasterAgeGroup(BaseModel):
    id: int
    name: str

class MasterDifficultyLevel(BaseModel):
    id: int
    name: str

class MasterDataPayload(BaseModel):
    categories: List[MasterCategory]
    languages: List[MasterLanguage]
    bible_versions: List[MasterBibleVersion]
    age_groups: List[MasterAgeGroup]
    difficulty_levels: List[MasterDifficultyLevel]

class MasterDataResponse(BaseModel):
    success: bool
    data: MasterDataPayload

class CheckDuplicateRequest(BaseModel):
    question: str
    language_id: int
    bible_version_id: int

class CheckDuplicateResponse(BaseModel):
    success: bool
    is_duplicate: bool
    message: str
    existing_question_id: Optional[int] = None

class CreateQuizSubmitRequest(BaseModel):
    category_id: int
    language_id: int
    bible_version_id: int
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str
    answer_explanation: str
    bible_reference: str
    difficulty_level: str
    age_group_id: int

class CreateQuizSubmitResponse(BaseModel):
    success: bool
    message: str
    submission_uuid: Optional[str] = None
    review_status: Optional[str] = None

class MySubmissionItem(BaseModel):
    submission_uuid: str
    question: str
    category_name: str
    language: str
    review_status: str
    submitted_at: datetime

class MySubmissionsResponse(BaseModel):
    success: bool
    data: List[MySubmissionItem]
    pagination: PaginationMeta

class SubmissionDetailsData(BaseModel):
    submission_uuid: str
    category_id: int
    category_name: str
    language_id: int
    language_name: str
    bible_version_id: int
    bible_version_name: str
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str
    answer_explanation: str
    bible_reference: str
    difficulty_level: str
    review_status: str
    review_comment: Optional[str] = None
    submitted_at: datetime

class SubmissionDetailsResponse(BaseModel):
    success: bool
    data: SubmissionDetailsData

class AvailableTranslationItem(BaseModel):
    quiz_uuid: str
    question: str
    source_language: str
    target_language: str
    category_name: str
    bible_version: str
    created_by: str
    created_at: datetime

class AvailableTranslationsResponse(BaseModel):
    success: bool
    data: List[AvailableTranslationItem]
    pagination: PaginationMeta

class TranslationQuizDetailsData(BaseModel):
    quiz_uuid: str
    source_language: str
    target_language: str
    category_name: str
    bible_version: str
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str
    answer_explanation: str
    bible_reference: str

class TranslationQuizDetailsResponse(BaseModel):
    success: bool
    data: TranslationQuizDetailsData

class SubmitTranslationRequest(BaseModel):
    quiz_uuid: str
    source_language_id: int
    target_language_id: int
    translated_question: str
    translated_option_a: str
    translated_option_b: str
    translated_option_c: str
    translated_option_d: str
    translated_correct_option: str
    translated_answer_explanation: str

class SubmitTranslationResponse(BaseModel):
    success: bool
    message: str
    translation_uuid: Optional[str] = None
    review_status: Optional[str] = None

class MyTranslationItem(BaseModel):
    translation_uuid: str
    quiz_uuid: str
    question: str
    target_language: str
    review_status: str
    review_comment: Optional[str] = None
    submitted_at: datetime

class MyTranslationsResponse(BaseModel):
    success: bool
    data: List[MyTranslationItem]
    pagination: PaginationMeta

class AvailableCorrectionItem(BaseModel):
    quiz_uuid: str
    question: str
    language: str
    category_name: str
    bible_version: str
    created_at: datetime

class AvailableCorrectionsResponse(BaseModel):
    success: bool
    data: List[AvailableCorrectionItem]
    pagination: PaginationMeta

class CorrectionQuizDetailsData(BaseModel):
    quiz_uuid: str
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_option: str
    answer_explanation: str
    bible_reference: str
    language: str
    category_name: str
    bible_version: str

class CorrectionQuizDetailsResponse(BaseModel):
    success: bool
    data: CorrectionQuizDetailsData

class SubmitCorrectionRequest(BaseModel):
    quiz_uuid: str
    correction_type: str
    current_value: str
    suggested_value: str
    user_comment: Optional[str] = None

class SubmitCorrectionResponse(BaseModel):
    success: bool
    message: str
    correction_uuid: Optional[str] = None
    review_status: Optional[str] = None

class MyCorrectionItem(BaseModel):
    correction_uuid: str
    quiz_uuid: str
    correction_type: str
    review_status: str
    review_comment: Optional[str] = None
    submitted_at: datetime

class MyCorrectionsResponse(BaseModel):
    success: bool
    data: List[MyCorrectionItem]
    pagination: PaginationMeta

class LeaderboardItem(BaseModel):
    rank: int
    user_uuid: str
    full_name: str
    profile_image: Optional[str] = None
    total_points: int
    current_level: int
    daily_streak: int

class LeaderboardCurrentUser(BaseModel):
    rank: int
    total_points: int
    current_level: int

class GlobalLeaderboardResponse(BaseModel):
    success: bool
    data: List[LeaderboardItem]
    current_user: LeaderboardCurrentUser
    pagination: PaginationMeta

class DailyLeaderboardItem(BaseModel):
    rank: int
    user_uuid: str
    full_name: str
    profile_image: Optional[str] = None
    points_today: int
    quizzes_completed_today: int
    accuracy_percentage: float

class DailyLeaderboardCurrentUser(BaseModel):
    rank: int
    points_today: int
    quizzes_completed_today: int

class DailyLeaderboardResponse(BaseModel):
    success: bool
    data: List[DailyLeaderboardItem]
    current_user: DailyLeaderboardCurrentUser
    pagination: Optional[PaginationMeta] = None

class LanguageLeaderboardLanguageInfo(BaseModel):
    id: int
    name: str

class LanguageLeaderboardResponse(BaseModel):
    success: bool
    selected_language: LanguageLeaderboardLanguageInfo
    data: List[LeaderboardItem]
    current_user: LeaderboardCurrentUser
    pagination: PaginationMeta

class MyRankData(BaseModel):
    user_uuid: str
    full_name: str
    profile_image: Optional[str] = None
    global_rank: int
    daily_rank: int
    language_rank: int
    total_points: int
    current_level: int
    daily_streak: int
    total_quizzes_played: int
    total_correct_answers: int
    accuracy_percentage: float

class MyRankResponse(BaseModel):
    success: bool
    data: MyRankData

class CreateGroupRequest(BaseModel):
    group_name: str
    group_description: Optional[str] = None
    category_id: int
    language_id: int
    bible_version_id: int
    max_members: int
    group_type: str
    start_date: datetime
    end_date: datetime

class CreateGroupResponse(BaseModel):
    success: bool
    message: str
    group_uuid: str
    invite_code: str

class GroupInviteRequest(BaseModel):
    group_uuid: str
    user_ids: List[str]

class GroupInviteResponse(BaseModel):
    success: bool
    message: str
    total_invites: Optional[int] = 0

class AcceptInviteRequest(BaseModel):
    invitation_uuid: str

class AcceptInviteResponse(BaseModel):
    success: bool
    message: str
    group_uuid: str
    group_name: str

class GroupAdminInfo(BaseModel):
    user_uuid: str
    full_name: str
    profile_image: Optional[str] = None

class GroupChallengeInfo(BaseModel):
    category_name: str
    language: str
    bible_version: str
    start_date: datetime
    end_date: datetime

class GroupDetailsData(BaseModel):
    group_uuid: str
    group_name: str
    group_description: Optional[str] = None
    invite_code: str
    group_type: str
    status: str
    max_members: int
    current_members: int
    admin: GroupAdminInfo
    challenge: GroupChallengeInfo

class GroupDetailsResponse(BaseModel):
    success: bool
    data: GroupDetailsData

class GroupMemberItem(BaseModel):
    member_uuid: str
    user_uuid: str
    full_name: str
    profile_image: Optional[str] = None
    role: str
    group_rank: int
    group_score: int
    joined_at: datetime

class GroupMembersResponse(BaseModel):
    success: bool
    data: List[GroupMemberItem]
    pagination: PaginationMeta

class GroupLeaderboardItem(BaseModel):
    rank: int
    user_uuid: str
    full_name: str
    profile_image: Optional[str] = None
    group_score: int
    correct_answers: int
    wrong_answers: int
    accuracy_percentage: float
    points_earned: int

class GroupLeaderboardCurrentUser(BaseModel):
    rank: int
    group_score: int

class GroupLeaderboardResponse(BaseModel):
    success: bool
    data: List[GroupLeaderboardItem]
    current_user: GroupLeaderboardCurrentUser
    pagination: Optional[PaginationMeta] = None

class NotificationItem(BaseModel):
    notification_uuid: str
    title: str
    message: str
    notification_type: str
    reference_uuid: Optional[str] = None
    is_read: bool
    created_at: datetime

class NotificationsResponse(BaseModel):
    success: bool
    unread_count: int
    data: List[NotificationItem]
    pagination: Optional[PaginationMeta] = None

class MarkReadRequest(BaseModel):
    notification_uuid: Optional[str] = None
    notification_uuids: Optional[List[str]] = None

class MarkReadResponse(BaseModel):
    success: bool
    message: str

class DeleteNotificationResponse(BaseModel):
    success: bool
    message: str

class RewardItem(BaseModel):
    reward_uuid: str
    reward_name: str
    reward_description: Optional[str] = None
    reward_type: str
    points_required: int
    is_claimed: bool
    is_claimable: bool

class RewardsResponse(BaseModel):
    success: bool
    current_points: int
    data: List[RewardItem]
    pagination: Optional[PaginationMeta] = None

class ClaimRewardRequest(BaseModel):
    reward_uuid: str

class ClaimRewardData(BaseModel):
    claim_uuid: str
    reward_uuid: str
    reward_name: str
    claimed_at: datetime

class ClaimRewardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[ClaimRewardData] = None

class RewardHistoryItem(BaseModel):
    claim_uuid: str
    reward_uuid: str
    reward_name: str
    reward_type: str
    claimed_at: datetime
    claim_status: str

class RewardHistoryResponse(BaseModel):
    success: bool
    data: List[RewardHistoryItem]
    pagination: PaginationMeta

class ReferralData(BaseModel):
    referral_uuid: str
    referral_code: str
    referral_link: str
    total_referrals: int
    total_rewards_earned: int

class GenerateReferralResponse(BaseModel):
    success: bool
    data: ReferralData

class ReferralStatisticsData(BaseModel):
    referral_code: str
    referral_link: str
    total_referrals: int
    successful_referrals: int
    pending_referrals: int
    total_rewards_earned: int
    total_points_earned: int

class ReferralStatisticsResponse(BaseModel):
    success: bool
    data: ReferralStatisticsData

class ReferralHistoryItem(BaseModel):
    history_uuid: str
    referred_user_name: str
    status: str
    reward_points: int
    registered_at: datetime
    rewarded_at: Optional[datetime] = None

class ReferralHistoryResponse(BaseModel):
    success: bool
    data: List[ReferralHistoryItem]
    pagination: PaginationMeta

class UserProfileData(BaseModel):
    user_uuid: str
    full_name: Optional[str] = None
    email: str
    phone_number: Optional[str] = None
    country_code: Optional[str] = None
    profile_image: Optional[str] = None
    primary_language: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    education: Optional[str] = None
    total_points: int
    current_level: int
    daily_streak: int
    global_rank: int
    language_rank: int
    total_quizzes_played: int
    total_correct_answers: int
    accuracy_percentage: float
    total_referrals: int
    total_rewards_claimed: int
    total_created_quizzes: int
    total_translations: int
    total_corrections: int
    member_since: datetime

class UserProfileResponse(BaseModel):
    success: bool
    data: UserProfileData

class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    profile_image: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    education: Optional[str] = None
    primary_language_id: Optional[int] = None

class UpdateProfileData(BaseModel):
    full_name: Optional[str] = None
    profile_image: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    education: Optional[str] = None
    primary_language: Optional[str] = None

class UpdateProfileResponse(BaseModel):
    success: bool
    message: str
    data: UpdateProfileData

class AchievementSummary(BaseModel):
    total_achievements: int
    earned_achievements: int

class AchievementItem(BaseModel):
    achievement_uuid: str
    achievement_name: str
    achievement_description: str
    achievement_icon: str
    achievement_type: str
    is_earned: bool
    earned_at: Optional[datetime] = None

class ProfileAchievementsResponse(BaseModel):
    success: bool
    summary: AchievementSummary
    data: List[AchievementItem]

class AchievementRewardData(BaseModel):
    reward_type: str
    reward_name: str
    reward_points: int

class AchievementDetailData(BaseModel):
    achievement_uuid: str
    achievement_name: str
    achievement_description: str
    achievement_icon: str
    achievement_type: str
    required_value: int
    current_progress: int
    progress_percentage: int
    is_earned: bool
    earned_at: Optional[datetime] = None
    reward: AchievementRewardData

class AchievementDetailResponse(BaseModel):
    success: bool
    data: AchievementDetailData

class AdminLoginRequest(BaseModel):
    email: str
    password: str

class AdminLoginData(BaseModel):
    admin_uuid: str
    full_name: str
    role: str
    token: str

class AdminLoginResponse(BaseModel):
    success: bool
    message: str
    data: Optional[AdminLoginData] = None

class SubmittedByData(BaseModel):
    user_uuid: str
    full_name: str

class PendingQuizSubmissionItem(BaseModel):
    submission_uuid: str
    question: str
    category_name: str
    language_name: str
    submitted_by: SubmittedByData
    review_status: str
    submitted_at: datetime

class PendingQuizSubmissionsResponse(BaseModel):
    success: bool
    data: List[PendingQuizSubmissionItem]
    pagination: PaginationMeta

class ReviewQuizSubmissionRequest(BaseModel):
    submission_uuid: str
    action: str
    review_comment: Optional[str] = None

class ReviewQuizSubmissionData(BaseModel):
    submission_uuid: str
    review_status: str

class ReviewQuizSubmissionResponse(BaseModel):
    success: bool
    message: str
    data: ReviewQuizSubmissionData

class PendingTranslationItem(BaseModel):
    translation_uuid: str
    quiz_uuid: str
    original_question: str
    translated_question: str
    source_language: str
    target_language: str
    submitted_by: SubmittedByData
    review_status: str
    submitted_at: datetime

class PendingTranslationsResponse(BaseModel):
    success: bool
    data: List[PendingTranslationItem]
    pagination: PaginationMeta

class ReviewTranslationRequest(BaseModel):
    translation_uuid: str
    action: str
    review_comment: Optional[str] = None

class ReviewTranslationData(BaseModel):
    translation_uuid: str
    review_status: str
    points_awarded: Optional[int] = None

class ReviewTranslationResponse(BaseModel):
    success: bool
    message: str
    data: ReviewTranslationData

class PendingCorrectionItem(BaseModel):
    correction_uuid: str
    quiz_uuid: str
    question: str
    correction_type: str
    current_value: str
    suggested_value: str
    user_comment: Optional[str] = None
    submitted_by: SubmittedByData
    review_status: str
    submitted_at: datetime

class PendingCorrectionsResponse(BaseModel):
    success: bool
    data: List[PendingCorrectionItem]
    pagination: PaginationMeta

class ReviewCorrectionRequest(BaseModel):
    correction_uuid: str
    action: str
    review_comment: Optional[str] = None

class ReviewCorrectionData(BaseModel):
    correction_uuid: str
    review_status: str
    points_awarded: Optional[int] = None

class ReviewCorrectionResponse(BaseModel):
    success: bool
    message: str
    data: ReviewCorrectionData

class CreateAchievementRequest(BaseModel):
    achievement_name: str
    achievement_description: str
    achievement_type: str
    required_value: int
    reward_points: int
    achievement_icon: Optional[str] = None
    status: bool

class CreateAchievementData(BaseModel):
    achievement_uuid: str

class CreateAchievementResponse(BaseModel):
    success: bool
    message: str
    data: CreateAchievementData

class AdminUserListItem(BaseModel):
    user_uuid: str
    full_name: str
    email: str
    phone_number: str
    profile_image: Optional[str] = None
    status: str
    current_level: int
    total_points: int
    daily_streak: int
    created_at: datetime

class AdminUsersListResponse(BaseModel):
    success: bool
    data: List[AdminUserListItem]
    pagination: PaginationMeta

class AdminUserDetailData(BaseModel):
    user_uuid: str
    full_name: str
    email: str
    phone_number: Optional[str] = None
    country_code: Optional[str] = None
    profile_image: Optional[str] = None
    status: str
    current_level: int
    total_points: int
    daily_streak: int
    total_quizzes_played: int
    accuracy_percentage: float
    total_referrals: int
    total_rewards_claimed: int
    total_achievements: int
    total_created_quizzes: int
    total_translations: int
    total_corrections: int
    member_since: datetime
    last_login_at: Optional[datetime] = None

class AdminUserDetailResponse(BaseModel):
    success: bool
    data: AdminUserDetailData

class AdminDashboardData(BaseModel):
    total_users: int
    active_users: int
    blocked_users: int
    total_quizzes: int
    pending_quiz_reviews: int
    pending_translations: int
    pending_corrections: int
    total_groups: int
    total_rewards_claimed: int
    today_new_users: int
    today_quizzes_played: int
    today_points_earned: int

class AdminDashboardResponse(BaseModel):
    success: bool
    data: AdminDashboardData

class DateCountItem(BaseModel):
    date: str
    count: int

class QuizCompletionItem(BaseModel):
    date: str
    completed_quizzes: int

class LanguageUsageItem(BaseModel):
    language: str
    users: int

class AdminAnalyticsData(BaseModel):
    user_growth: Optional[List[DateCountItem]] = None
    daily_active_users: Optional[List[DateCountItem]] = None
    quiz_completion: Optional[List[QuizCompletionItem]] = None
    language_usage: Optional[List[LanguageUsageItem]] = None

class AdminAnalyticsResponse(BaseModel):
    success: bool
    data: AdminAnalyticsData

class AdminSettingsData(BaseModel):
    quiz_points_per_correct_answer: int
    translation_reward_points: int
    correction_reward_points: int
    referral_reward_points: int
    max_group_members: int
    daily_streak_bonus: int
    notification_enabled: bool
    achievement_enabled: bool

class AdminSettingsResponse(BaseModel):
    success: bool
    data: AdminSettingsData

class UpdateAdminSettingsRequest(BaseModel):
    quiz_points_per_correct_answer: Optional[int] = None
    translation_reward_points: Optional[int] = None
    correction_reward_points: Optional[int] = None
    referral_reward_points: Optional[int] = None
    max_group_members: Optional[int] = None
    daily_streak_bonus: Optional[int] = None
    notification_enabled: Optional[bool] = None
    achievement_enabled: Optional[bool] = None

class UpdateAdminSettingsResponse(BaseModel):
    success: bool
    message: str
    updated_by: str
    updated_at: datetime

class AdminAuditLogItem(BaseModel):
    audit_uuid: str
    admin_uuid: str
    admin_name: str
    action_type: str
    entity_type: Optional[str] = None
    entity_uuid: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

class AdminAuditLogsResponse(BaseModel):
    success: bool
    data: List[AdminAuditLogItem]
    pagination: PaginationMeta

class AdminAuditLogDetailData(BaseModel):
    audit_uuid: str
    admin_uuid: str
    admin_name: str
    action_type: str
    entity_type: Optional[str] = None
    entity_uuid: Optional[str] = None
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

class AdminAuditLogDetailResponse(BaseModel):
    success: bool
    data: AdminAuditLogDetailData

class QuizAnswerRequest(BaseModel):
    session_uuid: str
    question_uuid: str
    selected_option_id: int
    time_taken_seconds: int

class QuizAnswerResultData(BaseModel):
    is_correct: bool
    correct_option_id: int
    points_earned: int
    current_score: int
    answered_questions: int
    remaining_questions: int
    quiz_completed: bool

class QuizAnswerResponse(BaseModel):
    success: bool
    data: QuizAnswerResultData

class QuizAttemptResponse(BaseModel):
    id: int
    user_id: int
    category_id: int
    score: int
    total_questions: int
    completed_at: datetime

    class Config:
        from_attributes = True

class QuizHistoryResponse(BaseModel):
    id: int
    category_name: str
    score: int
    total_questions: int
    completed_at: datetime

class CategoryPerformance(BaseModel):
    category_name: str
    quizzes_taken: int
    avg_score: float

class DashboardResponse(BaseModel):
    total_quizzes_attempted: int
    highest_score: int
    average_score: float
    category_performance: List[CategoryPerformance]

class LeaderboardEntry(BaseModel):
    rank: int
    username: str
    total_score: int
    quizzes_taken: int
