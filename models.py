from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from app import db


class Organization(db.Model):
    __tablename__ = 'organization'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(50), nullable=False, unique=True)
    branding_config = db.Column(db.JSON)  # Logo URL, colors, theme
    subscription_plan = db.Column(db.String(50), default='trial')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    trial_ends_at = db.Column(db.DateTime)
    
    # Relationships
    users = db.relationship('User', backref='organization', lazy=True)
    interviews = db.relationship('Interview', backref='organization', lazy=True)


class SystemSettings(db.Model):
    __tablename__ = 'system_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False, unique=True)
    value = db.Column(db.Text)
    setting_type = db.Column(db.String(50), default='string')  # 'string', 'integer', 'boolean', 'json', 'password'
    category = db.Column(db.String(50), default='general')  # 'general', 'database', 'api', 'email', 'security'
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('user.id'))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='candidate')  # 'admin', 'recruiter', 'candidate', 'viewer', 'technical_person'
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    user_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Profile information
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    department = db.Column(db.String(100))
    job_title = db.Column(db.String(100))
    bio = db.Column(db.Text)
    skills = db.Column(db.Text)  # JSON string of skills
    experience_years = db.Column(db.Integer)
    education = db.Column(db.Text)  # JSON string of education history
    certifications = db.Column(db.Text)  # JSON string of certifications
    linkedin_url = db.Column(db.String(200))
    portfolio_url = db.Column(db.String(200))
    resume_url = db.Column(db.String(200))
    profile_image_url = db.Column(db.String(200))
    location = db.Column(db.String(100))
    availability = db.Column(db.String(50))  # 'immediate', '2_weeks', '1_month', etc.
    salary_expectation = db.Column(db.String(50))
    
    # Password reset fields
    reset_token = db.Column(db.String(100))
    reset_token_expires = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)
    profile_completed = db.Column(db.Boolean, default=False)
    experience = db.Column(db.Text)  # JSON string of work experience
    
    # Universal Profile Access fields
    is_organization_employee = db.Column(db.Boolean, default=False, nullable=False)
    public_profile_enabled = db.Column(db.Boolean, default=True, nullable=False)
    cross_org_accessible = db.Column(db.Boolean, default=True, nullable=False)  # Changed to True for cross-organization visibility
    
    # Candidate feedback notification status
    interview_feedback_status = db.Column(db.String(20))  # 'welcome', 'sorry', 'pending', None
    feedback_message = db.Column(db.Text)  # Stores the actual feedback message
    feedback_updated_at = db.Column(db.DateTime)  # When the feedback was last updated
    
    # Two-Factor Authentication fields removed - Ez2source focuses on core talent intelligence features
    
    # Career Journey Step Completion Tracking removed - Ez2source focuses on core talent intelligence features
    
    # Composite unique constraint for username within organization
    __table_args__ = (db.UniqueConstraint('username', 'organization_id', name='_username_org_uc'),
                      db.UniqueConstraint('email', 'organization_id', name='_email_org_uc'))
    
    # Relationships
    interviews_created = db.relationship('Interview', backref='creator', lazy=True, foreign_keys='Interview.recruiter_id')
    interview_responses = db.relationship('InterviewResponse', backref='candidate', lazy=True)

class Interview(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    questions = db.Column(db.Text, nullable=False)  # JSON string of questions
    duration_minutes = db.Column(db.Integer, default=30)
    recruiter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    interview_type = db.Column(db.String(20), default='public')  # 'public', 'private', 'scheduled'
    requires_invitation = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Universal Access fields
    cross_org_accessible = db.Column(db.Boolean, default=False, nullable=False)
    public_invitation_enabled = db.Column(db.Boolean, default=False, nullable=False)
    max_concurrent_candidates = db.Column(db.Integer, default=1)
    
    # Relationships
    responses = db.relationship('InterviewResponse', backref='interview', lazy=True)
    invitations = db.relationship('InterviewInvitation', backref='interview', lazy=True)

class InterviewResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    answers = db.Column(db.Text, nullable=False)  # JSON string of answers
    ai_score = db.Column(db.Float, default=0.0)
    ai_feedback = db.Column(db.Text)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    time_taken_minutes = db.Column(db.Integer)
    status = db.Column(db.String(20), default='completed')  # completed, reviewed, pending
    
    # Composite unique constraint to prevent duplicate responses
    __table_args__ = (db.UniqueConstraint('interview_id', 'candidate_id', name='_interview_candidate_uc'),)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), default='text')  # 'text', 'multiple_choice'
    order_index = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Float, default=1.0)
    expected_keywords = db.Column(db.Text)  # JSON string of expected keywords for scoring

class VideoRecording(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    duration_seconds = db.Column(db.Integer)
    ai_analysis = db.Column(db.Text)  # JSON string of AI analysis results
    confidence_score = db.Column(db.Float, default=0.0)
    communication_style = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)
    
    # Relationships
    interview = db.relationship('Interview', backref='video_recordings')
    candidate = db.relationship('User', backref='video_recordings')

class TeamMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    organization_id = db.Column(db.Integer, nullable=False)  # For multi-tenant support
    role = db.Column(db.String(50), nullable=False, default='recruiter')  # admin, recruiter, viewer
    permissions = db.Column(db.Text)  # JSON string of permissions
    is_active = db.Column(db.Boolean, default=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    added_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    last_active = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='team_memberships')
    added_by_user = db.relationship('User', foreign_keys=[added_by])

class IntegrationSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, nullable=False)
    setting_type = db.Column(db.String(50), nullable=False)  # webhook, ats, etc.
    setting_key = db.Column(db.String(100), nullable=False)
    setting_value = db.Column(db.Text)
    is_encrypted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('organization_id', 'setting_type', 'setting_key', name='_org_setting_uc'),)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)
    resource_id = db.Column(db.Integer)
    details = db.Column(db.Text)  # JSON string with additional details
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='audit_logs')

class EmailNotification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    to_email = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(500), nullable=False)
    template_name = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed, bounced
    error_message = db.Column(db.Text)
    sent_at = db.Column(db.DateTime)
    opened_at = db.Column(db.DateTime)
    clicked_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Email tracking
    tracking_id = db.Column(db.String(36), unique=True)
    bounce_reason = db.Column(db.String(255))
    delivery_attempts = db.Column(db.Integer, default=0)
    
    # Relationships
    user = db.relationship('User', backref='email_notifications')

class NotificationPreference(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notification_type = db.Column(db.String(100), nullable=False)  # email type
    enabled = db.Column(db.Boolean, default=True)
    frequency = db.Column(db.String(20), default='immediate')  # immediate, daily, weekly, never
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='notification_preferences')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'notification_type', name='_user_notification_type_uc'),)

class InterviewSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recruiter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    scheduled_datetime = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=60)
    status = db.Column(db.String(20), default='scheduled')  # scheduled, confirmed, completed, cancelled
    meeting_link = db.Column(db.String(500))  # For video interviews
    calendar_event_id = db.Column(db.String(255))  # Google Calendar event ID
    time_zone = db.Column(db.String(50), default='UTC')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    interview = db.relationship('Interview', backref='schedules')
    candidate = db.relationship('User', foreign_keys=[candidate_id], backref='candidate_schedules')
    recruiter = db.relationship('User', foreign_keys=[recruiter_id], backref='recruiter_schedules')

class AvailabilitySlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    time_zone = db.Column(db.String(50), default='UTC')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='availability_slots')

class ScheduleNotification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('interview_schedule.id'), nullable=False)
    notification_type = db.Column(db.String(20), nullable=False)  # email, sms
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    send_at = db.Column(db.DateTime, nullable=False)
    sent_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')  # pending, sent, failed
    message_content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    schedule = db.relationship('InterviewSchedule', backref='notifications')
    recipient = db.relationship('User', backref='schedule_notifications')

class InterviewInvitation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recruiter_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, accepted, declined, expired
    invited_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    responded_at = db.Column(db.DateTime)
    message = db.Column(db.Text)  # Custom invitation message
    
    # Universal Access fields
    invitation_type = db.Column(db.String(20), default='direct')  # 'direct', 'public', 'cross_org'
    is_cross_organization = db.Column(db.Boolean, default=False, nullable=False)
    
    candidate = db.relationship('User', foreign_keys=[candidate_id], backref='interview_invitations')
    recruiter = db.relationship('User', foreign_keys=[recruiter_id], backref='sent_invitations')
    
    __table_args__ = (db.UniqueConstraint('interview_id', 'candidate_id', name='_interview_candidate_invitation_uc'),)

class InterviewApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    status = db.Column(db.String(20), default='applied')  # applied, reviewed, approved, rejected, interview_sent
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime)
    reviewer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    cover_letter = db.Column(db.Text)
    notes = db.Column(db.Text)  # Recruiter notes
    
    interview = db.relationship('Interview', backref='applications')
    candidate = db.relationship('User', foreign_keys=[candidate_id], backref='job_applications')
    reviewer = db.relationship('User', foreign_keys=[reviewer_id], backref='reviewed_applications')
    
    __table_args__ = (db.UniqueConstraint('interview_id', 'candidate_id', name='_interview_candidate_application_uc'),)


class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    website = db.Column(db.String(500))
    careers_page_url = db.Column(db.String(500))
    logo_url = db.Column(db.String(500))
    description = db.Column(db.Text)
    industry = db.Column(db.String(100))
    size = db.Column(db.String(50))  # startup, small, medium, large, enterprise
    location = db.Column(db.String(200))  # Headquarters location
    founded = db.Column(db.Integer)
    funding_stage = db.Column(db.String(50))  # seed, series-a, series-b, etc.
    tech_stack = db.Column(db.Text)  # JSON string of technologies used
    benefits = db.Column(db.Text)  # JSON string of company benefits
    culture_keywords = db.Column(db.Text)  # JSON string for company culture
    glassdoor_rating = db.Column(db.Float)
    is_hiring = db.Column(db.Boolean, default=True)
    last_scraped = db.Column(db.DateTime)
    scraping_enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    job_postings = db.relationship('JobPosting', backref='company', lazy=True, cascade='all, delete-orphan')
    saved_companies = db.relationship('SavedCompany', backref='company', lazy=True, cascade='all, delete-orphan')


class JobPosting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    requirements = db.Column(db.Text)
    responsibilities = db.Column(db.Text)
    location = db.Column(db.String(200))
    remote_type = db.Column(db.String(20), default='onsite')  # onsite, remote, hybrid
    employment_type = db.Column(db.String(20), default='full-time')  # full-time, part-time, contract, internship
    experience_level = db.Column(db.String(20))  # entry, mid, senior, lead, executive
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    salary_currency = db.Column(db.String(3), default='USD')
    salary_type = db.Column(db.String(10), default='yearly')  # yearly, monthly, hourly
    equity_offered = db.Column(db.Boolean, default=False)
    
    # Technical requirements
    technologies = db.Column(db.Text)  # JSON string of required technologies
    programming_languages = db.Column(db.Text)  # JSON string of programming languages
    frameworks = db.Column(db.Text)  # JSON string of frameworks
    databases = db.Column(db.Text)  # JSON string of databases
    cloud_platforms = db.Column(db.Text)  # JSON string of cloud platforms
    
    # Application details
    application_url = db.Column(db.String(500), nullable=False)
    application_email = db.Column(db.String(200))
    external_job_id = db.Column(db.String(100))  # Company's internal job ID
    posted_date = db.Column(db.DateTime)
    deadline = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    views_count = db.Column(db.Integer, default=0)
    applications_count = db.Column(db.Integer, default=0)
    
    # AI-generated insights
    ai_match_score = db.Column(db.Float)  # AI-calculated match score for trending skills
    trending_score = db.Column(db.Float)  # How trending this job type is
    difficulty_score = db.Column(db.Float)  # Estimated difficulty based on requirements
    
    # Metadata
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source = db.Column(db.String(50), default='scraper')  # scraper, manual, api
    
    # Relationships
    saved_jobs = db.relationship('SavedJob', backref='job_posting', lazy=True, cascade='all, delete-orphan')
    job_applications = db.relationship('JobApplication', backref='job_posting', lazy=True, cascade='all, delete-orphan')

    __table_args__ = (
        db.Index('idx_job_location', 'location'),
        db.Index('idx_job_remote_type', 'remote_type'),
        db.Index('idx_job_salary', 'salary_min', 'salary_max'),
        db.Index('idx_job_experience', 'experience_level'),
        db.Index('idx_job_active', 'is_active'),
        db.Index('idx_job_posted_date', 'posted_date'),
    )


class SavedJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_posting_id = db.Column(db.Integer, db.ForeignKey('job_posting.id'), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)  # User's personal notes about the job
    application_status = db.Column(db.String(20), default='interested')  # interested, applied, interviewing, rejected, offer
    reminder_date = db.Column(db.DateTime)  # User can set reminder to apply
    priority = db.Column(db.String(10), default='medium')  # low, medium, high

    user = db.relationship('User', backref='saved_jobs')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'job_posting_id', name='_user_job_save_uc'),)


class SavedCompany(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    notification_enabled = db.Column(db.Boolean, default=True)  # Notify when new jobs posted

    user = db.relationship('User', backref='saved_companies')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'company_id', name='_user_company_save_uc'),)


class JobApplication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    job_posting_id = db.Column(db.Integer, db.ForeignKey('job_posting.id'), nullable=False)
    application_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='applied')  # applied, under_review, interview_scheduled, rejected, offer
    cover_letter = db.Column(db.Text)
    resume_version = db.Column(db.String(100))  # Which version of resume was used
    follow_up_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    
    # Application tracking
    application_method = db.Column(db.String(20), default='direct')  # direct, linkedin, indeed, etc.
    referral_source = db.Column(db.String(100))  # If referred by someone
    estimated_response_time = db.Column(db.Integer)  # Days expected for response
    
    # AI-powered enhancements
    ai_match_score = db.Column(db.Float)  # AI-calculated match score (0-100)
    ai_insights = db.Column(db.Text)  # JSON string of AI-generated insights
    ai_generated_cover_letter = db.Column(db.Boolean, default=False)
    ai_custom_answers = db.Column(db.Text)  # JSON string of AI-generated custom answers
    ai_application_notes = db.Column(db.Text)  # AI-generated application notes
    

    auto_filled_fields = db.Column(db.Text)  # JSON string of auto-filled fields
    
    # Application performance tracking
    profile_completion_at_apply = db.Column(db.Float)  # Profile completion percentage when applied
    response_received = db.Column(db.Boolean, default=False)
    response_received_date = db.Column(db.DateTime)
    
    user = db.relationship('User', backref='job_applications_tracking')
    
    __table_args__ = (db.UniqueConstraint('user_id', 'job_posting_id', name='_user_job_application_uc'),)


class JobAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)  # User-defined name for the alert
    
    # Search criteria
    keywords = db.Column(db.Text)  # JSON string of keywords
    locations = db.Column(db.Text)  # JSON string of preferred locations
    remote_types = db.Column(db.Text)  # JSON string: onsite, remote, hybrid
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    experience_levels = db.Column(db.Text)  # JSON string of experience levels
    employment_types = db.Column(db.Text)  # JSON string of employment types
    companies = db.Column(db.Text)  # JSON string of specific company names
    technologies = db.Column(db.Text)  # JSON string of required technologies
    
    # Alert settings
    frequency = db.Column(db.String(20), default='daily')  # daily, weekly, immediate
    is_active = db.Column(db.Boolean, default=True)
    email_enabled = db.Column(db.Boolean, default=True)
    sms_enabled = db.Column(db.Boolean, default=False)
    last_sent = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='job_alerts')

class InterviewProgress(db.Model):
    __tablename__ = 'interview_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    
    responses = db.Column(db.Text)  # JSON string of current answers
    progress_percentage = db.Column(db.Integer, default=0)
    last_question = db.Column(db.Integer, default=0)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    interview = db.relationship('Interview', backref='progress_records')
    candidate = db.relationship('User', backref='interview_progress')
    organization = db.relationship('Organization', backref='interview_progress')
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('interview_id', 'candidate_id', name='unique_interview_candidate_progress'),
    )

class CoverLetter(db.Model):
    __tablename__ = 'cover_letters'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Cover letter details
    title = db.Column(db.String(200), nullable=False)
    company_name = db.Column(db.String(200))
    position_title = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    
    # Template information
    template_type = db.Column(db.String(50))  # 'google', 'amazon', 'tesla', 'frontend', 'product_manager', 'custom'
    industry = db.Column(db.String(100))
    job_level = db.Column(db.String(50))  # 'entry', 'mid', 'senior', 'executive'
    
    # AI generation metadata
    generated_by_ai = db.Column(db.Boolean, default=False)
    ai_prompt = db.Column(db.Text)  # Store the original prompt for regeneration
    generation_model = db.Column(db.String(50))  # 'gpt-4o', etc.
    
    # Status and settings
    is_favorite = db.Column(db.Boolean, default=False)
    is_template = db.Column(db.Boolean, default=False)  # User can save as personal template
    status = db.Column(db.String(20), default='draft')  # 'draft', 'final', 'sent'
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='cover_letters')

class CoverLetterTemplate(db.Model):
    __tablename__ = 'cover_letter_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Template details
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    company_type = db.Column(db.String(100))  # 'tech', 'startup', 'enterprise', 'government'
    role_type = db.Column(db.String(100))  # 'engineering', 'product', 'design', 'marketing'
    experience_level = db.Column(db.String(50))  # 'entry', 'mid', 'senior', 'executive'
    
    # Template content
    template_content = db.Column(db.Text, nullable=False)  # Template with placeholders
    example_content = db.Column(db.Text)  # Filled example for reference
    
    # Placeholders and instructions
    placeholders = db.Column(db.Text)  # JSON list of placeholder variables
    instructions = db.Column(db.Text)  # Instructions for using the template
    tips = db.Column(db.Text)  # Company-specific tips
    
    # Template metadata
    category = db.Column(db.String(50))  # 'company_specific', 'role_specific', 'general'
    tags = db.Column(db.Text)  # JSON array of tags for searching
    is_premium = db.Column(db.Boolean, default=False)
    usage_count = db.Column(db.Integer, default=0)
    
    # Quality metrics
    success_rate = db.Column(db.Float, default=0.0)  # Based on user feedback
    rating = db.Column(db.Float, default=0.0)
    rating_count = db.Column(db.Integer, default=0)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class CoverLetterFeedback(db.Model):
    __tablename__ = 'cover_letter_feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    cover_letter_id = db.Column(db.Integer, db.ForeignKey('cover_letters.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Feedback details
    rating = db.Column(db.Integer)  # 1-5 stars
    feedback_text = db.Column(db.Text)
    was_successful = db.Column(db.Boolean)  # Did it help get an interview/job?
    
    # Interview outcome tracking
    got_interview = db.Column(db.Boolean, default=False)
    got_job_offer = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    cover_letter = db.relationship('CoverLetter', backref='feedback')
    user = db.relationship('User', backref='cover_letter_feedback')


class CandidateTag(db.Model):
    __tablename__ = 'candidate_tag'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    color = db.Column(db.String(7), default='#6c757d')  # Hex color code
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    organization = db.relationship('Organization', backref='candidate_tags')
    creator = db.relationship('User', backref='created_tags')


class CandidateTagAssignment(db.Model):
    __tablename__ = 'candidate_tag_assignment'
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tag_id = db.Column(db.Integer, db.ForeignKey('candidate_tag.id'), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    candidate = db.relationship('User', foreign_keys=[candidate_id], backref='tag_assignments')
    tag = db.relationship('CandidateTag', backref='assignments')
    assigner = db.relationship('User', foreign_keys=[assigned_by])


class CandidateList(db.Model):
    __tablename__ = 'candidate_list'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = db.relationship('Organization', backref='candidate_lists')
    creator = db.relationship('User', backref='created_lists')


class CandidateListMembership(db.Model):
    __tablename__ = 'candidate_list_membership'
    id = db.Column(db.Integer, primary_key=True)
    list_id = db.Column(db.Integer, db.ForeignKey('candidate_list.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    added_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    candidate_list = db.relationship('CandidateList', backref='memberships')
    candidate = db.relationship('User', foreign_keys=[candidate_id], backref='list_memberships')
    adder = db.relationship('User', foreign_keys=[added_by])


class TechnicalInterviewAssignment(db.Model):
    """Assigns technical persons to interviews for feedback collection"""
    __tablename__ = 'technical_interview_assignment'
    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'), nullable=False)
    technical_person_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    interview_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'completed', 'cancelled'
    calendar_event_id = db.Column(db.String(100))  # Google Calendar event ID
    meeting_link = db.Column(db.String(500))  # Meeting URL for video interviews (Zoom, Google Meet, etc.)
    
    # Relationships
    interview = db.relationship('Interview', backref='technical_assignments')
    technical_person = db.relationship('User', foreign_keys=[technical_person_id], backref='technical_interviews')
    candidate = db.relationship('User', foreign_keys=[candidate_id], backref='technical_interview_assignments')
    assigner = db.relationship('User', foreign_keys=[assigned_by])
    
    # Unique constraint to prevent duplicate assignments
    __table_args__ = (db.UniqueConstraint('interview_id', 'technical_person_id', 'candidate_id', name='_tech_interview_assignment_uc'),)


class TechnicalInterviewFeedback(db.Model):
    """Stores feedback from technical persons after conducting interviews"""
    __tablename__ = 'technical_interview_feedback'
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('technical_interview_assignment.id'), nullable=False)
    technical_person_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'), nullable=False)
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'), nullable=False)
    
    # Feedback Decision
    decision = db.Column(db.String(20), nullable=False)  # 'selected', 'rejected', 'second_round'
    
    # Detailed Feedback
    technical_comments = db.Column(db.Text)
    communication_comments = db.Column(db.Text)
    overall_comments = db.Column(db.Text)
    
    # Skills Ratings (1-5 scale)
    technical_skills_rating = db.Column(db.Integer)  # 1-5
    problem_solving_rating = db.Column(db.Integer)  # 1-5
    communication_rating = db.Column(db.Integer)  # 1-5
    cultural_fit_rating = db.Column(db.Integer)  # 1-5
    
    # AI Integration
    ai_summary = db.Column(db.Text)  # AI-generated summary if used
    ai_suggestions = db.Column(db.Text)  # AI suggestions for improvement
    used_ai_assistance = db.Column(db.Boolean, default=False)
    
    # Metadata
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    interview_duration_minutes = db.Column(db.Integer)
    
    # Follow-up
    requires_second_round = db.Column(db.Boolean, default=False)
    second_round_notes = db.Column(db.Text)
    
    # Relationships
    assignment = db.relationship('TechnicalInterviewAssignment', backref='feedback')
    technical_person = db.relationship('User', foreign_keys=[technical_person_id], backref='given_feedback')
    candidate = db.relationship('User', foreign_keys=[candidate_id], backref='received_feedback')
    interview = db.relationship('Interview', backref='technical_feedback')


class TechnicalPersonNotification(db.Model):
    """Tracks notifications sent to technical persons"""
    __tablename__ = 'technical_person_notification'
    id = db.Column(db.Integer, primary_key=True)
    technical_person_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('technical_interview_assignment.id'), nullable=False)
    notification_type = db.Column(db.String(50), nullable=False)  # 'email', 'sms', 'push', 'in_app'
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='sent')  # 'sent', 'delivered', 'failed'
    content = db.Column(db.Text)  # Notification content
    
    # Relationships
    technical_person = db.relationship('User', backref='notifications')
    assignment = db.relationship('TechnicalInterviewAssignment', backref='notifications')

class CVAnalysis(db.Model):
    """CV analysis results storage"""
    __tablename__ = 'cv_analysis'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    overall_score = db.Column(db.Integer, nullable=False)
    format_score = db.Column(db.Integer, nullable=False)
    content_score = db.Column(db.Integer, nullable=False)
    sections_score = db.Column(db.Integer, nullable=False)
    style_score = db.Column(db.Integer, nullable=False)
    keywords_score = db.Column(db.Integer, nullable=False)
    
    # JSON fields for detailed analysis
    strengths = db.Column(db.Text)  # JSON array
    weaknesses = db.Column(db.Text)  # JSON array
    missing_sections = db.Column(db.Text)  # JSON array
    format_issues = db.Column(db.Text)  # JSON array
    content_suggestions = db.Column(db.Text)  # JSON array
    keyword_gaps = db.Column(db.Text)  # JSON array
    recommendations = db.Column(db.Text)  # JSON array
    detailed_feedback = db.Column(db.Text)  # JSON object
    
    # Analysis metadata
    analyzed_at = db.Column(db.DateTime, default=datetime.utcnow)
    cv_version = db.Column(db.String(50))  # Version identifier
    
    user = db.relationship('User', backref='cv_analyses')


class ResumeTemplate(db.Model):
    """ATS-friendly resume templates"""
    __tablename__ = 'resume_templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # 'modern', 'classic', 'minimalist', 'creative'
    template_type = db.Column(db.String(50), default='ats_friendly')  # 'ats_friendly', 'executive', 'student'
    css_styles = db.Column(db.Text)  # CSS for template styling
    html_template = db.Column(db.Text)  # HTML template structure
    is_active = db.Column(db.Boolean, default=True)
    is_premium = db.Column(db.Boolean, default=False)
    popularity_score = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    resumes = db.relationship('Resume', backref='template', lazy=True)


class Resume(db.Model):
    """User's resume data"""
    __tablename__ = 'resumes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('resume_templates.id'), nullable=False)
    
    # Basic Information
    title = db.Column(db.String(200), nullable=False, default='My Resume')
    is_default = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    version_number = db.Column(db.Integer, default=1)
    
    # Personal Information
    full_name = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    location = db.Column(db.String(200))
    linkedin_url = db.Column(db.String(300))
    portfolio_url = db.Column(db.String(300))
    website_url = db.Column(db.String(300))
    
    # Professional Summary
    professional_summary = db.Column(db.Text)
    headline = db.Column(db.String(200))
    
    # Skills (JSON arrays)
    technical_skills = db.Column(db.Text)  # JSON array
    soft_skills = db.Column(db.Text)  # JSON array
    languages = db.Column(db.Text)  # JSON array
    certifications = db.Column(db.Text)  # JSON array
    
    # Settings
    show_photo = db.Column(db.Boolean, default=False)
    photo_url = db.Column(db.String(300))
    color_scheme = db.Column(db.String(50), default='blue')
    font_style = db.Column(db.String(50), default='modern')
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_generated_at = db.Column(db.DateTime)
    
    # Relationships
    user = db.relationship('User', backref='resumes')
    work_experiences = db.relationship('ResumeWorkExperience', backref='resume', lazy=True, cascade='all, delete-orphan')
    educations = db.relationship('ResumeEducation', backref='resume', lazy=True, cascade='all, delete-orphan')
    projects = db.relationship('ResumeProject', backref='resume', lazy=True, cascade='all, delete-orphan')
    achievements = db.relationship('ResumeAchievement', backref='resume', lazy=True, cascade='all, delete-orphan')


class ResumeWorkExperience(db.Model):
    """Work experience entries for resumes"""
    __tablename__ = 'resume_work_experience'
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    
    # Company Information
    company_name = db.Column(db.String(200), nullable=False)
    job_title = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200))
    employment_type = db.Column(db.String(50))  # 'full-time', 'part-time', 'contract', 'internship'
    
    # Dates
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    is_current = db.Column(db.Boolean, default=False)
    
    # Content
    description = db.Column(db.Text)
    achievements = db.Column(db.Text)  # JSON array of bullet points
    technologies_used = db.Column(db.Text)  # JSON array
    
    # AI Enhancement
    ai_generated = db.Column(db.Boolean, default=False)
    ai_keywords = db.Column(db.Text)  # JSON array
    
    # Metadata
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ResumeEducation(db.Model):
    """Education entries for resumes"""
    __tablename__ = 'resume_education'
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    
    # Institution Information
    institution_name = db.Column(db.String(200), nullable=False)
    degree_type = db.Column(db.String(100))  # 'Bachelor', 'Master', 'PhD', 'Associate', 'Certificate'
    field_of_study = db.Column(db.String(200))
    location = db.Column(db.String(200))
    
    # Academic Details
    gpa = db.Column(db.String(10))
    honors = db.Column(db.String(200))
    relevant_coursework = db.Column(db.Text)  # JSON array
    
    # Dates
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    is_current = db.Column(db.Boolean, default=False)
    
    # Metadata
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ResumeProject(db.Model):
    """Project entries for resumes"""
    __tablename__ = 'resume_projects'
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    
    # Project Information
    project_name = db.Column(db.String(200), nullable=False)
    project_url = db.Column(db.String(300))
    repository_url = db.Column(db.String(300))
    
    # Content
    description = db.Column(db.Text)
    technologies_used = db.Column(db.Text)  # JSON array
    key_achievements = db.Column(db.Text)  # JSON array
    
    # Dates
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    is_ongoing = db.Column(db.Boolean, default=False)
    
    # AI Enhancement
    ai_generated = db.Column(db.Boolean, default=False)
    
    # Metadata
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ResumeAchievement(db.Model):
    """Additional achievements for resumes"""
    __tablename__ = 'resume_achievements'
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    
    # Achievement Information
    title = db.Column(db.String(200), nullable=False)
    organization = db.Column(db.String(200))
    description = db.Column(db.Text)
    achievement_date = db.Column(db.Date)
    category = db.Column(db.String(50))  # 'award', 'certification', 'publication', 'volunteer'
    
    # Links
    achievement_url = db.Column(db.String(300))
    certificate_url = db.Column(db.String(300))
    
    # Metadata
    order_index = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ResumeAnalysis(db.Model):
    """AI analysis of resumes for ATS optimization"""
    __tablename__ = 'resume_analysis'
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    job_description = db.Column(db.Text)  # Optional job description for targeted analysis
    
    # Analysis Scores (0-100)
    overall_score = db.Column(db.Integer, nullable=False)
    ats_compatibility = db.Column(db.Integer, nullable=False)
    keyword_optimization = db.Column(db.Integer, nullable=False)
    content_quality = db.Column(db.Integer, nullable=False)
    format_score = db.Column(db.Integer, nullable=False)
    length_optimization = db.Column(db.Integer, nullable=False)
    
    # Detailed Analysis (JSON)
    strengths = db.Column(db.Text)  # JSON array
    weaknesses = db.Column(db.Text)  # JSON array
    keyword_suggestions = db.Column(db.Text)  # JSON array
    improvement_suggestions = db.Column(db.Text)  # JSON array
    missing_keywords = db.Column(db.Text)  # JSON array
    ats_warnings = db.Column(db.Text)  # JSON array
    
    # Match Analysis
    job_match_percentage = db.Column(db.Integer)  # If job description provided
    top_matching_skills = db.Column(db.Text)  # JSON array
    missing_skills = db.Column(db.Text)  # JSON array
    
    # Metadata
    analyzed_at = db.Column(db.DateTime, default=datetime.utcnow)
    analysis_version = db.Column(db.String(10), default='1.0')
    
    # Relationships
    resume = db.relationship('Resume', backref='analyses')


class ResumeFeedback(db.Model):
    """User feedback and ratings for resume templates"""
    __tablename__ = 'resume_feedback'
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('resume_templates.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Feedback
    rating = db.Column(db.Integer)  # 1-5 stars
    feedback_text = db.Column(db.Text)
    ease_of_use = db.Column(db.Integer)  # 1-5
    design_quality = db.Column(db.Integer)  # 1-5
    ats_effectiveness = db.Column(db.Integer)  # 1-5
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    resume = db.relationship('Resume')
    template = db.relationship('ResumeTemplate')
    user = db.relationship('User')


class InterviewPracticeSession(db.Model):
    """Store interview practice sessions and generated questions for data persistence"""
    __tablename__ = 'interview_practice_session'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)  # 'Easy', 'Medium', 'Hard'
    questions_data = db.Column(db.JSON)  # Stores generated questions as JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)  # Track if this is the current session
    
    # Relationships
    user = db.relationship('User', backref='interview_practice_sessions')
    
    def __repr__(self):
        return f'<InterviewPracticeSession {self.topic}-{self.difficulty}>'


class Message(db.Model):
    """Message model for recruiter-candidate communication"""
    __tablename__ = 'messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(50), default='direct')  # direct, application, interview, system
    related_job_id = db.Column(db.Integer, db.ForeignKey('job_posting.id'), nullable=True)
    related_application_id = db.Column(db.Integer, db.ForeignKey('job_application.id'), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    is_archived = db.Column(db.Boolean, default=False)
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')
    related_job = db.relationship('JobPosting', backref='messages')
    related_application = db.relationship('JobApplication', backref='messages')


class NotificationSettings(db.Model):
    """User notification preferences"""
    __tablename__ = 'notification_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    email_notifications = db.Column(db.Boolean, default=True)
    sms_notifications = db.Column(db.Boolean, default=False)
    push_notifications = db.Column(db.Boolean, default=True)
    message_notifications = db.Column(db.Boolean, default=True)
    application_updates = db.Column(db.Boolean, default=True)
    interview_reminders = db.Column(db.Boolean, default=True)
    job_alerts = db.Column(db.Boolean, default=True)
    weekly_digest = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='notification_settings')


class TeamCollaboration(db.Model):
    """Team collaboration for hiring decisions"""
    __tablename__ = 'team_collaboration'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('job_application.id'), nullable=False)
    team_member_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # reviewer, decision_maker, observer
    feedback = db.Column(db.Text, nullable=True)
    recommendation = db.Column(db.String(20), nullable=True)  # hire, reject, interview, hold
    confidence_score = db.Column(db.Integer, nullable=True)  # 1-10 scale
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    application = db.relationship('JobApplication', backref='team_feedback')
    team_member = db.relationship('User', backref='collaboration_feedback')
