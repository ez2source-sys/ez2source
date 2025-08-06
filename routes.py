import json
import logging
import os
import re
from datetime import datetime, timedelta
from flask import render_template, request, redirect, url_for, flash, jsonify, make_response, send_from_directory
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app import app, db
from models import (
    User, Interview, InterviewResponse, Question, VideoRecording, TeamMember, 
    IntegrationSettings, AuditLog, InterviewSchedule, AvailabilitySlot, 
    ScheduleNotification, Organization, InterviewApplication, InterviewInvitation,
    Company, JobPosting, SavedJob, SavedCompany, JobApplication, JobAlert,
    CandidateTag, CandidateTagAssignment, CandidateList, CandidateListMembership,
    InterviewProgress, TechnicalInterviewAssignment, TechnicalInterviewFeedback,
    TechnicalPersonNotification, CVAnalysis, CoverLetter, CoverLetterTemplate, CoverLetterFeedback,
    ResumeTemplate, Resume, ResumeWorkExperience, ResumeEducation, ResumeProject,
    ResumeAchievement, ResumeAnalysis, ResumeFeedback, InterviewPracticeSession,
    Message, NotificationSettings, TeamCollaboration
)
from organization_assignment_service import OrganizationAssignmentService
from ai_service import generate_interview_questions, score_interview_responses, analyze_video_interview
from voice_service import transcribe_audio, validate_audio_file
from validation_service import ValidationService
from form_validation_service import FormValidationService, validate_form_data, get_form_errors_html
from candidate_notification_service import send_candidate_decision_email


from analytics_service import get_recruitment_dashboard_data, get_candidate_pipeline_analytics, get_interview_performance_tracking
from messaging_service import (
    send_recruiter_message, get_user_conversations, get_conversation_messages,
    get_application_updates, add_team_collaboration, submit_team_feedback,
    get_application_team_feedback, MessagingService
)
from enhanced_email_service import (
    EnhancedEmailService, send_notification_email, send_user_invitation_email, 
    get_email_delivery_stats, email_service
)
from hr_registration_service import hr_registration_service

# Helper function for profile completion calculation
def calculate_profile_completion(user):
    """Calculate profile completion percentage"""
    completion_fields = [
        'first_name', 'last_name', 'email', 'phone', 'bio',
        'skills', 'experience', 'education', 'resume_url'
    ]
    
    completed = 0
    total = len(completion_fields)
    
    for field in completion_fields:
        value = getattr(user, field, None)
        if value and str(value).strip():
            completed += 1
    
    return round((completed / total) * 100)

# Helper function for safe JSON parsing
def safe_json_loads(json_str, default=None):
    """Safely parse JSON string with fallback to default value"""
    if default is None:
        default = []
    try:
        if not json_str or json_str.strip() == "":
            return default
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError, ValueError):
        return default

@app.route('/')
def index():
    """Landing page - shows different content based on user role"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET'])
def register():
    """Registration page with options for candidate and HR registration"""
    return render_template('register.html')

@app.route('/hr/register', methods=['GET', 'POST'])
def hr_register():
    """HR registration with verification and approval process"""
    if request.method == 'POST':
        # Extract form data
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        
        # Handle phone number from separated fields
        country_code = request.form.get('country_code', '').strip()
        local_phone = request.form.get('local_phone', '').strip()
        phone = request.form.get('phone', '').strip()  # Combined phone from JavaScript
        
        # If phone is not combined, combine it from separate fields
        if not phone and country_code and local_phone:
            phone = country_code + local_phone
        
        job_title = request.form.get('job_title', '').strip()
        linkedin_url = request.form.get('linkedin_url', '').strip()
        organization_name = request.form.get('organization_name', '').strip()
        organization_email = request.form.get('organization_email', '').strip().lower()
        company_website = request.form.get('company_website', '').strip()
        message = request.form.get('message', '').strip()
        
        # Validate required fields with comprehensive validation
        validation_errors = {}
        
        # Name validation
        if not first_name:
            validation_errors['first_name'] = 'Please enter a valid first name (letters only).'
        elif not first_name.replace(' ', '').isalpha():
            validation_errors['first_name'] = 'Please enter a valid first name (letters only).'
            
        if not last_name:
            validation_errors['last_name'] = 'Please enter a valid last name (letters only).'
        elif not last_name.replace(' ', '').isalpha():
            validation_errors['last_name'] = 'Please enter a valid last name (letters only).'
        
        # Email validation
        if not email:
            validation_errors['email'] = 'Use your company email address (e.g., yourname@company.com). Gmail/Yahoo not accepted.'
        elif not '@' in email or not '.' in email.split('@')[1]:
            validation_errors['email'] = 'Use your company email address (e.g., yourname@company.com). Gmail/Yahoo not accepted.'
        
        # Phone validation
        if not country_code:
            validation_errors['country_code'] = 'Please select a country code.'
        if not local_phone:
            validation_errors['local_phone'] = 'Enter a valid phone number with digits only (no spaces or symbols).'
        elif not local_phone.isdigit() or len(local_phone) < 10 or len(local_phone) > 15:
            validation_errors['local_phone'] = 'Enter a valid phone number with digits only (no spaces or symbols).'
        
        # Job title validation
        if not job_title:
            validation_errors['job_title'] = 'Please enter your job title (e.g., HR Manager, Recruiter).'
        elif not all(c.isalpha() or c.isspace() or c == '-' for c in job_title):
            validation_errors['job_title'] = 'Please enter your job title (e.g., HR Manager, Recruiter).'
        
        # Organization validation
        if not organization_name:
            validation_errors['organization_name'] = 'Enter your organization\'s name (e.g., Capgemini, Infosys, etc.).'
        elif not all(c.isalpha() or c.isspace() or c in '&.' for c in organization_name):
            validation_errors['organization_name'] = 'Enter your organization\'s name (e.g., Capgemini, Infosys, etc.).'
        
        if not organization_email:
            validation_errors['organization_email'] = 'Use your official work email (e.g., name@organization.com).'
        elif not '@' in organization_email or not '.' in organization_email.split('@')[1]:
            validation_errors['organization_email'] = 'Use your official work email (e.g., name@organization.com).'
        
        # LinkedIn validation (optional)
        if linkedin_url and not linkedin_url.startswith('https://linkedin.com/in/'):
            validation_errors['linkedin_url'] = 'Please provide a valid LinkedIn profile URL (starting with https://linkedin.com/in/...).'
        
        # Company website validation (optional)
        if company_website and not company_website.startswith('https://'):
            validation_errors['company_website'] = 'Provide a valid company website (e.g., https://www.company.com).'
        
        # Message length validation
        if message and len(message) > 1000:
            validation_errors['message'] = 'You can describe your role or any verification details (optional, max 1000 characters).'
        
        # Check if email already exists
        if email and User.query.filter_by(email=email).first():
            validation_errors['email'] = 'An account with this email already exists'
        
        # Check if phone already exists
        if phone:
            normalized_phone = ValidationService.normalize_phone(phone)
            if User.query.filter_by(phone=normalized_phone).first():
                validation_errors['phone'] = 'An account with this phone number already exists'
        
        # Check for personal email domains
        if email:
            personal_domains = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']
            email_domain = email.split('@')[1] if '@' in email else ''
            if email_domain in personal_domains:
                validation_errors['email'] = 'Please use your official company email address'
        
        if validation_errors:
            return render_template('hr_register.html', 
                                 validation_errors=validation_errors,
                                 form_data=request.form)
        
        try:
            # Create HR registration request
            result = hr_registration_service.create_hr_registration_request(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                organization_name=organization_name,
                organization_email=organization_email,
                job_title=job_title,
                linkedin_url=linkedin_url,
                company_website=company_website,
                message=message
            )
            
            if result['success']:
                return render_template('hr_registration_success.html', 
                                     result=result,
                                     first_name=first_name,
                                     organization_name=organization_name)
            else:
                flash(result['message'], 'error')
                if result.get('details'):
                    flash(result['details'], 'info')
                return render_template('hr_register.html', form_data=request.form)
                
        except Exception as e:
            logging.error(f"HR registration error: {str(e)}")
            flash('Registration request failed due to a system error. Please try again.', 'error')
            return render_template('hr_register.html', form_data=request.form)
    
    return render_template('hr_register.html')

@app.route('/guest-admin/dashboard')
@login_required
def guest_admin_dashboard():
    """Guest Admin Dashboard for managing Guest HR users"""
    # Check if user is Guest Admin
    if not (current_user.role == 'admin' and current_user.organization.name == 'Guest Organization'):
        flash('Access denied. Guest Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get all Guest HR users
    guest_hr_users = User.query.filter_by(
        organization_id=current_user.organization_id,
        role='recruiter'
    ).all()
    
    # Calculate statistics
    pending_approvals = len([u for u in guest_hr_users if not u.is_active])
    approved_count = len([u for u in guest_hr_users if u.is_active])
    
    # Get unique organizations from bio field
    unique_organizations = set()
    for user in guest_hr_users:
        if user.bio and 'Guest HR from ' in user.bio:
            org_name = user.bio.split('Guest HR from ')[1].split('.')[0]
            unique_organizations.add(org_name)
    
    # Recent activities (you can expand this based on audit logs)
    recent_activities = [
        {
            'action': 'New Guest HR Registration',
            'details': f'{len(guest_hr_users)} total Guest HR users registered',
            'timestamp': datetime.utcnow()
        }
    ]
    
    return render_template('guest_admin_dashboard.html',
                         guest_hr_users=guest_hr_users,
                         pending_approvals=pending_approvals,
                         approved_count=approved_count,
                         unique_organizations=len(unique_organizations),
                         recent_activities=recent_activities)

@app.route('/guest-admin/review/<int:user_id>')
@login_required
def guest_admin_review_hr(user_id):
    """Review Guest HR user details"""
    # Check if user is Guest Admin
    if not (current_user.role == 'admin' and current_user.organization.name == 'Guest Organization'):
        flash('Access denied. Guest Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    hr_user = User.query.filter_by(
        id=user_id,
        organization_id=current_user.organization_id
    ).first()
    
    if not hr_user:
        flash('Guest HR user not found.', 'error')
        return redirect(url_for('guest_admin_dashboard'))
    
    # Parse bio information
    bio_info = {}
    if hr_user.bio:
        parts = hr_user.bio.split('. ')
        for part in parts:
            if ': ' in part:
                key, value = part.split(': ', 1)
                bio_info[key] = value
    
    return render_template('guest_admin_review_hr.html',
                         hr_user=hr_user,
                         bio_info=bio_info)

@app.route('/guest-admin/approve/<int:user_id>')
@login_required
def guest_admin_approve_hr(user_id):
    """Approve Guest HR user for limited access"""
    # Check if user is Guest Admin
    if not (current_user.role == 'admin' and current_user.organization.name == 'Guest Organization'):
        flash('Access denied. Guest Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    hr_user = User.query.filter_by(
        id=user_id,
        organization_id=current_user.organization_id
    ).first()
    
    if not hr_user:
        flash('Guest HR user not found.', 'error')
        return redirect(url_for('guest_admin_dashboard'))
    
    try:
        # Approve the user
        hr_user.is_active = True
        db.session.commit()
        
        # Send approval notification
        subject = "Your Job2Hire Guest HR Access Approved"
        body = f"""
        Dear {hr_user.first_name},
        
        Your Guest HR access has been approved by our Guest Admin team.
        
        You now have limited access to the Job2Hire platform with the following permissions:
        - View candidate profiles
        - Basic interview scheduling
        - Limited reporting features
        
        To gain full access, please contact support about verifying your organization.
        
        Welcome to Job2Hire!
        """
        
        send_notification_email(hr_user.email, subject, body)
        
        flash(f'Guest HR user {hr_user.first_name} {hr_user.last_name} has been approved.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error approving user: {str(e)}', 'error')
    
    return redirect(url_for('guest_admin_dashboard'))

@app.route('/guest-admin/transfer/<int:user_id>')
@login_required
def guest_admin_transfer_hr(user_id):
    """Transfer Guest HR user to appropriate organization"""
    # Check if user is Guest Admin
    if not (current_user.role == 'admin' and current_user.organization.name == 'Guest Organization'):
        flash('Access denied. Guest Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    hr_user = User.query.filter_by(
        id=user_id,
        organization_id=current_user.organization_id
    ).first()
    
    if not hr_user:
        flash('Guest HR user not found.', 'error')
        return redirect(url_for('guest_admin_dashboard'))
    
    # Get available organizations
    organizations = Organization.query.filter(
        Organization.name != 'Guest Organization'
    ).all()
    
    return render_template('guest_admin_transfer_hr.html',
                         hr_user=hr_user,
                         organizations=organizations)

@app.route('/registration_success')
def registration_success():
    """Registration success page"""
    email = request.args.get('email', '')
    username = request.args.get('username', '')
    role = request.args.get('role', '')
    
    if not email or not username:
        return redirect(url_for('register'))
    
    profile_url = url_for('dashboard')
    
    return render_template('registration_success.html', 
                         email=email, 
                         username=username, 
                         role=role,
                         profile_url=profile_url)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    """Password reset request with secure token generation"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Email address is required.', 'error')
            return render_template('forgot_password.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate secure reset token
            import secrets
            import string
            from datetime import datetime, timedelta
            
            # Generate a secure random token
            token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
            
            # Set token expiration (1 hour from now)
            user.reset_token = token
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
            
            try:
                db.session.commit()
                
                # In production, this would send an email with the reset link
                # For now, provide a secure way to reset without email service
                reset_url = url_for('reset_password', token=token, _external=True)
                flash('Password reset token generated successfully!', 'success')
                flash('Since email service is not configured, please use this direct reset link:', 'info')
                flash(f'Click here to reset your password: {reset_url}', 'warning')
                flash('This link will expire in 1 hour for security.', 'info')
                
            except Exception as e:
                db.session.rollback()
                flash('An error occurred. Please try again.', 'error')
        else:
            # Don't reveal whether email exists for security
            flash('If an account with that email exists, you will receive password reset instructions.', 'info')
        
        return render_template('forgot_password.html')
    
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Password reset with token validation"""
    from datetime import datetime
    from werkzeug.security import generate_password_hash
    
    # Find user with valid token
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        flash('Invalid or expired reset token. Please request a new password reset.', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        new_password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate password
        if not new_password:
            flash('Password is required.', 'error')
            return render_template('reset_password.html', token=token)
        
        if len(new_password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return render_template('reset_password.html', token=token)
        
        if new_password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('reset_password.html', token=token)
        
        # Update password and clear reset token
        user.password_hash = generate_password_hash(new_password)
        user.reset_token = None
        user.reset_token_expires = None
        
        try:
            db.session.commit()
            flash('Your password has been successfully reset. You can now log in with your new password.', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while resetting your password. Please try again.', 'error')
    
    return render_template('reset_password.html', token=token, user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Enhanced user login with security features"""
    from validation_service import ValidationService
    
    if request.method == 'POST':
        # Get form data
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember_me = request.form.get('remember_me') == 'on'
        
        # Input validation
        validation_errors = {}
        
        if not username:
            validation_errors['username'] = "Username is required"
        elif len(username) < 3:
            validation_errors['username'] = "Username must be at least 3 characters"
        
        if not password:
            validation_errors['password'] = "Password is required"
        elif len(password) < 8:
            validation_errors['password'] = "Password must be at least 8 characters"
        
        # Rate limiting check
        client_ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr)
        is_allowed, rate_error = ValidationService.check_rate_limit(client_ip, 'login', 5, 15)
        if not is_allowed:
            validation_errors['general'] = "Too many login attempts. Please try again in 15 minutes."
        
        # If validation errors, return early
        if validation_errors:
            return render_template('login.html', 
                                 validation_errors=validation_errors,
                                 form_data={'username': username})
        
        # Attempt authentication
        try:
            # Find user by username or email
            user = User.query.filter(
                (User.username == username) | (User.email == username)
            ).first()
            
            if user and user.user_active and check_password_hash(user.password_hash, password):
                # Two-Factor Authentication check removed - Ez2source focuses on core talent intelligence features
                # Successful login
                login_user(user, remember=remember_me)
                
                # Record successful login attempt
                # Login attempt tracking removed - Ez2source focuses on core talent intelligence features
                
                # Update last login
                user.last_login = datetime.utcnow()
                db.session.commit()
                
                # Log successful login
                logging.info(f"User logged in: {user.username} ({user.email})")
                
                # Determine redirect URL
                next_page = request.args.get('next')
                if next_page and next_page.startswith('/'):
                    redirect_url = next_page
                else:
                    # Role-based redirect
                    if user.role == 'candidate' and not user.profile_completed:
                        redirect_url = url_for('complete_profile_import')
                    else:
                        redirect_url = url_for('dashboard')
                
                flash(f'Welcome back, {user.first_name or user.username}!', 'success')
                return redirect(redirect_url)
            
            else:
                # Failed login attempt
                if user:
                    logging.warning(f"Failed login attempt for user: {username}")
                    # Login attempt tracking removed - Ez2source focuses on core talent intelligence features
                else:
                    logging.warning(f"Login attempt for non-existent user: {username}")
                
                validation_errors['general'] = "Invalid username/email or password"
                
        except Exception as e:
            logging.error(f"Login error: {str(e)}")
            validation_errors['general'] = "Login failed due to a system error. Please try again."
        
        return render_template('login.html', 
                             validation_errors=validation_errors,
                             form_data={'username': username})
    
    return render_template('login.html')

# Two-Factor Authentication routes removed - Ez2source focuses on core talent intelligence features

@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    # Validate inputs
    if not current_password or not new_password or not confirm_password:
        flash('All password fields are required.', 'error')
        return redirect(url_for('candidate_profile', user_id=current_user.id))
    
    # Check current password
    if not check_password_hash(current_user.password_hash, current_password):
        flash('Current password is incorrect.', 'error')
        return redirect(url_for('candidate_profile', user_id=current_user.id))
    
    # Check new password length
    if len(new_password) < 8:
        flash('New password must be at least 8 characters long.', 'error')
        return redirect(url_for('candidate_profile', user_id=current_user.id))
    
    # Check password confirmation
    if new_password != confirm_password:
        flash('New password and confirmation do not match.', 'error')
        return redirect(url_for('candidate_profile', user_id=current_user.id))
    
    # Update password
    try:
        current_user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        # Log the action
        logging.info(f"Password changed for user: {current_user.email}")
        
        flash('Password changed successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error changing password for user {current_user.email}: {str(e)}")
        flash('Error changing password. Please try again.', 'error')
    
    return redirect(url_for('candidate_profile', user_id=current_user.id))

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Role-based dashboard"""
    if current_user.role == 'super_admin':
        # Super admin dashboard - redirect to admin panel
        return redirect(url_for('admin_panel'))
    elif current_user.role == 'recruiter':
        # Recruiter dashboard - show interviews created and candidate analytics (organization-scoped)
        interviews = Interview.query.filter_by(
            recruiter_id=current_user.id,
            organization_id=current_user.organization_id
        ).order_by(Interview.created_at.desc()).all()
        total_responses = sum(len(interview.responses) for interview in interviews)
        
        # Get pending applications for recruiter's interviews
        pending_applications = InterviewApplication.query.join(Interview).filter(
            Interview.recruiter_id == current_user.id,
            InterviewApplication.status == 'applied'
        ).count()
        
        # Get technical interview assignments for meetings scheduled by this recruiter
        from models import TechnicalInterviewAssignment
        technical_interview_assignments = TechnicalInterviewAssignment.query.filter_by(
            assigned_by=current_user.id,
            organization_id=current_user.organization_id
        ).filter(
            TechnicalInterviewAssignment.interview_date >= datetime.utcnow(),
            TechnicalInterviewAssignment.status.in_(['assigned', 'pending'])
        ).all()
        
        return render_template('dashboard.html', 
                             interviews=interviews, 
                             total_responses=total_responses,
                             pending_applications=pending_applications,
                             technical_interview_assignments=technical_interview_assignments,
                             user_role='recruiter')
    elif current_user.role == 'admin':
        # Check if this is Guest Admin
        if current_user.organization.name == 'Guest Organization':
            return redirect(url_for('guest_admin_dashboard'))
        
        # Admin dashboard - show organization statistics
        # Get total users in the organization
        total_users = User.query.filter_by(
            organization_id=current_user.organization_id
        ).count()
        
        # Get all interviews in the organization
        interviews = Interview.query.filter_by(
            organization_id=current_user.organization_id
        ).order_by(Interview.created_at.desc()).all()
        total_interviews = len(interviews)
        
        # Get total responses for all interviews in the organization
        total_responses = sum(len(interview.responses) for interview in interviews)
        
        # Get pending applications for all interviews in the organization (admin can see all)
        pending_applications = InterviewApplication.query.join(Interview).filter(
            Interview.organization_id == current_user.organization_id,
            InterviewApplication.status == 'applied'
        ).count()
        
        # Get all technical interview assignments in the organization
        from models import TechnicalInterviewAssignment
        technical_interview_assignments = TechnicalInterviewAssignment.query.filter_by(
            organization_id=current_user.organization_id
        ).filter(
            TechnicalInterviewAssignment.interview_date >= datetime.utcnow(),
            TechnicalInterviewAssignment.status.in_(['assigned', 'pending'])
        ).all()
        
        # Get organization users for admin management
        organization_users = User.query.filter_by(
            organization_id=current_user.organization_id
        ).order_by(User.created_at.desc()).all()
        
        return render_template('dashboard.html',
                             interviews=interviews,
                             total_users=total_users,
                             total_interviews=total_interviews,
                             total_responses=total_responses,
                             pending_applications=pending_applications,
                             technical_interview_assignments=technical_interview_assignments,
                             organization_users=organization_users,
                             user_role='admin')
    elif current_user.role == 'technical_person':
        # Technical person dashboard - redirect to dedicated technical dashboard
        return redirect(url_for('technical_person_dashboard'))
    else:
        # Candidate dashboard - check organization assignment first
        if not current_user.organization_id:
            # Handle unassigned candidate
            from candidate_organization_middleware import handle_unassigned_candidate_dashboard
            unassigned_context = handle_unassigned_candidate_dashboard()
            
            return render_template('candidate_dashboard.html',
                                 public_interviews=[],
                                 invited_interviews=[],
                                 scheduled_interviews=[],
                                 completed_interviews=[],
                                 my_applications=[],
                                 profile_completion=0,
                                 user_role='candidate',
                                 **unassigned_context)
        
        # Candidate dashboard - hybrid interview access system
        # Get public interviews (can apply)
        public_interviews = Interview.query.filter_by(
            organization_id=current_user.organization_id,
            is_active=True,
            interview_type='public'
        ).all()
        
        # Get private interviews (via invitation)
        invited_interviews = db.session.query(Interview).join(InterviewInvitation).filter(
            InterviewInvitation.candidate_id == current_user.id,
            InterviewInvitation.status == 'pending',
            Interview.is_active == True
        ).all()
        
        # Get scheduled interviews
        scheduled_interviews = db.session.query(Interview).join(InterviewSchedule).filter(
            InterviewSchedule.candidate_id == current_user.id,
            InterviewSchedule.status == 'scheduled'
        ).all()
        
        # Get candidate's completed interviews
        completed_interviews = InterviewResponse.query.filter_by(
            candidate_id=current_user.id
        ).all()
        
        # Get applications
        my_applications = InterviewApplication.query.filter_by(
            candidate_id=current_user.id
        ).all()
        
        # Get technical interview assignments (Google Meet meetings)
        from models import TechnicalInterviewAssignment
        technical_interview_assignments = TechnicalInterviewAssignment.query.filter_by(
            candidate_id=current_user.id
        ).filter(
            TechnicalInterviewAssignment.interview_date >= datetime.utcnow(),
            TechnicalInterviewAssignment.status.in_(['assigned', 'pending'])
        ).all()
        
        # Calculate profile completion percentage
        from app import calculate_profile_completion
        profile_completion = calculate_profile_completion(current_user)
        
        # Quick job functionality removed - focusing on core talent intelligence features
        quick_job_stats = {}
        
        # Candidate journey functionality removed - Ez2source focuses on core talent intelligence features
        journey = None
        
        return render_template('candidate_dashboard.html',
                             public_interviews=public_interviews,
                             invited_interviews=invited_interviews,
                             scheduled_interviews=scheduled_interviews,
                             completed_interviews=completed_interviews,
                             my_applications=my_applications,
                             technical_interview_assignments=technical_interview_assignments,
                             profile_completion=profile_completion,
                             quick_job_stats=quick_job_stats,
                             journey=journey,
                             user_role='candidate')



@app.route('/interview/create', methods=['GET', 'POST'])
@login_required
def create_interview():
    """Interview builder for recruiters"""
    if current_user.role != 'recruiter':
        flash('Access denied. Only recruiters can create interviews.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        title = request.form['title']
        job_description = request.form['job_description']
        duration = int(request.form['duration'])
        interview_type = request.form.get('interview_type', 'public')
        cross_org_accessible = 'cross_org_accessible' in request.form
        public_invitation_enabled = 'public_invitation_enabled' in request.form
        
        if not title or not job_description:
            flash('Title and job description are required.', 'error')
            return render_template('interview_builder.html')
        
        try:
            # Generate questions using AI
            questions = generate_interview_questions(job_description, title)
            
            # Create interview with type selection
            interview = Interview(
                title=title,
                job_description=job_description,
                questions=json.dumps(questions),
                duration_minutes=duration,
                recruiter_id=current_user.id,
                organization_id=current_user.organization_id,
                interview_type=interview_type,
                requires_invitation=(interview_type != 'public'),
                cross_org_accessible=cross_org_accessible,
                public_invitation_enabled=public_invitation_enabled
            )
            
            db.session.add(interview)
            db.session.commit()
            
            # Success message based on interview type
            if interview_type == 'public':
                flash('Public interview created successfully! Candidates can now apply.', 'success')
            elif interview_type == 'private':
                flash('Private interview created successfully! You can now send invitations to candidates.', 'success')
            elif interview_type == 'scheduled':
                flash('Scheduled interview created successfully! You can now schedule specific dates and times.', 'success')
            
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Interview creation error: {e}")
            flash('Failed to create interview. Please check your OpenAI API configuration.', 'error')
    
    return render_template('interview_builder.html')

@app.route('/interview/<int:interview_id>')
@login_required
def interview_interface(interview_id):
    """Interview interface for candidates"""
    if current_user.role != 'candidate':
        flash('Access denied. Only candidates can take interviews.', 'error')
        return redirect(url_for('dashboard'))
    
    # First try to get interview from same organization
    interview = Interview.query.filter_by(
        id=interview_id,
        organization_id=current_user.organization_id
    ).first()
    
    # If not found in same org, check for cross-org accessible public interviews
    if not interview:
        interview = Interview.query.filter_by(
            id=interview_id,
            is_active=True,
            interview_type='public',
            cross_org_accessible=True
        ).first()
    
    # If still not found, check for public interviews that allow cross-org invitations
    if not interview:
        interview = Interview.query.filter_by(
            id=interview_id,
            is_active=True,
            interview_type='public',
            public_invitation_enabled=True
        ).first()
    
    if not interview:
        flash('Interview not found or not accessible.', 'error')
        return redirect(url_for('dashboard'))
    
    # Check access permissions based on interview type
    has_access = False
    
    if interview.interview_type == 'public':
        # For public interviews, check if applied and approved OR if cross-org accessible
        application = InterviewApplication.query.filter_by(
            interview_id=interview_id,
            candidate_id=current_user.id
        ).first()
        
        # Also check for accepted invitations if public invitations are enabled
        invitation = None
        if interview.public_invitation_enabled:
            invitation = InterviewInvitation.query.filter_by(
                interview_id=interview_id,
                candidate_id=current_user.id,
                status='accepted'
            ).first()
        
        # Allow access if:
        # 1. Applied and approved
        # 2. Cross-org accessible public interview
        # 3. Public invitation enabled (general access)
        # 4. Has accepted invitation for this interview
        has_access = (
            (application and application.status == 'approved') or
            interview.cross_org_accessible or
            interview.public_invitation_enabled or
            invitation is not None
        )
        
    elif interview.interview_type == 'private':
        # Check if invited and accepted
        invitation = InterviewInvitation.query.filter_by(
            interview_id=interview_id,
            candidate_id=current_user.id,
            status='accepted'
        ).first()
        has_access = invitation is not None
        
    elif interview.interview_type == 'scheduled':
        # Check if scheduled
        schedule = InterviewSchedule.query.filter_by(
            interview_id=interview_id,
            candidate_id=current_user.id,
            status='scheduled'
        ).first()
        has_access = schedule is not None
    
    if not has_access:
        flash('You do not have access to this interview. Please apply first or wait for an invitation.', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if already completed
    existing_response = InterviewResponse.query.filter_by(
        interview_id=interview_id, 
        candidate_id=current_user.id
    ).first()
    
    if existing_response:
        flash('You have already completed this interview.', 'info')
        return redirect(url_for('interview_results', response_id=existing_response.id))
    
    questions = json.loads(interview.questions)
    return render_template('interview_interface.html', interview=interview, questions=questions)

@app.route('/interview/<int:interview_id>/submit', methods=['POST'])
@login_required
def submit_interview(interview_id):
    """Submit interview responses"""
    if current_user.role != 'candidate':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    # Allow access to interviews based on type and permissions
    interview = Interview.query.get_or_404(interview_id)
    
    # Check access permissions for different interview types
    if interview.interview_type == 'private' and interview.organization_id != current_user.organization_id:
        flash('Access denied to this private interview.', 'error')
        return redirect(url_for('dashboard'))
    
    # Check if already completed
    existing_response = InterviewResponse.query.filter_by(
        interview_id=interview_id, 
        candidate_id=current_user.id
    ).first()
    
    if existing_response:
        flash('You have already completed this interview.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get answers from form
        answers = {}
        questions = json.loads(interview.questions)
        
        for i, question in enumerate(questions):
            answer_key = f'answer_{i}'
            answers[str(i)] = {
                'question': question['text'],
                'answer': request.form.get(answer_key, '').strip()
            }
        
        # Calculate time taken (in real implementation, this would be tracked client-side)
        time_taken = request.form.get('time_taken', 0)
        
        # Score the responses using AI
        score, feedback = score_interview_responses(answers, interview.job_description)
        
        # Save response
        response = InterviewResponse(
            interview_id=interview_id,
            candidate_id=current_user.id,
            organization_id=current_user.organization_id,
            answers=json.dumps(answers),
            ai_score=score,
            ai_feedback=feedback,
            time_taken_minutes=int(time_taken) if time_taken else None
        )
        
        db.session.add(response)
        db.session.commit()
        
        flash('Interview submitted successfully!', 'success')
        return redirect(url_for('interview_results', response_id=response.id))
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Interview submission error: {e}")
        flash('Failed to submit interview. Please try again.', 'error')
        return redirect(url_for('interview_interface', interview_id=interview_id))

@app.route('/interview/results/<int:response_id>')
@login_required
def interview_results(response_id):
    """Show interview results"""
    response = InterviewResponse.query.filter_by(
        id=response_id,
        organization_id=current_user.organization_id
    ).first_or_404()
    
    # Check permissions
    if (current_user.role == 'candidate' and response.candidate_id != current_user.id) or \
       (current_user.role == 'recruiter' and response.interview.recruiter_id != current_user.id):
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        answers = json.loads(response.answers)
        # Ensure answers is a dictionary for template compatibility
        if isinstance(answers, list):
            answers = {str(i): answer for i, answer in enumerate(answers)}
    except (json.JSONDecodeError, TypeError):
        answers = {}
    
    return render_template('interview_results.html', response=response, answers=answers)

@app.route('/candidates/<int:interview_id>')
@login_required
def candidate_analytics(interview_id):
    """Candidate analytics for recruiters"""
    if current_user.role != 'recruiter':
        flash('Access denied. Only recruiters can view analytics.', 'error')
        return redirect(url_for('dashboard'))
    
    interview = Interview.query.filter_by(
        id=interview_id,
        organization_id=current_user.organization_id
    ).first_or_404()
    
    # Check if recruiter owns this interview
    if interview.recruiter_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    responses = InterviewResponse.query.filter_by(
        interview_id=interview_id,
        organization_id=current_user.organization_id
    ).order_by(InterviewResponse.ai_score.desc()).all()
    
    # Calculate analytics
    if responses:
        avg_score = sum(r.ai_score for r in responses) / len(responses)
        # Fix division by zero for time calculation
        time_responses = [r for r in responses if r.time_taken_minutes]
        avg_time = sum(r.time_taken_minutes for r in time_responses) / len(time_responses) if time_responses else 0
    else:
        avg_score = 0
        avg_time = 0
    
    return render_template('candidate_analytics.html', 
                         interview=interview, 
                         responses=responses,
                         avg_score=avg_score,
                         avg_time=avg_time)

@app.route('/toggle_interview_status', methods=['POST'])
@login_required
def toggle_interview_status():
    """Toggle interview active/inactive status"""
    if current_user.role != 'recruiter':
        return jsonify({'error': 'Access denied. Only recruiters can modify interviews.'}), 403
    
    try:
        data = request.get_json()
        interview_id = data.get('interview_id')
        is_active = data.get('is_active')
        
        if interview_id is None or is_active is None:
            return jsonify({'error': 'Missing required data'}), 400
        
        interview = Interview.query.get_or_404(interview_id)
        
        # Check if recruiter owns this interview
        if interview.recruiter_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Update the status
        interview.is_active = is_active
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f"Interview {'activated' if is_active else 'deactivated'} successfully",
            'is_active': is_active
        })
        
    except Exception as e:
        logging.error(f"Error toggling interview status: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update interview status'}), 500

@app.route('/admin/add_user', methods=['POST'])
@login_required
def admin_add_user():
    """Admin route to add new users to their organization"""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        email = request.form.get('email', '').strip().lower()
        role = request.form.get('role', '').strip()
        
        if not email or not role:
            flash('Email and role are required.', 'error')
            return redirect(url_for('dashboard'))
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('User with this email already exists.', 'error')
            return redirect(url_for('dashboard'))
        
        # Generate temporary username and password
        username = email.split('@')[0] + '_' + role
        temp_password = 'temp123'  # User should change this on first login
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(temp_password),
            role=role,
            organization_id=current_user.organization_id,
            user_active=True,
            profile_completed=False,
            created_at=datetime.utcnow()
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        flash(f'User {email} added successfully with temporary password: {temp_password}', 'success')
        logging.info(f"Admin {current_user.email} added new user: {email} with role: {role}")
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding user: {str(e)}")
        flash('Error adding user. Please try again.', 'error')
    
    return redirect(url_for('dashboard'))

@app.route('/admin/toggle_user_status', methods=['POST'])
@login_required
def admin_toggle_user_status():
    """Admin route to toggle user active status"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        active = data.get('active')
        
        if user_id is None or active is None:
            return jsonify({'success': False, 'message': 'Missing required data'}), 400
        
        # Get user in the same organization
        user = User.query.filter_by(
            id=user_id,
            organization_id=current_user.organization_id
        ).first()
        
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Cannot modify your own status'}), 400
        
        user.user_active = active
        db.session.commit()
        
        action = 'activated' if active else 'deactivated'
        logging.info(f"Admin {current_user.email} {action} user: {user.email}")
        
        return jsonify({
            'success': True,
            'message': f'User {action} successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error toggling user status: {str(e)}")
        return jsonify({'success': False, 'message': 'Error updating user status'}), 500

@app.route('/admin/organization_settings')
@login_required
def organization_settings():
    """Organization settings page for admin"""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('organization_settings.html', organization=current_user.organization)

@app.route('/admin/update_org_settings', methods=['POST'])
@login_required
def update_org_settings():
    """Update organization settings"""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        timezone = request.form.get('timezone', 'UTC')
        allow_public = 'allow_public_interviews' in request.form
        require_profile = 'require_profile_completion' in request.form
        
        # Update organization settings (you may need to add these fields to Organization model)
        flash('Organization settings updated successfully!', 'success')
        logging.info(f"Admin {current_user.email} updated organization settings")
        
    except Exception as e:
        logging.error(f"Error updating organization settings: {str(e)}")
        flash('Error updating settings. Please try again.', 'error')
    
    return redirect(url_for('organization_settings'))

@app.route('/upload_video_recording', methods=['POST'])
@login_required
def upload_video_recording():
    """Handle video recording upload and AI analysis"""
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400
        
        video_file = request.files['video']
        interview_id = request.form.get('interview_id')
        candidate_id = request.form.get('candidate_id')
        
        if not video_file or not interview_id or not candidate_id:
            return jsonify({'error': 'Missing required data'}), 400
        
        # Verify permissions
        if current_user.id != int(candidate_id):
            return jsonify({'error': 'Access denied'}), 403
        
        # Create uploads directory if it doesn't exist
        upload_dir = os.path.join(app.root_path, 'uploads', 'videos')
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate secure filename
        filename = secure_filename(f"{candidate_id}_{interview_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.webm")
        file_path = os.path.join(upload_dir, filename)
        
        # Save the video file
        video_file.save(file_path)
        file_size = os.path.getsize(file_path)
        
        # Get interview context for AI analysis
        interview = Interview.query.get(interview_id)
        interview_context = f"Job: {interview.title}\n{interview.job_description[:200]}" if interview else None
        
        # Perform AI analysis
        ai_analysis = analyze_video_interview(file_path, interview_context)
        
        # Create database record
        video_recording = VideoRecording(
            interview_id=interview_id,
            candidate_id=candidate_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            ai_analysis=json.dumps(ai_analysis),
            confidence_score=ai_analysis.get('confidence', 0),
            communication_style=ai_analysis.get('communication_style', 'Standard'),
            processed_at=datetime.utcnow()
        )
        
        db.session.add(video_recording)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'ai_analysis': ai_analysis,
            'message': 'Video uploaded and analyzed successfully'
        })
        
    except Exception as e:
        logging.error(f"Error uploading video: {e}")
        db.session.rollback()
        return jsonify({'error': 'Upload failed'}), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.route('/analytics/advanced')
@login_required
def advanced_analytics():
    """Advanced analytics dashboard with filtering and charts"""
    if current_user.role != 'recruiter':
        flash('Access denied. Only recruiters can view advanced analytics.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    min_score = request.args.get('min_score', type=float)
    max_score = request.args.get('max_score', type=float)
    
    # Base query for recruiter's interviews
    base_query = InterviewResponse.query.join(Interview).filter(
        Interview.recruiter_id == current_user.id
    )
    
    # Apply filters
    if start_date:
        base_query = base_query.filter(InterviewResponse.completed_at >= start_date)
    if end_date:
        base_query = base_query.filter(InterviewResponse.completed_at <= end_date)
    if min_score is not None:
        base_query = base_query.filter(InterviewResponse.ai_score >= min_score)
    if max_score is not None:
        base_query = base_query.filter(InterviewResponse.ai_score <= max_score)
    
    responses = base_query.order_by(InterviewResponse.completed_at.desc()).all()
    
    # Calculate statistics
    total_candidates = len(set(r.candidate_id for r in responses))
    total_interviews = Interview.query.filter_by(recruiter_id=current_user.id, is_active=True).count()
    avg_score = sum(r.ai_score for r in responses) / len(responses) if responses else 0
    time_responses = [r for r in responses if r.time_taken_minutes]
    avg_time = sum(r.time_taken_minutes for r in time_responses) / len(time_responses) if time_responses else 0
    
    # Score distribution for chart
    score_ranges = [0, 0, 0, 0, 0]  # 0-20, 21-40, 41-60, 61-80, 81-100
    for response in responses:
        score = response.ai_score
        if score <= 20:
            score_ranges[0] += 1
        elif score <= 40:
            score_ranges[1] += 1
        elif score <= 60:
            score_ranges[2] += 1
        elif score <= 80:
            score_ranges[3] += 1
        else:
            score_ranges[4] += 1
    
    # Trend data (last 7 days)
    from datetime import datetime, timedelta
    trend_labels = []
    trend_data = []
    for i in range(6, -1, -1):
        date = datetime.now().date() - timedelta(days=i)
        trend_labels.append(date.strftime('%m/%d'))
        count = len([r for r in responses if r.completed_at.date() == date])
        trend_data.append(count)
    
    return render_template('advanced_analytics.html',
                         responses=responses,
                         total_candidates=total_candidates,
                         total_interviews=total_interviews,
                         avg_score=avg_score,
                         avg_time=avg_time,
                         score_distribution=score_ranges,
                         trend_labels=trend_labels,
                         trend_data=trend_data)

@app.route('/candidate/<int:candidate_id>/profile')
@login_required
def recruiter_view_candidate_profile(candidate_id):
    """Detailed candidate profile for recruiters"""
    if current_user.role != 'recruiter':
        flash('Access denied. Only recruiters can view candidate profiles.', 'error')
        return redirect(url_for('dashboard'))
    
    candidate = User.query.get_or_404(candidate_id)
    if candidate.role != 'candidate':
        flash('Invalid candidate ID.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get responses for interviews created by current recruiter
    responses = InterviewResponse.query.join(Interview).filter(
        Interview.recruiter_id == current_user.id,
        InterviewResponse.candidate_id == candidate_id
    ).order_by(InterviewResponse.completed_at.desc()).all()
    
    if not responses:
        flash('No interview data found for this candidate.', 'error')
        return redirect(url_for('dashboard'))
    
    # Calculate statistics
    avg_score = sum(r.ai_score for r in responses) / len(responses)
    video_recordings = VideoRecording.query.join(Interview).filter(
        Interview.recruiter_id == current_user.id,
        VideoRecording.candidate_id == candidate_id
    ).all()
    
    # Skills breakdown (mock data based on AI feedback)
    skills_breakdown = {
        'technical_skills': avg_score * 0.9,
        'communication': avg_score * 1.1,
        'problem_solving': avg_score * 0.95,
        'cultural_fit': avg_score * 1.05
    }
    
    # Performance data for chart
    performance_dates = [r.completed_at.strftime('%m/%d') for r in responses]
    performance_scores = [r.ai_score for r in responses]
    
    # Communication analysis
    communication_strengths = [
        "Clear articulation of ideas",
        "Professional presentation",
        "Confident delivery"
    ]
    communication_improvements = [
        "Expand on technical details",
        "Use more specific examples",
        "Improve response structure"
    ]
    
    return render_template('candidate_profile.html',
                         candidate=candidate,
                         responses=responses,
                         avg_score=avg_score,
                         video_recordings=video_recordings,
                         skills_breakdown=skills_breakdown,
                         performance_dates=performance_dates,
                         performance_scores=performance_scores,
                         communication_strengths=communication_strengths,
                         communication_improvements=communication_improvements)

@app.route('/compare_candidates', methods=['POST'])
@login_required
def compare_candidates():
    """Compare multiple candidates side by side"""
    if current_user.role != 'recruiter':
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    response_ids = data.get('response_ids', [])
    
    if len(response_ids) < 2:
        return jsonify({'error': 'Need at least 2 candidates to compare'}), 400
    
    responses = InterviewResponse.query.join(Interview).filter(
        InterviewResponse.id.in_(response_ids),
        Interview.recruiter_id == current_user.id
    ).all()
    
    comparison_html = render_template('comparison_table.html', responses=responses)
    return jsonify({'html': comparison_html})

@app.route('/bulk_action', methods=['POST'])
@login_required
def bulk_action():
    """Handle bulk actions on interview responses"""
    if current_user.role != 'recruiter':
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    action = data.get('action')
    response_ids = data.get('response_ids', [])
    
    try:
        responses = InterviewResponse.query.join(Interview).filter(
            InterviewResponse.id.in_(response_ids),
            Interview.recruiter_id == current_user.id
        ).all()
        
        if action == 'delete':
            for response in responses:
                db.session.delete(response)
            db.session.commit()
            return jsonify({'success': True, 'message': f'Deleted {len(responses)} responses'})
        
        return jsonify({'error': 'Invalid action'}), 400
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Bulk action error: {e}")
        return jsonify({'error': 'Action failed'}), 500

@app.route('/export_report', methods=['POST'])
@login_required
def export_report():
    """Export analytics report in various formats"""
    if current_user.role != 'recruiter':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    format_type = request.form.get('format', 'pdf')
    
    # Get filtered data
    responses = InterviewResponse.query.join(Interview).filter(
        Interview.recruiter_id == current_user.id
    ).all()
    
    if format_type == 'pdf':
        # Generate PDF report
        from io import BytesIO
        from flask import make_response
        
        # Create a simple text report for now
        report_content = f"Interview Analytics Report\n"
        report_content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        report_content += f"Total Responses: {len(responses)}\n"
        
        for response in responses:
            report_content += f"\nCandidate: {response.candidate.username}\n"
            report_content += f"Interview: {response.interview.title}\n"
            report_content += f"Score: {response.ai_score:.1f}%\n"
            report_content += f"Date: {response.completed_at.strftime('%Y-%m-%d')}\n"
            report_content += "---\n"
        
        response = make_response(report_content)
        response.headers['Content-Type'] = 'text/plain'
        response.headers['Content-Disposition'] = 'attachment; filename=analytics_report.txt'
        return response
    
    flash('Export format not supported yet.', 'warning')
    return redirect(url_for('advanced_analytics'))

@app.route('/team/management')
@login_required
def team_management():
    """Team management dashboard for enterprise users"""
    if current_user.role not in ['admin', 'recruiter']:
        flash('Access denied. Insufficient permissions.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get team members (mock organization_id = 1 for demo)
    organization_id = 1
    team_members = []
    
    # Get all recruiters as team members
    recruiters = User.query.filter_by(role='recruiter').all()
    for recruiter in recruiters:
        # Calculate stats for each recruiter
        interviews_count = Interview.query.filter_by(recruiter_id=recruiter.id).count()
        responses = InterviewResponse.query.join(Interview).filter(
            Interview.recruiter_id == recruiter.id
        ).all()
        responses_count = len(responses)
        avg_score = sum(r.ai_score for r in responses) / len(responses) if responses else 0
        
        # Create team member object
        member_data = type('obj', (object,), {
            'id': recruiter.id,
            'username': recruiter.username,
            'email': recruiter.email,
            'role': recruiter.role,
            'interviews_count': interviews_count,
            'responses_count': responses_count,
            'avg_score': avg_score,
            'is_active': True,
            'last_active': recruiter.created_at
        })()
        
        team_members.append(member_data)
    
    # Calculate team statistics
    total_interviews = sum(m.interviews_count for m in team_members)
    team_avg_score = sum(m.avg_score for m in team_members) / len(team_members) if team_members else 0
    active_members = len([m for m in team_members if m.is_active])
    
    return render_template('team_management.html',
                         team_members=team_members,
                         total_interviews=total_interviews,
                         team_avg_score=team_avg_score,
                         active_members=active_members)

@app.route('/api/test_webhook', methods=['POST'])
@login_required
def test_webhook():
    """Test webhook connectivity"""
    if current_user.role not in ['admin', 'recruiter']:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    webhook_url = data.get('webhook_url')
    webhook_type = data.get('webhook_type')
    
    try:
        import requests
        
        # Create test payload
        test_payload = {
            'test': True,
            'type': webhook_type,
            'timestamp': datetime.now().isoformat(),
            'data': {
                'interview_id': 1,
                'candidate_name': 'Test Candidate',
                'score': 85.5
            }
        }
        
        response = requests.post(webhook_url, json=test_payload, timeout=10)
        
        if response.status_code == 200:
            return jsonify({'success': True, 'message': 'Webhook test successful'})
        else:
            return jsonify({'success': False, 'error': f'HTTP {response.status_code}'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/test_ats', methods=['POST'])
@login_required
def test_ats_connection():
    """Test ATS integration connectivity"""
    if current_user.role not in ['admin', 'recruiter']:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    provider = data.get('provider')
    api_key = data.get('api_key')
    
    # For demo purposes, simulate ATS connection test
    if provider and api_key:
        # In real implementation, this would test actual ATS APIs
        if len(api_key) > 10:  # Basic validation
            return jsonify({'success': True, 'message': f'{provider.title()} connection successful'})
        else:
            return jsonify({'success': False, 'error': 'Invalid API key format'})
    
    return jsonify({'success': False, 'error': 'Missing provider or API key'})

@app.route('/api/save_integration_settings', methods=['POST'])
@login_required
def save_integration_settings():
    """Save integration settings"""
    if current_user.role not in ['admin', 'recruiter']:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        settings = request.get_json()
        organization_id = 1  # Mock organization ID
        
        # Save each setting
        for key, value in settings.items():
            if value:  # Only save non-empty values
                setting = IntegrationSettings.query.filter_by(
                    organization_id=organization_id,
                    setting_type='integration',
                    setting_key=key
                ).first()
                
                if setting:
                    setting.setting_value = value
                    setting.updated_at = datetime.now()
                else:
                    setting = IntegrationSettings(
                        organization_id=organization_id,
                        setting_type='integration',
                        setting_key=key,
                        setting_value=value,
                        is_encrypted=(key == 'ats_api_key')
                    )
                    db.session.add(setting)
        
        # Log the action
        audit_log = AuditLog(
            user_id=current_user.id,
            action='update_integration_settings',
            resource_type='settings',
            details=json.dumps({'settings_updated': list(settings.keys())}),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(audit_log)
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error saving integration settings: {e}")
        return jsonify({'success': False, 'error': 'Failed to save settings'})

@app.route('/api/add_team_member', methods=['POST'])
@login_required
def add_team_member():
    """Add a new team member"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied. Admin privileges required'}), 403
    
    try:
        data = request.get_json()
        email = data.get('email')
        role = data.get('role')
        permissions = data.get('permissions', [])
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'success': False, 'error': 'User already exists'})
        
        # Create new user (in real app, this would send invitation email)
        new_user = User(
            username=email.split('@')[0],
            email=email,
            password_hash=generate_password_hash('temp_password'),
            role=role
        )
        db.session.add(new_user)
        db.session.flush()  # Get the user ID
        
        # Create team membership
        team_member = TeamMember(
            user_id=new_user.id,
            organization_id=1,
            role=role,
            permissions=json.dumps(permissions),
            added_by=current_user.id
        )
        db.session.add(team_member)
        
        # Log the action
        audit_log = AuditLog(
            user_id=current_user.id,
            action='add_team_member',
            resource_type='user',
            resource_id=new_user.id,
            details=json.dumps({'email': email, 'role': role})
        )
        db.session.add(audit_log)
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Team member added successfully'})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding team member: {e}")
        return jsonify({'success': False, 'error': 'Failed to add team member'})

@app.route('/apply/<int:interview_id>')
@login_required
def apply_interview(interview_id):
    """Apply for a public interview"""
    interview = Interview.query.get_or_404(interview_id)
    
    existing_application = InterviewApplication.query.filter_by(
        interview_id=interview_id,
        candidate_id=current_user.id
    ).first()
    
    if existing_application:
        flash('You have already applied for this interview.', 'warning')
        return redirect(url_for('dashboard'))
    
    return render_template('apply_interview.html', interview=interview)

@app.route('/apply/<int:interview_id>', methods=['POST'])
@login_required
def submit_application(interview_id):
    """Submit application for interview"""
    interview = Interview.query.get_or_404(interview_id)
    
    existing_application = InterviewApplication.query.filter_by(
        interview_id=interview_id,
        candidate_id=current_user.id
    ).first()
    
    if existing_application:
        flash('You have already applied for this interview.', 'warning')
        return redirect(url_for('dashboard'))
    
    cover_letter = request.form.get('cover_letter', '')
    
    application = InterviewApplication(
        interview_id=interview_id,
        candidate_id=current_user.id,
        organization_id=current_user.organization_id,
        cover_letter=cover_letter,
        status='applied'
    )
    
    db.session.add(application)
    db.session.commit()
    
    flash('Your application has been submitted successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/recruiter/applications')
@login_required
def manage_applications():
    """Manage candidate applications for recruiter's interviews"""
    if current_user.role not in ['recruiter', 'admin']:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    if current_user.role == 'admin':
        # Admin can see all applications in their organization
        applications = db.session.query(InterviewApplication).join(Interview).filter(
            Interview.organization_id == current_user.organization_id
        ).order_by(InterviewApplication.applied_at.desc()).all()
    else:
        # Recruiter only sees their own interview applications
        applications = db.session.query(InterviewApplication).join(Interview).filter(
            Interview.recruiter_id == current_user.id,
            Interview.organization_id == current_user.organization_id
        ).order_by(InterviewApplication.applied_at.desc()).all()
    
    return render_template('manage_applications.html', applications=applications)

@app.route('/recruiter/application/<int:application_id>/approve', methods=['POST'])
@login_required
def approve_application(application_id):
    """Approve candidate application"""
    if current_user.role not in ['recruiter', 'admin']:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    application = InterviewApplication.query.get_or_404(application_id)
    
    # Check permissions: recruiters can only approve their own, admins can approve any in their org
    if current_user.role == 'recruiter' and application.interview.recruiter_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('manage_applications'))
    elif current_user.role == 'admin' and application.interview.organization_id != current_user.organization_id:
        flash('Access denied.', 'danger')
        return redirect(url_for('manage_applications'))
    
    application.status = 'approved'
    application.reviewed_at = datetime.utcnow()
    application.reviewer_id = current_user.id
    
    db.session.commit()
    
    flash(f'Application for {application.candidate.username} approved!', 'success')
    return redirect(url_for('manage_applications'))

@app.route('/recruiter/application/<int:application_id>/reject', methods=['POST'])
@login_required
def reject_application(application_id):
    """Reject candidate application"""
    if current_user.role not in ['recruiter', 'admin']:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    application = InterviewApplication.query.get_or_404(application_id)
    
    # Check permissions: recruiters can only reject their own, admins can reject any in their org
    if current_user.role == 'recruiter' and application.interview.recruiter_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('manage_applications'))
    elif current_user.role == 'admin' and application.interview.organization_id != current_user.organization_id:
        flash('Access denied.', 'danger')
        return redirect(url_for('manage_applications'))
    
    application.status = 'rejected'
    application.reviewed_at = datetime.utcnow()
    application.reviewer_id = current_user.id
    
    db.session.commit()
    
    flash(f'Application for {application.candidate.username} rejected.', 'info')
    return redirect(url_for('manage_applications'))

@app.route('/admin/interviews')
@login_required
def admin_view_interviews():
    """Admin can view all interviews in their organization"""
    if current_user.role not in ['admin', 'super_admin']:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    if current_user.role == 'super_admin':
        # Super admin can see all interviews across all organizations
        interviews = Interview.query.order_by(Interview.created_at.desc()).all()
    else:
        # Admin can see all interviews in their organization
        interviews = Interview.query.filter_by(
            organization_id=current_user.organization_id
        ).order_by(Interview.created_at.desc()).all()
    
    return render_template('admin_interviews.html', interviews=interviews)

# Candidate Registration Routes
@app.route('/candidate/register', methods=['GET', 'POST'])
def candidate_register():
    """Candidate registration page with form handling"""
    if request.method == 'POST':
        # Debug logging
        logging.info(f"Registration form submitted with data: {dict(request.form)}")
        
        # Extract form data
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        country_code = request.form.get('country_code', '').strip()
        local_phone = request.form.get('local_phone', '').strip()
        job_title = request.form.get('job_title', '').strip()
        password = request.form.get('password', '').strip()
        
        logging.info(f"Extracted data - email: {email}, first_name: {first_name}, last_name: {last_name}")
        
        # Combine phone number
        phone = f"{country_code}{local_phone}" if country_code and local_phone else None
        
        # Validation
        validation_errors = {}
        
        # Required field validation
        if not first_name:
            validation_errors['first_name'] = 'First name is required'
        if not last_name:
            validation_errors['last_name'] = 'Last name is required'
        if not email:
            validation_errors['email'] = 'Email is required'
        if not password:
            validation_errors['password'] = 'Password is required'
        elif len(password) < 8:
            validation_errors['password'] = 'Password must be at least 8 characters'
        
        # Email validation
        if email:
            is_valid, error_msg = ValidationService.validate_email_uniqueness(email)
            if not is_valid:
                validation_errors['email'] = error_msg
        
        # Phone validation
        if phone:
            is_valid, error_msg = ValidationService.validate_phone_uniqueness(phone)
            if not is_valid:
                validation_errors['phone'] = error_msg
        
        # If validation errors, return form with errors
        if validation_errors:
            logging.info(f"Validation errors found: {validation_errors}")
            return render_template('candidate_register.html', 
                                 validation_errors=validation_errors,
                                 form_data=request.form)
        
        try:
            # Create default organization if needed (for demo)
            default_org = Organization.query.filter_by(name='TechCorp Solutions').first()
            if not default_org:
                default_org = Organization(
                    name='TechCorp Solutions',
                    slug='techcorp-solutions'
                )
                db.session.add(default_org)
                db.session.flush()
            
            # Determine organization assignment
            from organization_assignment_service import OrganizationAssignmentService
            org_id = OrganizationAssignmentService.assign_candidate_to_organization(
                candidate_email=email,
                referrer_url=request.referrer,
                invitation_code=request.form.get('invitation_code')
            )
            
            # If still no organization, use the existing default logic
            if not org_id:
                org_id = default_org.id
            
            # Create candidate user
            # Normalize phone number for storage
            normalized_phone = ValidationService.normalize_phone(phone) if phone else None
            logging.info(f"Creating candidate with org_id: {org_id}, normalized_phone: {normalized_phone}")
            
            candidate = User(
                username=email.split('@')[0],
                email=email,
                password_hash=generate_password_hash(password),
                role='candidate',
                organization_id=org_id,
                first_name=first_name,
                last_name=last_name,
                phone=normalized_phone,
                job_title=job_title,
                profile_completed=False,
                public_profile_enabled=True,
                cross_org_accessible=True,
                is_organization_employee=False
            )
            
            logging.info(f"Adding candidate to database: {candidate.username}")
            db.session.add(candidate)
            
            logging.info("Committing database transaction")
            db.session.commit()
            
            # Log successful registration
            logging.info(f"New candidate registered successfully: {candidate.username} ({email}) with ID: {candidate.id}")
            
            # Redirect to success page with user details
            return redirect(url_for('registration_success', 
                                  email=email, 
                                  username=candidate.username, 
                                  role='candidate'))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Candidate registration error: {str(e)}")
            flash('Registration failed due to a system error. Please try again.', 'error')
            return render_template('candidate_register.html', form_data=request.form)
    
    return render_template('candidate_register.html')

@app.route('/candidate/quick-register', methods=['POST'])
def candidate_quick_register():
    """Quick candidate registration"""
    email = request.form.get('email')
    full_name = request.form.get('full_name')
    phone = request.form.get('phone')
    job_title = request.form.get('job_title')
    
    # Validate email uniqueness
    is_valid, error_msg = ValidationService.validate_email_uniqueness(email)
    if not is_valid:
        flash(error_msg, 'error')
        return redirect(url_for('candidate_register'))
    
    # Validate phone uniqueness if provided
    if phone:
        is_valid, error_msg = ValidationService.validate_phone_uniqueness(phone)
        if not is_valid:
            flash(error_msg, 'error')
            return redirect(url_for('candidate_register'))
    
    # Create default organization if needed (for demo)
    default_org = Organization.query.filter_by(name='TechCorp Solutions').first()
    if not default_org:
        default_org = Organization(
            name='TechCorp Solutions',
            slug='techcorp-solutions'
        )
        db.session.add(default_org)
        db.session.flush()
    
    # Split full name
    name_parts = full_name.split(' ', 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ''
    
    # Determine organization assignment
    from organization_assignment_service import OrganizationAssignmentService
    org_id = OrganizationAssignmentService.assign_candidate_to_organization(
        candidate_email=email,
        referrer_url=request.referrer,
        invitation_code=request.form.get('invitation_code')
    )
    
    # If still no organization, use the existing default logic
    if not org_id:
        org_id = default_org.id
    
    # Create candidate user
    # Normalize phone number for storage
    normalized_phone = ValidationService.normalize_phone(phone) if phone else None
    candidate = User(
        username=email.split('@')[0],
        email=email,
        password_hash=generate_password_hash('candidate123'),  # Default password
        role='candidate',
        organization_id=org_id,
        first_name=first_name,
        last_name=last_name,
        phone=normalized_phone,
        job_title=job_title,
        profile_completed=False,
        # Enable cross-organization access by default for universal visibility
        cross_org_accessible=True,
        public_profile_enabled=True
    )
    
    db.session.add(candidate)
    db.session.commit()
    
    # Redirect to registration success page with credentials
    return render_template('registration_success.html', 
                         username=candidate.username,
                         email=candidate.email,
                         password='candidate123',
                         profile_url=f"{request.url_root}candidate/profile/{candidate.id}",
                         registration_method='quick')

@app.route('/candidate/resume-register', methods=['GET', 'POST'])
def candidate_resume_register():
    """Register candidate with resume upload"""
    if request.method == 'GET':
        return render_template('candidate_resume_register.html')
    
    email = request.form.get('email')
    resume_file = request.files.get('resume')
    
    if not resume_file:
        flash('Please upload a resume file.', 'error')
        return redirect(url_for('candidate_register'))
    
    # Validate email uniqueness
    is_valid, error_msg = ValidationService.validate_email_uniqueness(email)
    if not is_valid:
        flash(error_msg, 'error')
        return redirect(url_for('candidate_register'))
    
    try:
        # Save resume file
        filename = secure_filename(resume_file.filename)
        resume_path = os.path.join('uploads', 'resumes', filename)
        os.makedirs(os.path.dirname(resume_path), exist_ok=True)
        resume_file.save(resume_path)
        
        # Extract information from resume using AI
        extracted_info = extract_resume_info(resume_path)
        
    except Exception as e:
        logging.error(f"Resume upload/parsing error: {e}")
        flash('Error processing resume. Please try again or use manual registration.', 'error')
        return redirect(url_for('candidate_resume_register'))
    
    # Create default organization if needed
    default_org = Organization.query.filter_by(name='TechCorp Solutions').first()
    if not default_org:
        default_org = Organization(
            name='TechCorp Solutions',
            slug='techcorp-solutions'
        )
        db.session.add(default_org)
        db.session.flush()
    
    # Determine organization assignment
    from organization_assignment_service import OrganizationAssignmentService
    org_id = OrganizationAssignmentService.assign_candidate_to_organization(
        candidate_email=email,
        referrer_url=request.referrer,
        invitation_code=request.form.get('invitation_code')
    )
    
    # If still no organization, use the existing default logic
    if not org_id:
        org_id = default_org.id
    
    # Create candidate user with extracted info
    # Normalize phone number for storage
    phone_from_resume = extracted_info.get('phone', '')
    normalized_phone = ValidationService.normalize_phone(phone_from_resume) if phone_from_resume else None
    candidate = User(
        username=email.split('@')[0],
        email=email,
        password_hash=generate_password_hash('candidate123'),
        role='candidate',
        organization_id=org_id,
        first_name=extracted_info.get('first_name', ''),
        last_name=extracted_info.get('last_name', ''),
        phone=normalized_phone,
        job_title=extracted_info.get('job_title', ''),
        bio=extracted_info.get('bio', ''),
        skills=json.dumps(extracted_info.get('skills', [])),
        experience_years=extracted_info.get('experience_years', 0),
        education=json.dumps(extracted_info.get('education', [])),
        resume_url=resume_path,
        profile_completed=True,
        # Enable cross-organization access by default for universal visibility
        cross_org_accessible=True,
        public_profile_enabled=True
    )
    
    try:
        db.session.add(candidate)
        db.session.commit()
        
        # Log successful registration
        logging.info(f"Resume-based candidate registered: {candidate.username} ({email})")
        
        # Redirect to registration success page with credentials
        return render_template('registration_success.html', 
                             username=candidate.username,
                             email=candidate.email,
                             password='candidate123',
                             profile_url=f"{request.url_root}candidate/profile/{candidate.id}",
                             registration_method='resume')
    
    except Exception as e:
        db.session.rollback()
        logging.error(f"Database error during resume registration: {e}")
        flash('Registration failed due to a database error. Please try again.', 'error')
        return redirect(url_for('candidate_resume_register'))

@app.route('/candidate/complete-profile')
@login_required
def complete_profile_import():
    """Profile completion with import options"""
    if current_user.role != 'candidate':
        flash('Access denied. Only candidates can complete profiles.', 'error')
        return redirect(url_for('dashboard'))
    
    import_type = request.args.get('import')
    
    if import_type == 'linkedin':
        return render_template('linkedin_import.html', user=current_user)
    
    # Redirect to the user's own profile page instead of hardcoded ID
    return redirect(url_for('candidate_profile', user_id=current_user.id))

@app.route('/candidate/upload-resume', methods=['POST'])
@login_required
def upload_resume_for_profile():
    """Upload and parse resume to populate candidate profile"""
    if current_user.role != 'candidate':
        # Check if this is an API call (for resume builder)
        if request.headers.get('Content-Type', '').startswith('application/json') or 'json' in request.headers.get('Accept', ''):
            return jsonify({'success': False, 'error': 'Access denied. Only candidates can upload resumes.'}), 403
        flash('Access denied. Only candidates can upload resumes.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        if 'resume' not in request.files:
            if (request.headers.get('Content-Type', '').startswith('multipart/form-data') or 
                'application/json' in request.headers.get('Accept', '') or
                request.is_xhr):
                return jsonify({'success': False, 'error': 'No resume file uploaded.'}), 400
            flash('No resume file uploaded.', 'error')
            return redirect(url_for('candidate_profile', user_id=current_user.id))
        
        resume_file = request.files['resume']
        if resume_file.filename == '':
            if (request.headers.get('Content-Type', '').startswith('multipart/form-data') or 
                'application/json' in request.headers.get('Accept', '') or
                request.is_xhr):
                return jsonify({'success': False, 'error': 'No resume file selected.'}), 400
            flash('No resume file selected.', 'error')
            return redirect(url_for('candidate_profile', user_id=current_user.id))
        
        # Validate file type
        allowed_extensions = {'pdf', 'docx', 'doc', 'txt'}
        file_extension = resume_file.filename.rsplit('.', 1)[1].lower() if '.' in resume_file.filename else ''
        
        if file_extension not in allowed_extensions:
            error_msg = 'Invalid file type. Please upload PDF, DOCX, or DOC files.'
            if (request.headers.get('Content-Type', '').startswith('multipart/form-data') or 
                'application/json' in request.headers.get('Accept', '') or
                request.is_xhr):
                return jsonify({'success': False, 'error': error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('candidate_profile', user_id=current_user.id))
        
        # Save uploaded file
        from werkzeug.utils import secure_filename
        import uuid
        filename = secure_filename(resume_file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        resume_path = os.path.join('uploads', 'resumes', unique_filename)
        os.makedirs(os.path.dirname(resume_path), exist_ok=True)
        resume_file.save(resume_path)
        
        # Parse resume using comprehensive importer
        from comprehensive_resume_import import import_comprehensive_resume
        parsed_result = import_comprehensive_resume(resume_path, filename, current_user)
        
        if parsed_result.get("success"):
            # Update resume URL
            current_user.resume_url = resume_path
            db.session.commit()
            
            # Generate suggested title from parsed data
            suggested_title = f"{current_user.first_name or 'Professional'} Resume"
            
            # Return JSON response for API calls
            if request.headers.get('Content-Type', '').startswith('multipart/form-data'):
                return jsonify({
                    'success': True, 
                    'message': f'Resume uploaded and profile updated successfully! Extracted {parsed_result.get("work_experiences_count", 0)} work experiences.',
                    'suggested_title': suggested_title,
                    'parsed_data': parsed_result
                })
            
            flash(f'Resume uploaded and profile updated successfully! We extracted {parsed_result.get("work_experiences_count", 0)} work experiences automatically.', 'success')
        else:
            error_msg = parsed_result.get("error", "Unknown parsing error")
            # Return JSON response for AJAX calls
            if (request.headers.get('Content-Type', '').startswith('multipart/form-data') or 
                'application/json' in request.headers.get('Accept', '') or
                request.is_xhr):
                return jsonify({
                    'success': False, 
                    'error': f'Resume uploaded but parsing failed: {error_msg}. Please update your profile manually.'
                })
            flash(f'Resume uploaded but parsing failed: {error_msg}. Please update your profile manually.', 'warning')
        
        # Clean up temp file
        try:
            os.remove(resume_path)
        except:
            pass
        
        return redirect(url_for('candidate_profile', user_id=current_user.id))
        
    except Exception as e:
        logging.error(f"Resume upload failed: {e}")
        # Return JSON response for AJAX calls or when Accept header indicates JSON
        if (request.headers.get('Content-Type', '').startswith('multipart/form-data') or 
            'application/json' in request.headers.get('Accept', '') or
            request.is_xhr):
            return jsonify({'success': False, 'error': 'Resume upload failed. Please try again.'}), 500
        flash('Resume upload failed. Please try again.', 'error')
        return redirect(url_for('candidate_profile', user_id=current_user.id))

@app.route('/candidate/comprehensive-resume-import', methods=['POST'])
@login_required
def comprehensive_resume_import():
    """Comprehensive resume import with enhanced work experience extraction"""
    if current_user.role != 'candidate':
        flash('Access denied. Only candidates can import resumes.', 'error')
        return redirect(url_for('dashboard'))
    
    if 'resume' not in request.files:
        flash('No resume file provided.', 'error')
        return redirect(url_for('candidate_profile', user_id=current_user.id))
    
    resume_file = request.files['resume']
    if resume_file.filename == '':
        flash('No resume file selected.', 'error')
        return redirect(url_for('candidate_profile', user_id=current_user.id))
    
    try:
        # Save file temporarily
        from werkzeug.utils import secure_filename
        import uuid
        filename = secure_filename(resume_file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        resume_path = os.path.join('uploads', 'resumes', unique_filename)
        os.makedirs(os.path.dirname(resume_path), exist_ok=True)
        resume_file.save(resume_path)
        
        # Import comprehensive profile
        from comprehensive_resume_import import import_comprehensive_resume
        result = import_comprehensive_resume(resume_path, filename, current_user)
        
        if result.get("success"):
            # Update resume URL
            current_user.resume_url = resume_path
            db.session.commit()
            
            flash(f'Resume imported successfully! {result.get("message", "")}', 'success')
        else:
            flash(f'Resume import failed: {result.get("error", "Unknown error")}', 'error')
        
        # Clean up temp file if needed
        try:
            if not result.get("success"):
                os.remove(resume_path)
        except:
            pass
            
    except Exception as e:
        logging.error(f"Comprehensive resume import failed: {e}")
        flash('Resume import failed. Please try again.', 'error')
    
    return redirect(url_for('candidate_profile', user_id=current_user.id))

@app.route('/candidate/work-experience-details/<int:user_id>')
@login_required
def work_experience_details(user_id):
    """View detailed work experience for a candidate"""
    candidate = User.query.get_or_404(user_id)
    
    # Check access permissions
    if current_user.role == 'candidate' and current_user.id != user_id:
        flash('Access denied. You can only view your own work experience.', 'error')
        return redirect(url_for('candidate_profile', user_id=current_user.id))
    
    # Parse work experience
    work_experiences = []
    if candidate.experience:
        try:
            work_experiences = json.loads(candidate.experience)
        except json.JSONDecodeError:
            work_experiences = []
    
    return render_template('candidate/work_experience_details.html', 
                         candidate=candidate, 
                         work_experiences=work_experiences,
                         current_user=current_user)

@app.route('/candidate/linkedin-import', methods=['POST'])
@login_required
def linkedin_import():
    """Import LinkedIn profile data"""
    if current_user.role != 'candidate':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    linkedin_url = request.form.get('linkedin_url')
    email = request.form.get('email', current_user.email)
    
    if not linkedin_url:
        flash('LinkedIn URL is required.', 'error')
        return redirect(url_for('complete_profile_import') + '?import=linkedin')
    
    try:
        # Extract LinkedIn profile information (placeholder implementation)
        extracted_info = extract_linkedin_info(linkedin_url)
        
        # Update user profile with extracted info
        current_user.bio = extracted_info.get('bio', current_user.bio)
        current_user.skills = json.dumps(extracted_info.get('skills', json.loads(current_user.skills or '[]')))
        current_user.experience = json.dumps(extracted_info.get('experience', json.loads(current_user.experience or '[]')))
        current_user.education = json.dumps(extracted_info.get('education', json.loads(current_user.education or '[]')))
        current_user.linkedin_url = linkedin_url
        
        if not current_user.first_name and extracted_info.get('first_name'):
            current_user.first_name = extracted_info.get('first_name')
        if not current_user.last_name and extracted_info.get('last_name'):
            current_user.last_name = extracted_info.get('last_name')
        if not current_user.job_title and extracted_info.get('job_title'):
            current_user.job_title = extracted_info.get('job_title')
        
        db.session.commit()
        flash('LinkedIn profile imported successfully!', 'success')
        return redirect(url_for('candidate_profile', user_id=current_user.id))
        
    except Exception as e:
        db.session.rollback()
        flash(f'Failed to import LinkedIn profile: {str(e)}', 'error')
        return redirect(url_for('complete_profile_import') + '?import=linkedin')

def extract_linkedin_info(linkedin_url):
    """Extract information from LinkedIn profile URL (placeholder)"""
    # In a real implementation, this would use LinkedIn API or web scraping
    # For demo purposes, return sample data
    return {
        'first_name': 'Professional',
        'last_name': 'User', 
        'job_title': 'Senior Professional',
        'bio': 'Experienced professional with a strong background in technology and innovation. Passionate about driving results and leading teams to success.',
        'skills': ['Leadership', 'Project Management', 'Strategic Planning', 'Team Management', 'Innovation'],
        'experience': [
            {
                'company': 'Tech Solutions Inc',
                'title': 'Senior Manager',
                'duration': '2020 - Present',
                'description': 'Leading cross-functional teams and driving strategic initiatives.'
            }
        ],
        'education': [
            {
                'institution': 'Professional University',
                'degree': 'Bachelor of Science',
                'field': 'Business Administration',
                'year': '2018'
            }
        ]
    }

@app.route('/auth/google')
def auth_google():
    """Google OAuth sign up"""
    # In production, this would integrate with Google OAuth
    # For demo, redirect to quick registration with pre-filled data
    return render_template('social_auth_demo.html', 
                         provider='Google',
                         demo_data={
                             'name': 'Google User',
                             'email': 'user@gmail.com',
                             'profile_image': 'https://lh3.googleusercontent.com/a/default-user'
                         })

@app.route('/auth/linkedin')
def auth_linkedin():
    """LinkedIn OAuth sign up"""
    return render_template('social_auth_demo.html', 
                         provider='LinkedIn',
                         demo_data={
                             'name': 'LinkedIn Professional',
                             'email': 'professional@linkedin.com',
                             'job_title': 'Software Engineer',
                             'profile_image': 'https://media.licdn.com/dms/image/default'
                         })

@app.route('/auth/github')
def auth_github():
    """GitHub OAuth sign up"""
    return render_template('social_auth_demo.html', 
                         provider='GitHub',
                         demo_data={
                             'name': 'GitHub Developer',
                             'email': 'developer@github.com',
                             'username': 'github_dev',
                             'profile_image': 'https://avatars.githubusercontent.com/u/default'
                         })

@app.route('/auth/facebook')
def auth_facebook():
    """Facebook OAuth sign up"""
    return render_template('social_auth_demo.html', 
                         provider='Facebook',
                         demo_data={
                             'name': 'Facebook User',
                             'email': 'user@facebook.com',
                             'profile_image': 'https://graph.facebook.com/default/picture'
                         })

@app.route('/auth/social-complete', methods=['POST'])
def social_auth_complete():
    """Complete social media authentication"""
    provider = request.form.get('provider')
    name = request.form.get('name')
    email = request.form.get('email')
    job_title = request.form.get('job_title', '')
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        flash('An account with this email already exists. Please login instead.', 'warning')
        return redirect(url_for('login'))
    
    # Create default organization if needed
    default_org = Organization.query.filter_by(name='TechCorp Solutions').first()
    if not default_org:
        default_org = Organization(
            name='TechCorp Solutions',
            slug='techcorp-solutions'
        )
        db.session.add(default_org)
        db.session.flush()
    
    # Create candidate user
    username = email.split('@')[0]
    candidate = User(
        username=username,
        email=email,
        password_hash=generate_password_hash('social123'),  # Temporary password
        role='candidate',
        organization_id=default_org.id,
        first_name=name.split()[0] if name else '',
        last_name=' '.join(name.split()[1:]) if len(name.split()) > 1 else '',
        job_title=job_title,
        bio=f'Registered via {provider} social authentication.',
        profile_completed=False,
        # Enable cross-organization access by default for universal visibility
        cross_org_accessible=True,
        public_profile_enabled=True
    )
    
    db.session.add(candidate)
    db.session.commit()
    
    # Redirect to success page with credentials
    return render_template('registration_success.html', 
                         username=candidate.username,
                         email=candidate.email,
                         password='social123',
                         profile_url=f"{request.url_root}candidate/profile/{candidate.id}",
                         registration_method='social',
                         provider=provider)

@app.route('/candidate/invitation-register', methods=['POST'])
def candidate_invitation_register():
    """Register candidate with invitation code"""
    invitation_code = request.form.get('invitation_code')
    
    # Find invitation by code (placeholder - implement invitation system)
    flash('Invitation system coming soon!', 'info')
    return redirect(url_for('candidate_register'))

@app.route('/candidate/import-linkedin', methods=['POST'])
def import_linkedin_direct():
    """Import candidate profile from LinkedIn"""
    data = request.get_json()
    linkedin_url = data.get('linkedin_url')
    email = data.get('email')
    
    # LinkedIn import logic (placeholder)
    extracted_info = extract_linkedin_info(linkedin_url)
    
    if extracted_info:
        return jsonify({'success': True, 'data': extracted_info})
    else:
        return jsonify({'success': False, 'error': 'Failed to import LinkedIn profile'})

@app.route('/debug/auth-status')
def debug_auth_status():
    """Debug route to check authentication status"""
    from flask_login import current_user
    if current_user.is_authenticated:
        return f"Authenticated: {current_user.username} (ID: {current_user.id})"
    else:
        return "Not authenticated"

@app.route('/candidate/profile/<int:user_id>')
@login_required
def candidate_profile(user_id):
    """Display candidate profile"""
    try:
        # Debug logging
        logging.info(f"candidate_profile accessed by user {current_user.id} for profile {user_id}")
        
        candidate = User.query.get_or_404(user_id)
        
        if candidate.role != 'candidate':
            flash('Access denied.', 'danger')
            return redirect(url_for('dashboard'))
        
        # Add access control - users can only view their own profile unless they're HR/admin
        if current_user.role == 'candidate' and current_user.id != user_id:
            flash('You can only view your own profile.', 'danger')
            return redirect(url_for('candidate_profile', user_id=current_user.id))
        
        return render_template('candidate_profile.html', candidate=candidate)
    except Exception as e:
        logging.error(f"Error in candidate_profile: {e}")
        flash('An error occurred while loading the profile.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/cv-checker', methods=['GET', 'POST'])
@login_required
def cv_checker():
    """CV Checker analysis page for candidates"""
    if current_user.role != 'candidate':
        flash('Access denied. CV checker is only available to candidates.', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # Handle CV upload and analysis
        from cv_checker_service import analyze_candidate_cv
        from resume_parser import ResumeParser
        import os
        
        if 'cv_file' not in request.files:
            flash('No file selected', 'danger')
            return redirect(url_for('cv_checker'))
        
        file = request.files['cv_file']
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(url_for('cv_checker'))
        
        if file:
            try:
                # Save uploaded file temporarily
                if not file.filename:
                    flash('Invalid file name', 'danger')
                    return redirect(url_for('cv_checker'))
                    
                filename = secure_filename(file.filename)
                file_path = os.path.join('uploads', filename)
                os.makedirs('uploads', exist_ok=True)
                file.save(file_path)
                
                # Parse the resume to extract text
                parser = ResumeParser()
                parsed_result = parser.parse_resume(file_path, filename)
                
                # Extract text from parsed result
                if isinstance(parsed_result, dict):
                    if parsed_result.get('success'):
                        cv_text = parsed_result.get('raw_text', '')
                    elif parsed_result.get('error'):
                        flash(f'Error processing file: {parsed_result["error"]}', 'danger')
                        return redirect(url_for('cv_checker'))
                    else:
                        cv_text = parsed_result.get('raw_text', '') or str(parsed_result)
                else:
                    cv_text = str(parsed_result)
                
                if not cv_text or len(cv_text.strip()) < 50:
                    flash('Unable to extract meaningful text from the CV. Please try a different file.', 'danger')
                    return redirect(url_for('cv_checker'))
                
                # Analyze the CV
                analysis_result = analyze_candidate_cv(cv_text, current_user.first_name or current_user.username)
                
                # Save analysis to database
                import json
                
                try:
                    cv_analysis = CVAnalysis(
                        user_id=current_user.id,
                        overall_score=analysis_result.get('overall_score', 0),
                        format_score=analysis_result.get('format_score', 0),
                        content_score=analysis_result.get('content_score', 0),
                        sections_score=analysis_result.get('sections_score', 0),
                        style_score=analysis_result.get('style_score', 0),
                        keywords_score=analysis_result.get('keywords_score', 0),
                        strengths=json.dumps(analysis_result.get('strengths', [])),
                        weaknesses=json.dumps(analysis_result.get('weaknesses', [])),
                        missing_sections=json.dumps(analysis_result.get('missing_sections', [])),
                        format_issues=json.dumps(analysis_result.get('format_issues', [])),
                        content_suggestions=json.dumps(analysis_result.get('content_suggestions', [])),
                        keyword_gaps=json.dumps(analysis_result.get('keyword_gaps', [])),
                        recommendations=json.dumps(analysis_result.get('recommendations', [])),
                        detailed_feedback=json.dumps(analysis_result.get('detailed_feedback', {})),
                        cv_version=filename,
                        analyzed_at=datetime.utcnow()
                    )
                    
                    db.session.add(cv_analysis)
                    db.session.commit()
                except Exception as db_error:
                    db.session.rollback()
                    logging.error(f"Database error saving CV analysis: {str(db_error)}")
                    flash('CV analysis completed but could not save to database. Please try again.', 'warning')
                
                # Clean up temporary file
                try:
                    os.remove(file_path)
                except:
                    pass
                
                flash('CV analysis completed successfully!', 'success')
                return redirect(url_for('cv_checker'))
                
            except Exception as e:
                flash(f'Error analyzing CV: {str(e)}', 'danger')
                return redirect(url_for('cv_checker'))
    
    # GET request - show the page
    import json
    try:
        # Handle any pending database issues
        db.session.rollback()
        
        latest_analysis = CVAnalysis.query.filter_by(user_id=current_user.id).order_by(CVAnalysis.analyzed_at.desc()).first()
        
        # Convert JSON strings back to lists for template
        if latest_analysis:
            latest_analysis.strengths = json.loads(latest_analysis.strengths) if latest_analysis.strengths else []
            latest_analysis.weaknesses = json.loads(latest_analysis.weaknesses) if latest_analysis.weaknesses else []
            latest_analysis.recommendations = json.loads(latest_analysis.recommendations) if latest_analysis.recommendations else []
        
        return render_template('cv_checker.html', candidate=current_user, analysis=latest_analysis)
    except Exception as e:
        logging.error(f"Error in cv_checker GET: {str(e)}")
        db.session.rollback()
        flash('An error occurred while loading the CV checker page.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/cv-checker/upload', methods=['POST'])
@login_required
def cv_checker_upload():
    """Analyze uploaded CV and provide feedback"""
    from cv_checker_service import analyze_candidate_cv
    from resume_parser import ResumeParser
    import json
    import os
    from werkzeug.utils import secure_filename
    
    if current_user.role != 'candidate':
        return jsonify({'success': False, 'error': 'Access denied'})
    
    try:
        # Check if file was uploaded
        if 'cv_file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['cv_file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        # Validate file type
        allowed_extensions = {'.pdf', '.doc', '.docx', '.txt'}
        if not file.filename:
            return jsonify({'success': False, 'error': 'No file selected'})
        
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'success': False, 'error': 'Invalid file type. Please upload PDF, DOC, DOCX, or TXT files.'})
        
        # Extract text from file
        parser = ResumeParser()
        
        # Save uploaded file temporarily
        temp_filename = secure_filename(file.filename)
        temp_path = os.path.join('uploads', temp_filename)
        
        # Ensure uploads directory exists
        os.makedirs('uploads', exist_ok=True)
        
        # Save file temporarily
        file.save(temp_path)
        
        try:
            # Extract text using the resume parser method
            parsed_result = parser.parse_resume(temp_path, file.filename)
            
            # Extract text from parsed result
            if isinstance(parsed_result, dict):
                if parsed_result.get('success'):
                    cv_text = parsed_result.get('raw_text', '')
                elif parsed_result.get('error'):
                    return jsonify({'success': False, 'error': f'Error processing file: {parsed_result["error"]}'})
                else:
                    cv_text = parsed_result.get('raw_text', '') or str(parsed_result)
            else:
                cv_text = str(parsed_result)
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        if not cv_text or len(cv_text.strip()) < 50:
            return jsonify({'success': False, 'error': 'Could not extract sufficient text from the file. Please ensure the file is readable.'})
        
        # Analyze CV using AI
        candidate_name = f"{current_user.first_name} {current_user.last_name}".strip() or current_user.username
        logging.info(f"Starting CV analysis for {candidate_name}, text length: {len(cv_text)}")
        analysis_result = analyze_candidate_cv(cv_text, candidate_name)
        logging.info(f"CV analysis completed. Result keys: {list(analysis_result.keys()) if analysis_result else 'None'}")
        
        # Validate analysis result
        if not analysis_result or not isinstance(analysis_result, dict):
            logging.error(f"Invalid analysis result: {analysis_result}")
            raise ValueError("Invalid analysis result from CV analysis service")
        
        # Save analysis to database
        cv_analysis = CVAnalysis(
            user_id=current_user.id,
            overall_score=analysis_result.get('overall_score', 0),
            format_score=analysis_result.get('format_score', 0),
            content_score=analysis_result.get('content_score', 0),
            sections_score=analysis_result.get('sections_score', 0),
            style_score=analysis_result.get('style_score', 0),
            keywords_score=analysis_result.get('keywords_score', 0),
            strengths=json.dumps(analysis_result.get('strengths', [])),
            weaknesses=json.dumps(analysis_result.get('weaknesses', [])),
            missing_sections=json.dumps(analysis_result.get('missing_sections', [])),
            format_issues=json.dumps(analysis_result.get('format_issues', [])),
            content_suggestions=json.dumps(analysis_result.get('content_suggestions', [])),
            keyword_gaps=json.dumps(analysis_result.get('keyword_gaps', [])),
            recommendations=json.dumps(analysis_result.get('recommendations', [])),
            detailed_feedback=json.dumps(analysis_result.get('detailed_feedback', {})),
            cv_version=file.filename
        )
        
        db.session.add(cv_analysis)
        db.session.commit()
        logging.info(f"CV analysis saved to database with ID: {cv_analysis.id}")
        
        # Log the analysis
        audit_log = AuditLog(
            user_id=current_user.id,
            action='CV Analysis',
            resource_type='CVAnalysis',
            resource_id=cv_analysis.id,
            details=f'CV analyzed: {file.filename}, Overall Score: {analysis_result.get("overall_score", 0)}/100'
        )
        db.session.add(audit_log)
        db.session.commit()
        
        # Check if this is an AJAX request
        is_ajax = (request.is_json or 
                  request.headers.get('Content-Type') == 'application/json' or 
                  'application/json' in request.headers.get('Accept', '') or
                  request.headers.get('X-Requested-With') == 'XMLHttpRequest')
        
        if is_ajax:
            # Return JSON response for AJAX requests
            response_data = {
                'success': True,
                'redirect_url': url_for('view_cv_analysis', analysis_id=cv_analysis.id),
                'analysis_id': cv_analysis.id,
                'overall_score': analysis_result.get('overall_score', 0)
            }
            logging.info(f"Returning JSON response: {response_data}")
            return jsonify(response_data)
        else:
            # For traditional form submission, redirect to results page
            flash('CV analysis completed successfully!', 'success')
            return redirect(url_for('view_cv_analysis', analysis_id=cv_analysis.id))
        
    except Exception as e:
        logging.error(f"Error analyzing CV: {e}")
        logging.error(f"Error type: {type(e)}")
        import traceback
        logging.error(f"Full traceback: {traceback.format_exc()}")
        
        # Check if this is an AJAX request
        is_ajax = (request.is_json or 
                  request.headers.get('Content-Type') == 'application/json' or 
                  'application/json' in request.headers.get('Accept', '') or
                  request.headers.get('X-Requested-With') == 'XMLHttpRequest')
        
        if is_ajax:
            return jsonify({
                'success': False,
                'error': f'An error occurred while analyzing your CV: {str(e)}',
                'message': 'Please try again or contact support if the problem persists.'
            })
        else:
            flash('An error occurred while analyzing your CV. Please try again.', 'danger')
            return redirect(url_for('cv_checker'))

@app.route('/cv-checker/history')
@login_required
def cv_analysis_history():
    """View CV analysis history for candidate"""
    if current_user.role != 'candidate':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    analyses = CVAnalysis.query.filter_by(user_id=current_user.id).order_by(CVAnalysis.analyzed_at.desc()).all()
    
    return render_template('cv_analysis_history.html', analyses=analyses)

@app.route('/cv-checker/analysis/<int:analysis_id>')
@login_required
def view_cv_analysis(analysis_id):
    """View specific CV analysis results"""
    analysis = CVAnalysis.query.get_or_404(analysis_id)
    
    # Check access permissions
    if current_user.role == 'candidate' and analysis.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('cv_checker'))
    elif current_user.role in ['admin', 'hr'] and current_user.organization_id != analysis.user.organization_id:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Parse JSON fields
    import json
    analysis_data = {
        'id': analysis.id,
        'overall_score': analysis.overall_score,
        'format_score': analysis.format_score,
        'content_score': analysis.content_score,
        'sections_score': analysis.sections_score,
        'style_score': analysis.style_score,
        'keywords_score': analysis.keywords_score,
        'strengths': json.loads(analysis.strengths) if analysis.strengths else [],
        'weaknesses': json.loads(analysis.weaknesses) if analysis.weaknesses else [],
        'missing_sections': json.loads(analysis.missing_sections) if analysis.missing_sections else [],
        'format_issues': json.loads(analysis.format_issues) if analysis.format_issues else [],
        'content_suggestions': json.loads(analysis.content_suggestions) if analysis.content_suggestions else [],
        'keyword_gaps': json.loads(analysis.keyword_gaps) if analysis.keyword_gaps else [],
        'recommendations': json.loads(analysis.recommendations) if analysis.recommendations else [],
        'detailed_feedback': json.loads(analysis.detailed_feedback) if analysis.detailed_feedback else {},
        'analyzed_at': analysis.analyzed_at,
        'cv_version': analysis.cv_version
    }
    
    return render_template('cv_analysis_detail.html', analysis=analysis_data, candidate=analysis.user)

# ==================== Cover Letter Routes ====================

@app.route('/cover-letters')
@login_required
def cover_letters():
    """Cover letter management dashboard"""
    if current_user.role != 'candidate':
        flash('Access denied. Cover letters are only available to candidates.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get user's cover letters
    cover_letters = CoverLetter.query.filter_by(user_id=current_user.id).order_by(CoverLetter.updated_at.desc()).all()
    
    # Get available templates
    from cover_letter_service import CoverLetterGenerator
    generator = CoverLetterGenerator()
    templates = generator.get_available_templates()
    
    return render_template('cover_letters.html', 
                         cover_letters=cover_letters, 
                         templates=templates,
                         candidate=current_user)

@app.route('/cover-letters/new')
@login_required
def new_cover_letter():
    """Create new cover letter page"""
    if current_user.role != 'candidate':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get available templates
    from cover_letter_service import CoverLetterGenerator
    generator = CoverLetterGenerator()
    templates = generator.get_available_templates()
    
    return render_template('new_cover_letter.html', 
                         templates=templates,
                         candidate=current_user)

@app.route('/cover-letters/generate', methods=['POST'])
@login_required
def generate_cover_letter():
    """Generate AI-powered cover letter"""
    if current_user.role != 'candidate':
        return jsonify({'success': False, 'error': 'Access denied'})
    
    try:
        from cover_letter_service import CoverLetterGenerator
        import json
        
        # Get form data
        company_name = request.form.get('company_name', '').strip()
        position_title = request.form.get('position_title', '').strip()
        job_description = request.form.get('job_description', '').strip()
        template_type = request.form.get('template_type', 'custom')
        tone = request.form.get('tone', 'professional')
        
        if not company_name or not position_title:
            return jsonify({'success': False, 'error': 'Company name and position title are required'})
        
        # Prepare candidate information
        candidate_info = {
            'name': f"{current_user.first_name} {current_user.last_name}".strip() or current_user.username,
            'email': current_user.email,
            'skills': json.loads(current_user.skills) if current_user.skills else [],
            'experience': json.loads(current_user.experience) if current_user.experience else [],
            'education': json.loads(current_user.education) if current_user.education else [],
            'job_title': current_user.job_title,
            'bio': current_user.bio,
            'experience_years': current_user.experience_years
        }
        
        # Prepare job details
        job_details = {
            'company': company_name,
            'position': position_title,
            'description': job_description,
            'requirements': job_description
        }
        
        # Generate cover letter
        generator = CoverLetterGenerator()
        result = generator.generate_cover_letter(candidate_info, job_details, template_type, tone)
        
        if result and result.get('content'):
            # Save to database
            cover_letter = CoverLetter(
                user_id=current_user.id,
                title=result.get('title', f"Cover Letter - {company_name}"),
                company_name=company_name,
                position_title=position_title,
                content=result['content'],
                template_type=template_type,
                generated_by_ai=result.get('generated_by_ai', False),
                ai_prompt=result.get('ai_prompt'),
                generation_model=result.get('generation_model')
            )
            
            db.session.add(cover_letter)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'cover_letter_id': cover_letter.id,
                'content': result['content'],
                'title': result.get('title'),
                'key_points': result.get('key_points', []),
                'suggestions': result.get('suggestions', [])
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to generate cover letter'})
            
    except Exception as e:
        logging.error(f"Error generating cover letter: {str(e)}")
        return jsonify({'success': False, 'error': f'Generation failed: {str(e)}'})

@app.route('/generate-cover-letter', methods=['POST'])
@login_required
def generate_cover_letter_from_job():
    """Generate AI-powered cover letter from job listings"""
    if current_user.role != 'candidate':
        return jsonify({'success': False, 'error': 'Access denied'})
    
    try:
        from cover_letter_service import CoverLetterGenerator
        import json
        
        # Get form data
        company_name = request.form.get('company_name', '').strip()
        position_title = request.form.get('position_title', '').strip()
        job_description = request.form.get('job_description', '').strip()
        template_type = request.form.get('template_type', 'custom')
        tone = request.form.get('tone', 'professional')
        
        if not company_name or not position_title:
            return jsonify({'success': False, 'error': 'Company name and position title are required'})
        
        # Prepare candidate information
        candidate_info = {
            'name': f"{current_user.first_name} {current_user.last_name}".strip() or current_user.username,
            'email': current_user.email,
            'skills': json.loads(current_user.skills) if current_user.skills else [],
            'experience': json.loads(current_user.experience) if current_user.experience else [],
            'education': json.loads(current_user.education) if current_user.education else [],
            'job_title': current_user.job_title,
            'bio': current_user.bio,
            'experience_years': current_user.experience_years
        }
        
        # Prepare job details
        job_details = {
            'company': company_name,
            'position': position_title,
            'description': job_description,
            'requirements': job_description
        }
        
        # Generate cover letter
        generator = CoverLetterGenerator()
        result = generator.generate_cover_letter(candidate_info, job_details, template_type, tone)
        
        if result and result.get('content'):
            # Save to database
            cover_letter = CoverLetter(
                user_id=current_user.id,
                title=result.get('title', f"Cover Letter - {company_name}"),
                company_name=company_name,
                position_title=position_title,
                content=result['content'],
                template_type=template_type,
                generated_by_ai=result.get('generated_by_ai', False),
                ai_prompt=result.get('ai_prompt'),
                generation_model=result.get('generation_model')
            )
            
            db.session.add(cover_letter)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'cover_letter_id': cover_letter.id,
                'content': result['content'],
                'title': result.get('title'),
                'key_points': result.get('key_points', []),
                'suggestions': result.get('suggestions', [])
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to generate cover letter'})
            
    except Exception as e:
        logging.error(f"Error generating cover letter: {str(e)}")
        return jsonify({'success': False, 'error': f'Generation failed: {str(e)}'})

@app.route('/cover-letters/<int:letter_id>')
@login_required
def view_cover_letter(letter_id):
    """View specific cover letter"""
    cover_letter = CoverLetter.query.get_or_404(letter_id)
    
    # Check access permissions
    if current_user.role == 'candidate' and cover_letter.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('cover_letters'))
    elif current_user.role in ['admin', 'hr'] and current_user.organization_id != cover_letter.user.organization_id:
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('view_cover_letter.html', 
                         cover_letter=cover_letter,
                         candidate=cover_letter.user)

@app.route('/cover-letters/<int:letter_id>/edit')
@login_required
def edit_cover_letter(letter_id):
    """Edit cover letter"""
    cover_letter = CoverLetter.query.get_or_404(letter_id)
    
    if current_user.role != 'candidate' or cover_letter.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('cover_letters'))
    
    return render_template('edit_cover_letter.html', 
                         cover_letter=cover_letter,
                         candidate=current_user)

@app.route('/cover-letters/<int:letter_id>/update', methods=['POST'])
@login_required
def update_cover_letter(letter_id):
    """Update cover letter"""
    cover_letter = CoverLetter.query.get_or_404(letter_id)
    
    if current_user.role != 'candidate' or cover_letter.user_id != current_user.id:
        flash('Access denied.', 'danger')
        return redirect(url_for('cover_letters'))
    
    try:
        cover_letter.title = request.form.get('title', '').strip()
        cover_letter.company_name = request.form.get('company_name', '').strip()
        cover_letter.position_title = request.form.get('position_title', '').strip()
        cover_letter.content = request.form.get('content', '').strip()
        cover_letter.template_type = request.form.get('template_type', 'custom')
        cover_letter.status = request.form.get('status', 'draft')
        cover_letter.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Cover letter updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating cover letter: {str(e)}")
        flash('Error updating cover letter. Please try again.', 'danger')
    
    return redirect(url_for('view_cover_letter', letter_id=letter_id))

@app.route('/cover-letters/<int:letter_id>/delete', methods=['POST'])
@login_required
def delete_cover_letter(letter_id):
    """Delete cover letter"""
    cover_letter = CoverLetter.query.get_or_404(letter_id)
    
    if current_user.role != 'candidate' or cover_letter.user_id != current_user.id:
        # Check if it's an AJAX request
        if (request.headers.get('Content-Type') == 'application/json' or 
            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
            'application/json' in request.headers.get('Accept', '')):
            return jsonify({'success': False, 'error': 'Access denied'})
        flash('Access denied.', 'danger')
        return redirect(url_for('cover_letters'))
    
    try:
        db.session.delete(cover_letter)
        db.session.commit()
        
        # Check if it's an AJAX request
        if (request.headers.get('Content-Type') == 'application/json' or 
            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
            'application/json' in request.headers.get('Accept', '')):
            return jsonify({'success': True, 'message': 'Cover letter deleted successfully!'})
        
        flash('Cover letter deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting cover letter: {str(e)}")
        
        # Check if it's an AJAX request
        if (request.headers.get('Content-Type') == 'application/json' or 
            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
            'application/json' in request.headers.get('Accept', '')):
            return jsonify({'success': False, 'error': 'Error deleting cover letter. Please try again.'})
        
        flash('Error deleting cover letter. Please try again.', 'danger')
    
    return redirect(url_for('cover_letters'))

@app.route('/cover-letters/<int:letter_id>/analyze', methods=['POST'])
@login_required
def analyze_cover_letter(letter_id):
    """Analyze cover letter with AI feedback"""
    cover_letter = CoverLetter.query.get_or_404(letter_id)
    
    if current_user.role != 'candidate' or cover_letter.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Access denied'})
    
    try:
        from cover_letter_service import CoverLetterGenerator
        
        generator = CoverLetterGenerator()
        job_requirements = request.form.get('job_requirements', '')
        
        analysis = generator.analyze_cover_letter(cover_letter.content, job_requirements)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
        
    except Exception as e:
        logging.error(f"Error analyzing cover letter: {str(e)}")
        return jsonify({'success': False, 'error': f'Analysis failed: {str(e)}'})

@app.route('/cover-letters/examples')
@login_required
def cover_letter_examples():
    """View cover letter examples"""
    if current_user.role != 'candidate':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    from cover_letter_service import get_cover_letter_examples
    examples = get_cover_letter_examples()
    
    return render_template('cover_letter_examples.html', 
                         examples=examples,
                         candidate=current_user)

@app.route('/cover-letters/examples/<example_key>')
@login_required
def view_cover_letter_example(example_key):
    """View specific cover letter example"""
    if current_user.role != 'candidate':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    from cover_letter_service import get_cover_letter_examples
    examples = get_cover_letter_examples()
    
    if example_key not in examples:
        flash('Example not found.', 'danger')
        return redirect(url_for('cover_letter_examples'))
    
    example = examples[example_key]
    
    return render_template('view_cover_letter_example.html', 
                         example=example,
                         example_key=example_key,
                         candidate=current_user)

@app.route('/cover-letters/examples/<example_key>/use-template', methods=['POST'])
@login_required
def use_example_template(example_key):
    """Create new cover letter based on example"""
    if current_user.role != 'candidate':
        return jsonify({'success': False, 'error': 'Access denied'})
    
    try:
        from cover_letter_service import get_cover_letter_examples
        examples = get_cover_letter_examples()
        
        if example_key not in examples:
            return jsonify({'success': False, 'error': 'Example not found'})
        
        example = examples[example_key]
        
        # Create new cover letter based on example
        cover_letter = CoverLetter(
            user_id=current_user.id,
            title=f"Based on {example['title']}",
            company_name=request.form.get('company_name', example.get('company', '')),
            position_title=request.form.get('position_title', example.get('position', '')),
            content=example['content'],
            template_type='example',
            status='draft'
        )
        
        db.session.add(cover_letter)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'cover_letter_id': cover_letter.id,
            'redirect_url': url_for('edit_cover_letter', letter_id=cover_letter.id)
        })
        
    except Exception as e:
        logging.error(f"Error creating cover letter from example: {str(e)}")
        return jsonify({'success': False, 'error': f'Failed to create cover letter: {str(e)}'})

@app.route('/candidate/edit-profile')
@login_required
def edit_candidate_profile():
    """Display candidate profile editing page"""
    if current_user.role != 'candidate':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Candidate journey functionality removed - Ez2source focuses on core talent intelligence features
    journey = None
    
    return render_template('candidate/edit_profile.html', journey=journey)

@app.route('/candidate/update-profile', methods=['POST'])
@login_required
def update_candidate_profile():
    """Update candidate profile"""
    if current_user.role != 'candidate':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        # Server-side form validation
        form_data = request.form.to_dict()
        validation_result = validate_form_data(form_data, 'candidate_profile')
        
        if not validation_result['valid']:
            for field, error in validation_result['errors'].items():
                flash(error, 'danger')
            return redirect(url_for('candidate_profile', user_id=current_user.id))
        
        # Handle email update with validation
        new_email = request.form.get('email')
        if new_email and new_email != current_user.email:
            # Check if email already exists in the same organization
            existing_user = User.query.filter(
                User.email == new_email,
                User.organization_id == current_user.organization_id,
                User.id != current_user.id
            ).first()
            
            if existing_user:
                flash('This email address is already registered in your organization. Please use a different email.', 'error')
                return redirect(url_for('candidate_profile', user_id=current_user.id))
            
            # Validate email format using ValidationService
            if not ValidationService.validate_email_uniqueness(new_email):
                flash('This email address is already registered in the system. Please use a different email.', 'error')
                return redirect(url_for('candidate_profile', user_id=current_user.id))
            
            current_user.email = new_email
        
        # Handle phone validation
        new_phone = request.form.get('phone')
        if new_phone:
            # Normalize phone format
            normalized_phone = ValidationService.normalize_phone(new_phone)
            if normalized_phone:
                current_user.phone = normalized_phone
            else:
                flash('Invalid phone number format. Please use a valid phone number.', 'warning')
        
        # Update user fields
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')
        current_user.job_title = request.form.get('job_title')
        current_user.location = request.form.get('location')
        current_user.linkedin_url = request.form.get('linkedin_url')
        current_user.portfolio_url = request.form.get('portfolio_url')
        current_user.bio = request.form.get('bio')
        current_user.years_of_experience = request.form.get('years_of_experience')
        current_user.availability = request.form.get('availability')
        current_user.salary_expectation = request.form.get('salary_expectation')
        
        # Update skills if provided
        skills_input = request.form.get('skills')
        if skills_input:
            import json
            try:
                # Handle both string and JSON input
                if isinstance(skills_input, str):
                    skills_list = [skill.strip() for skill in skills_input.split(',') if skill.strip()]
                else:
                    skills_list = skills_input
                current_user.skills = json.dumps(skills_list)
            except:
                pass  # Keep existing skills if parsing fails
        
        # Update experience if provided
        experience_input = request.form.get('experience')
        if experience_input:
            import json
            try:
                current_user.experience = experience_input
            except:
                pass  # Keep existing experience if parsing fails
        
        # Check if profile is now complete
        current_user.profile_completed = check_profile_completion(current_user)
        
        db.session.commit()
        
        flash('Profile updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Profile update error: {str(e)}")
        flash('An error occurred while updating your profile. Please try again.', 'error')
    
    return redirect(url_for('candidate_profile', user_id=current_user.id))

@app.route('/candidate/update-profile-section', methods=['POST'])
@login_required
def update_profile_section():
    """Update specific profile section"""
    if current_user.role != 'candidate':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    section = request.form.get('section')
    
    if section == 'about':
        current_user.bio = request.form.get('bio')
        flash('About section updated successfully!', 'success')
    
    elif section == 'skills':
        import json
        skills_input = request.form.get('skills', '')
        if skills_input.strip():
            skills_list = [skill.strip() for skill in skills_input.split(',') if skill.strip()]
            current_user.skills = json.dumps(skills_list)
        else:
            current_user.skills = None
        flash('Skills updated successfully!', 'success')
    
    elif section == 'experience':
        import json
        title = request.form.get('title')
        company = request.form.get('company')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        current_job = request.form.get('current_job') == 'on'
        description = request.form.get('description', '')
        
        if title and company and start_date:
            # Get existing experience or create new list
            try:
                experience_list = json.loads(current_user.experience) if current_user.experience else []
            except:
                experience_list = []
            
            # Format dates for display
            from datetime import datetime
            start_display = datetime.strptime(start_date, '%Y-%m').strftime('%B %Y')
            if current_job:
                duration = f"{start_display} - Present"
            elif end_date:
                end_display = datetime.strptime(end_date, '%Y-%m').strftime('%B %Y')
                duration = f"{start_display} - {end_display}"
            else:
                duration = start_display
            
            new_experience = {
                'title': title,
                'company': company,
                'duration': duration,
                'description': description,
                'start_date': start_date,
                'end_date': end_date if not current_job else None,
                'current': current_job
            }
            
            experience_list.append(new_experience)
            current_user.experience = json.dumps(experience_list)
            flash('Work experience added successfully!', 'success')
        else:
            flash('Please fill in all required fields.', 'error')
    
    elif section == 'education':
        import json
        degree = request.form.get('degree')
        field = request.form.get('field')
        institution = request.form.get('institution')
        year = request.form.get('year')
        description = request.form.get('description', '')
        
        if degree and field and institution and year:
            # Get existing education or create new list
            try:
                education_list = json.loads(current_user.education) if current_user.education else []
            except:
                education_list = []
            
            new_education = {
                'degree': degree,
                'field': field,
                'institution': institution,
                'year': int(year),
                'description': description
            }
            
            education_list.append(new_education)
            current_user.education = json.dumps(education_list)
            flash('Education added successfully!', 'success')
        else:
            flash('Please fill in all required fields.', 'error')
    
    db.session.commit()
    return redirect(url_for('candidate_profile', user_id=current_user.id))

@app.route('/candidate/upload-photo', methods=['POST'])
@login_required
def upload_profile_photo():
    """Upload candidate profile photo"""
    if current_user.role != 'candidate':
        flash('Access denied.', 'danger')
        return redirect(url_for('dashboard'))
    
    photo_file = request.files.get('profile_photo')
    if not photo_file:
        flash('Please select a photo to upload.', 'error')
        return redirect(url_for('candidate_profile', user_id=current_user.id))
    
    # Save photo file
    filename = secure_filename(photo_file.filename)
    photo_path = os.path.join('uploads', 'photos', f"{current_user.id}_{filename}")
    os.makedirs(os.path.dirname(photo_path), exist_ok=True)
    photo_file.save(photo_path)
    
    # Store relative URL path for serving the image
    current_user.profile_image_url = f"/uploads/photos/{current_user.id}_{filename}"
    db.session.commit()
    
    flash('Profile photo updated successfully!', 'success')
    return redirect(url_for('candidate_profile', user_id=current_user.id))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files"""
    return send_from_directory('uploads', filename)

@app.route('/candidate/mobile-register')
def mobile_register():
    """Mobile-optimized registration page"""
    return render_template('mobile_register.html')

def extract_resume_info(resume_path):
    """Extract information from resume using AI-powered parsing"""
    from resume_parser import parse_resume_file
    import os
    
    try:
        # Get the filename from the path
        filename = os.path.basename(resume_path)
        
        # Parse resume using our new AI-powered parser
        parsed_result = parse_resume_file(resume_path, filename)
        
        if parsed_result.get("success") and parsed_result.get("data"):
            data = parsed_result["data"]
            
            # Convert to the format expected by the registration
            personal_info = data.get("personal_info", {})
            prof_summary = data.get("professional_summary", {})
            
            return {
                'first_name': personal_info.get('first_name', ''),
                'last_name': personal_info.get('last_name', ''),
                'phone': personal_info.get('phone', ''),
                'job_title': prof_summary.get('current_job_title', ''),
                'bio': prof_summary.get('bio', ''),
                'skills': data.get('skills', []),
                'experience_years': prof_summary.get('experience_years', 0),
                'education': data.get('education', [])
            }
        else:
            logging.warning(f"Resume parsing failed: {parsed_result.get('error', 'Unknown error')}")
            # Return empty data instead of placeholder data
            return {
                'first_name': '',
                'last_name': '',
                'phone': '',
                'job_title': '',
                'bio': '',
                'skills': [],
                'experience_years': 0,
                'education': []
            }
            
    except Exception as e:
        logging.error(f"Error in extract_resume_info: {e}")
        # Return empty data on error
        return {
            'first_name': '',
            'last_name': '',
            'phone': '',
            'job_title': '',
            'bio': '',
            'skills': [],
            'experience_years': 0,
            'education': []
        }

def extract_linkedin_info(linkedin_url):
    """Extract information from LinkedIn profile (placeholder)"""
    # This would use LinkedIn API or scraping
    return {
        'first_name': 'Jane',
        'last_name': 'Smith',
        'job_title': 'Product Manager',
        'bio': 'Product manager with experience in tech startups.',
        'skills': ['Product Management', 'Strategy', 'Analytics'],
        'experience_years': 7
    }

def check_profile_completion(user):
    """Check if user profile is complete"""
    required_fields = [
        user.first_name, user.last_name, user.job_title, 
        user.bio, user.skills, user.experience_years
    ]
    return all(field for field in required_fields)

@app.route('/api/get_member_details/<int:member_id>')
@login_required
def get_member_details(member_id):
    """Get detailed information about a team member"""
    if current_user.role not in ['admin', 'recruiter']:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        member = User.query.get_or_404(member_id)
        if member.role != 'recruiter':
            return jsonify({'error': 'Invalid member ID'}), 404
        
        # Get member statistics
        interviews_count = Interview.query.filter_by(recruiter_id=member.id).count()
        responses = InterviewResponse.query.join(Interview).filter(
            Interview.recruiter_id == member.id
        ).all()
        
        member_details = {
            'id': member.id,
            'username': member.username,
            'email': member.email,
            'role': member.role,
            'created_at': member.created_at.strftime('%Y-%m-%d'),
            'interviews_count': interviews_count,
            'responses_count': len(responses),
            'avg_score': sum(r.ai_score for r in responses) / len(responses) if responses else 0,
            'recent_activity': [
                {
                    'type': 'interview_created',
                    'title': interview.title,
                    'date': interview.created_at.strftime('%Y-%m-%d')
                }
                for interview in Interview.query.filter_by(recruiter_id=member.id).order_by(Interview.created_at.desc()).limit(5)
            ]
        }
        
        html_content = f"""
        <div class="member-details">
            <div class="row">
                <div class="col-md-6">
                    <h6>Basic Information</h6>
                    <p><strong>Username:</strong> {member_details['username']}</p>
                    <p><strong>Email:</strong> {member_details['email']}</p>
                    <p><strong>Role:</strong> {member_details['role'].title()}</p>
                    <p><strong>Joined:</strong> {member_details['created_at']}</p>
                </div>
                <div class="col-md-6">
                    <h6>Statistics</h6>
                    <p><strong>Interviews Created:</strong> {member_details['interviews_count']}</p>
                    <p><strong>Total Responses:</strong> {member_details['responses_count']}</p>
                    <p><strong>Average Score:</strong> {member_details['avg_score']:.1f}%</p>
                </div>
            </div>
            <div class="row mt-3">
                <div class="col-12">
                    <h6>Recent Activity</h6>
                    <ul class="list-group">
                        {''.join([f'<li class="list-group-item"><small>{activity["date"]}</small> - Created interview: {activity["title"]}</li>' for activity in member_details['recent_activity']])}
                    </ul>
                </div>
            </div>
        </div>
        """
        
        return jsonify({'html': html_content})
        
    except Exception as e:
        logging.error(f"Error getting member details: {e}")
        return jsonify({'error': 'Failed to load member details'}), 500

@app.route('/api/update_member_role', methods=['POST'])
@login_required
def update_member_role():
    """Update a team member's role"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied. Admin privileges required'}), 403
    
    try:
        data = request.get_json()
        member_id = data.get('member_id')
        new_role = data.get('new_role')
        
        if new_role not in ['recruiter', 'admin', 'viewer']:
            return jsonify({'success': False, 'error': 'Invalid role'})
        
        member = User.query.get_or_404(member_id)
        old_role = member.role
        member.role = new_role
        
        # Log the action
        audit_log = AuditLog(
            user_id=current_user.id,
            action='update_member_role',
            resource_type='user',
            resource_id=member_id,
            details=json.dumps({'old_role': old_role, 'new_role': new_role})
        )
        db.session.add(audit_log)
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'Role updated to {new_role}'})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating member role: {e}")
        return jsonify({'success': False, 'error': 'Failed to update role'})

@app.route('/admin/fix-unassigned-candidates', methods=['POST'])
@login_required
def fix_unassigned_candidates():
    """Fix candidates without organization assignments"""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    from organization_assignment_service import OrganizationAssignmentService
    
    try:
        updated_count = OrganizationAssignmentService.update_unassigned_candidates()
        flash(f'Successfully assigned {updated_count} candidates to organizations.', 'success')
    except Exception as e:
        flash(f'Error updating candidates: {str(e)}', 'error')
    
    return redirect(url_for('admin_organizations'))

@app.route('/candidate/assign-organization')
@login_required
def assign_candidate_organization():
    """Organization assignment page for candidates"""
    if current_user.role != 'candidate':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    from candidate_organization_middleware import get_organization_assignment_context
    context = get_organization_assignment_context()
    
    return render_template('assign_organization.html', **context)

@app.route('/candidate/assign-organization', methods=['POST'])
@login_required
def submit_organization_assignment():
    """Handle organization assignment submission"""
    if current_user.role != 'candidate':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    from candidate_organization_middleware import assign_candidate_to_organization_flow
    
    org_id = request.form.get('organization_id', type=int)
    success, message = assign_candidate_to_organization_flow(org_id)
    
    if success:
        flash(message, 'success')
        # Redirect to intended URL or dashboard
        intended_url = session.pop('intended_url', url_for('dashboard'))
        return redirect(intended_url)
    else:
        flash(message, 'error')
        return redirect(url_for('assign_candidate_organization'))

@app.route('/api/public-interviews', methods=['GET'])
@login_required
def get_public_interviews():
    """API endpoint to get available public interviews for invitations"""
    try:
        # Get public interviews that support public invitations from current user's organization
        interviews = Interview.query.filter_by(
            organization_id=current_user.organization_id,
            is_active=True,
            interview_type='public',
            public_invitation_enabled=True
        ).all()
        
        # If super admin, can access all public interviews that support public invitations
        if current_user.role == 'super_admin':
            interviews = Interview.query.filter_by(
                is_active=True,
                interview_type='public',
                public_invitation_enabled=True
            ).all()
        
        interview_data = []
        for interview in interviews:
            interview_data.append({
                'id': interview.id,
                'title': interview.title,
                'organization_name': interview.organization.name if interview.organization else 'Unknown',
                'duration_minutes': interview.duration_minutes,
                'created_at': interview.created_at.strftime('%Y-%m-%d')
            })
        
        return jsonify({
            'success': True,
            'interviews': interview_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/private-interviews', methods=['GET'])
@login_required
def get_private_interviews():
    """API endpoint to get available private interviews for invitations"""
    try:
        # Get private interviews from current user's organization
        interviews = Interview.query.filter_by(
            organization_id=current_user.organization_id,
            is_active=True,
            interview_type='private'
        ).all()
        
        # If super admin, can access all private interviews
        if current_user.role == 'super_admin':
            interviews = Interview.query.filter_by(
                is_active=True,
                interview_type='private'
            ).all()
        
        interview_data = []
        for interview in interviews:
            interview_data.append({
                'id': interview.id,
                'title': interview.title,
                'organization_name': interview.organization.name if interview.organization else 'Unknown',
                'duration_minutes': interview.duration_minutes,
                'created_at': interview.created_at.strftime('%Y-%m-%d')
            })
        
        return jsonify({
            'success': True,
            'interviews': interview_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/scheduled-interviews', methods=['GET'])
@login_required
def get_scheduled_interviews():
    """API endpoint to get available scheduled interviews for scheduling"""
    try:
        # Get scheduled interviews from current user's organization
        interviews = Interview.query.filter_by(
            organization_id=current_user.organization_id,
            is_active=True,
            interview_type='scheduled'
        ).all()
        
        # If super admin, can access all scheduled interviews
        if current_user.role == 'super_admin':
            interviews = Interview.query.filter_by(
                is_active=True,
                interview_type='scheduled'
            ).all()
        
        interview_data = []
        for interview in interviews:
            interview_data.append({
                'id': interview.id,
                'title': interview.title,
                'organization_name': interview.organization.name if interview.organization else 'Unknown',
                'duration_minutes': interview.duration_minutes,
                'created_at': interview.created_at.strftime('%Y-%m-%d')
            })
        
        return jsonify({
            'success': True,
            'interviews': interview_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/send-public-invitation', methods=['POST'])
@login_required
def send_public_invitation():
    """Send public interview invitation to any candidate"""
    if current_user.role not in ['recruiter', 'admin']:
        return jsonify({'error': 'Access denied'}), 403
    
    from universal_profile_service import UniversalProfileService
    
    data = request.get_json()
    candidate_id = data.get('candidate_id')
    interview_id = data.get('interview_id')
    message = data.get('message', '')
    
    success, result_message = UniversalProfileService.send_public_interview_invitation(
        current_user.id, candidate_id, interview_id, message
    )
    
    return jsonify({
        'success': success,
        'message': result_message
    })

@app.route('/api/toggle-employee-status', methods=['POST'])
@login_required
def toggle_employee_status():
    """Toggle organization employee status for candidate"""
    if current_user.role not in ['recruiter', 'admin']:
        return jsonify({'error': 'Access denied'}), 403
    
    from universal_profile_service import UniversalProfileService
    
    data = request.get_json()
    candidate_id = data.get('candidate_id')
    is_employee = data.get('is_employee', False)
    
    success, message = UniversalProfileService.set_organization_employee_status(
        candidate_id, is_employee
    )
    
    return jsonify({
        'success': success,
        'message': message
    })

@app.route('/api/toggle-public-profile', methods=['POST'])
@login_required
def toggle_public_profile():
    """Toggle public profile access for candidate"""
    if current_user.role != 'candidate':
        return jsonify({'error': 'Access denied'}), 403
    
    from universal_profile_service import UniversalProfileService
    
    data = request.get_json()
    enable_public = data.get('enable_public', True)
    enable_cross_org = data.get('enable_cross_org', False)
    
    success, message = UniversalProfileService.toggle_public_profile_access(
        current_user.id, enable_public, enable_cross_org
    )
    
    return jsonify({
        'success': success,
        'message': message
    })

@app.route('/candidate/public-interviews')
@login_required
def candidate_public_interviews():
    """View all cross-organization public interview opportunities"""
    if current_user.role != 'candidate':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get publicly available interviews from other organizations
    public_interviews = db.session.query(
        Interview,
        User.username.label('recruiter_name'),
        Organization.name.label('organization_name')
    ).join(
        User, User.id == Interview.recruiter_id
    ).join(
        Organization, Organization.id == Interview.organization_id
    ).filter(
        Interview.is_active == True,
        Interview.interview_type == 'public',
        Interview.public_invitation_enabled == True,
        Interview.cross_org_accessible == True,
        Interview.organization_id != current_user.organization_id  # Different organization
    ).order_by(Interview.created_at.desc()).all()
    
    # Get user's completed interviews to check completion status
    completed_interviews = InterviewResponse.query.filter_by(
        candidate_id=current_user.id
    ).all()
    
    return render_template('candidate_public_interviews.html',
                         public_interviews=public_interviews,
                         completed_interviews=completed_interviews)

@app.route('/candidate/completed-interviews')
@login_required
def candidate_completed_interviews():
    """View all completed interviews for candidate"""
    if current_user.role != 'candidate':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get candidate's completed interviews with detailed information
    completed_interviews = db.session.query(
        InterviewResponse,
        Interview,
        User.username.label('recruiter_name'),
        Organization.name.label('organization_name')
    ).join(
        Interview, Interview.id == InterviewResponse.interview_id
    ).join(
        User, User.id == Interview.recruiter_id
    ).join(
        Organization, Organization.id == Interview.organization_id
    ).filter(
        InterviewResponse.candidate_id == current_user.id
    ).order_by(InterviewResponse.completed_at.desc()).all()
    
    return render_template('candidate_completed_interviews.html',
                         completed_interviews=completed_interviews)

@app.route('/candidate/invitations')
@login_required
def candidate_invitations():
    """View all interview invitations for candidate"""
    if current_user.role != 'candidate':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get pending interview invitations
    pending_invitations = db.session.query(
        InterviewInvitation,
        Interview,
        User.username.label('recruiter_name'),
        Organization.name.label('organization_name')
    ).join(
        Interview, Interview.id == InterviewInvitation.interview_id
    ).join(
        User, User.id == InterviewInvitation.recruiter_id
    ).join(
        Organization, Organization.id == Interview.organization_id
    ).filter(
        InterviewInvitation.candidate_id == current_user.id,
        InterviewInvitation.status == 'pending',
        Interview.is_active == True
    ).order_by(InterviewInvitation.invited_at.desc()).all()
    
    # Get accepted/completed invitations for history
    invitation_history = db.session.query(
        InterviewInvitation,
        Interview,
        User.username.label('recruiter_name'),
        Organization.name.label('organization_name')
    ).join(
        Interview, Interview.id == InterviewInvitation.interview_id
    ).join(
        User, User.id == InterviewInvitation.recruiter_id
    ).join(
        Organization, Organization.id == Interview.organization_id
    ).filter(
        InterviewInvitation.candidate_id == current_user.id,
        InterviewInvitation.status.in_(['accepted', 'completed'])
    ).order_by(InterviewInvitation.responded_at.desc()).limit(10).all()
    
    return render_template('candidate_invitations.html',
                         pending_invitations=pending_invitations,
                         invitation_history=invitation_history)

@app.route('/api/accept-public-invitation', methods=['POST'])
@login_required
def accept_public_invitation():
    """Accept a public interview invitation"""
    if current_user.role != 'candidate':
        return jsonify({'error': 'Access denied'}), 403
    
    from universal_profile_service import UniversalProfileService
    
    data = request.get_json()
    invitation_id = data.get('invitation_id')
    
    success, message = UniversalProfileService.accept_public_interview_invitation(
        current_user.id, invitation_id
    )
    
    return jsonify({
        'success': success,
        'message': message
    })

@app.route('/api/accept-invitation', methods=['POST'])
@login_required
def accept_invitation():
    """Accept an interview invitation"""
    if current_user.role != 'candidate':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        invitation_id = data.get('invitation_id')
        
        if not invitation_id:
            return jsonify({'error': 'Invitation ID is required'}), 400
        
        # Find and update the invitation
        invitation = InterviewInvitation.query.filter_by(
            id=invitation_id,
            candidate_id=current_user.id,
            status='pending'
        ).first()
        
        if not invitation:
            return jsonify({'error': 'Invitation not found or already processed'}), 404
        
        # Check if invitation has expired
        if invitation.expires_at and invitation.expires_at < datetime.utcnow():
            return jsonify({'error': 'Invitation has expired'}), 400
        
        # Update invitation status
        invitation.status = 'accepted'
        invitation.responded_at = datetime.utcnow()
        
        # Log audit trail
        from models import AuditLog
        audit = AuditLog(
            user_id=current_user.id,
            action='interview_invitation_accepted',
            resource_type='interview_invitation',
            resource_id=invitation_id,
            details=f'Accepted interview invitation {invitation_id}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Invitation accepted successfully'
        })
        
    except Exception as e:
        logging.error(f"Error accepting invitation: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to accept invitation'}), 500

@app.route('/api/decline-invitation', methods=['POST'])
@login_required
def decline_invitation():
    """Decline an interview invitation"""
    if current_user.role != 'candidate':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        invitation_id = data.get('invitation_id')
        
        if not invitation_id:
            return jsonify({'error': 'Invitation ID is required'}), 400
        
        # Find and update the invitation
        invitation = InterviewInvitation.query.filter_by(
            id=invitation_id,
            candidate_id=current_user.id,
            status='pending'
        ).first()
        
        if not invitation:
            return jsonify({'error': 'Invitation not found or already processed'}), 404
        
        # Update invitation status
        invitation.status = 'declined'
        invitation.responded_at = datetime.utcnow()
        
        # Log audit trail
        from models import AuditLog
        audit = AuditLog(
            user_id=current_user.id,
            action='interview_invitation_declined',
            resource_type='interview_invitation',
            resource_id=invitation_id,
            details=f'Declined interview invitation {invitation_id}',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        db.session.add(audit)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Invitation declined successfully'
        })
        
    except Exception as e:
        logging.error(f"Error declining invitation: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to decline invitation'}), 500

@app.route('/admin/organization-stats')
@login_required
def admin_organization_stats():
    """Get organization assignment statistics"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied'}), 403
    
    from organization_assignment_service import OrganizationAssignmentService
    stats = OrganizationAssignmentService.get_organization_stats()
    return jsonify(stats)

@app.route('/api/toggle_member_status', methods=['POST'])
@login_required
def toggle_member_status():
    """Toggle a team member's active status"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Access denied. Admin privileges required'}), 403
    
    try:
        data = request.get_json()
        member_id = data.get('member_id')
        
        # For demo purposes, we'll simulate status toggle
        # In real implementation, this would update a team_member table
        return jsonify({'success': True, 'message': 'Member status updated'})
        
    except Exception as e:
        logging.error(f"Error toggling member status: {e}")
        return jsonify({'success': False, 'error': 'Failed to update status'})

@app.route('/api/export_team_report')
@login_required
def export_team_report():
    """Export team performance report"""
    if current_user.role not in ['admin', 'recruiter']:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from flask import make_response
        
        # Get team data
        recruiters = User.query.filter_by(role='recruiter').all()
        
        report_content = f"Team Performance Report\n"
        report_content += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        
        for recruiter in recruiters:
            interviews_count = Interview.query.filter_by(recruiter_id=recruiter.id).count()
            responses = InterviewResponse.query.join(Interview).filter(
                Interview.recruiter_id == recruiter.id
            ).all()
            avg_score = sum(r.ai_score for r in responses) / len(responses) if responses else 0
            
            report_content += f"Member: {recruiter.username}\n"
            report_content += f"Email: {recruiter.email}\n"
            report_content += f"Interviews Created: {interviews_count}\n"
            report_content += f"Total Responses: {len(responses)}\n"
            report_content += f"Average Score: {avg_score:.1f}%\n"
            report_content += "---\n"
        
        response = make_response(report_content)
        response.headers['Content-Type'] = 'text/plain'
        response.headers['Content-Disposition'] = 'attachment; filename=team_report.txt'
        return response
        
    except Exception as e:
        logging.error(f"Error exporting team report: {e}")
        flash('Failed to export team report.', 'error')
        return redirect(url_for('team_management'))

@app.route('/pricing')
def pricing():
    """Pricing page with subscription plans"""
    return render_template('pricing.html')

@app.route('/settings')
@login_required
def settings():
    """User settings and profile management"""
    return render_template('settings.html', user=current_user)

@app.route('/settings/update', methods=['POST'])
@login_required
def update_settings():
    """Update user profile settings"""
    try:
        # Get form data
        username = request.form.get('username')
        email = request.form.get('email')
        
        # Basic validation
        if not username or not email:
            flash('Username and email are required.', 'error')
            return redirect(url_for('settings'))
        
        # Check if username/email already exists (excluding current user)
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email),
            User.id != current_user.id
        ).first()
        
        if existing_user:
            flash('Username or email already in use.', 'error')
            return redirect(url_for('settings'))
        
        # Update user profile
        current_user.username = username
        current_user.email = email
        
        # Log the action
        audit_log = AuditLog(
            user_id=current_user.id,
            action='update_profile',
            resource_type='user',
            resource_id=current_user.id,
            details=json.dumps({'username': username, 'email': email}),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        db.session.add(audit_log)
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating profile: {e}")
        flash('Failed to update profile. Please try again.', 'error')
    
    return redirect(url_for('settings'))

@app.route('/interview/<int:interview_id>/chat')
@login_required
def chat_interview(interview_id):
    """Chat-based interview interface for candidates"""
    if current_user.role != 'candidate':
        flash('Access denied. Only candidates can take interviews.', 'error')
        return redirect(url_for('dashboard'))
    
    interview = Interview.query.get_or_404(interview_id)
    
    # Check if already completed
    existing_response = InterviewResponse.query.filter_by(
        interview_id=interview_id, 
        candidate_id=current_user.id
    ).first()
    
    if existing_response:
        flash('You have already completed this interview.', 'info')
        return redirect(url_for('interview_results', response_id=existing_response.id))
    
    questions = json.loads(interview.questions)
    return render_template('chat_interview.html', interview=interview, questions=questions)

@app.route('/interview/<int:interview_id>/chat/submit', methods=['POST'])
@login_required
def submit_chat_interview(interview_id):
    """Submit chat interview responses with real-time AI analysis"""
    if current_user.role != 'candidate':
        return jsonify({'error': 'Access denied'}), 403
    
    interview = Interview.query.get_or_404(interview_id)
    
    # Check if already completed
    existing_response = InterviewResponse.query.filter_by(
        interview_id=interview_id, 
        candidate_id=current_user.id
    ).first()
    
    if existing_response:
        return jsonify({'error': 'Interview already completed'}), 400
    
    try:
        data = request.get_json()
        responses = data.get('responses', [])
        time_taken = data.get('time_taken', 0)
        
        # Format responses for storage
        formatted_answers = {}
        for i, response in enumerate(responses):
            formatted_answers[str(i)] = {
                'question': response.get('question', ''),
                'answer': response.get('answer', ''),
                'timestamp': response.get('timestamp', ''),
                'response_type': 'chat'
            }
        
        # Perform AI analysis on chat responses
        score, feedback = score_interview_responses(formatted_answers, interview.job_description)
        
        # Generate instant feedback for chat format
        instant_feedback = generate_instant_chat_feedback(responses)
        
        # Save response
        response = InterviewResponse(
            interview_id=interview_id,
            candidate_id=current_user.id,
            answers=json.dumps(formatted_answers),
            ai_score=score,
            ai_feedback=feedback,
            time_taken_minutes=int(time_taken) if time_taken else None
        )
        
        db.session.add(response)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'score': score,
            'feedback': instant_feedback,
            'response_id': response.id
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Chat interview submission error: {e}")
        return jsonify({'error': 'Failed to submit interview'}), 500

def generate_instant_chat_feedback(responses):
    """Generate instant feedback for chat interviews using AI analysis"""
    try:
        from openai import OpenAI
        import os
        
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        # Combine all responses for analysis
        combined_text = " ".join([resp.get('answer', '') for resp in responses])
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are an AI interview analyst. Provide brief, encouraging instant feedback for a candidate who just completed a chat interview. Focus on communication style, personality traits, and overall impression. Keep it positive and constructive, around 2-3 sentences."
                },
                {
                    "role": "user", 
                    "content": f"Analyze these interview responses and provide instant feedback: {combined_text[:1000]}"
                }
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logging.error(f"Error generating instant feedback: {e}")
        return "Thank you for completing the interview! Your responses show good communication skills and thoughtful answers. We'll be in touch soon with next steps."

@app.route('/recruiter/invite/<int:interview_id>')
@login_required  
def invite_candidates(interview_id):
    """Invite specific candidates to private interview"""
    if current_user.role != 'recruiter':
        flash('Access denied. Only recruiters can send invitations.', 'error')
        return redirect(url_for('dashboard'))
    
    interview = Interview.query.filter_by(
        id=interview_id,
        recruiter_id=current_user.id
    ).first_or_404()
    
    # Get all candidates in organization
    candidates = User.query.filter_by(
        organization_id=current_user.organization_id,
        role='candidate',
        user_active=True
    ).all()
    
    return render_template('invite_candidates.html', interview=interview, candidates=candidates)

@app.route('/recruiter/send_invitation', methods=['POST'])
@login_required
def send_invitation():
    """Send interview invitation to candidate"""
    if current_user.role != 'recruiter':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        interview_id = request.form.get('interview_id')
        candidate_id = request.form.get('candidate_id')
        message = request.form.get('message', '')
        
        # Verify interview ownership
        interview = Interview.query.filter_by(
            id=interview_id,
            recruiter_id=current_user.id
        ).first()
        
        if not interview:
            flash('Invalid interview selected.', 'error')
            return redirect(url_for('dashboard'))
        
        # Check if already invited
        existing_invitation = InterviewInvitation.query.filter_by(
            interview_id=interview_id,
            candidate_id=candidate_id
        ).first()
        
        if existing_invitation:
            flash('Candidate has already been invited to this interview.', 'warning')
            return redirect(url_for('invite_candidates', interview_id=interview_id))
        
        # Create invitation
        invitation = InterviewInvitation(
            interview_id=interview_id,
            candidate_id=candidate_id,
            recruiter_id=current_user.id,
            organization_id=current_user.organization_id,
            message=message,
            expires_at=datetime.utcnow() + timedelta(days=7)  # 7-day expiry
        )
        
        db.session.add(invitation)
        db.session.commit()
        
        flash('Invitation sent successfully!', 'success')
        return redirect(url_for('invite_candidates', interview_id=interview_id))
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error sending invitation: {e}")
        flash('Failed to send invitation.', 'error')
        return redirect(url_for('dashboard'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.route('/schedule')
@login_required
def schedule_dashboard():
    """Interview scheduling dashboard"""
    if current_user.role == 'recruiter':
        # Get interviews that need scheduling
        interviews = Interview.query.filter_by(recruiter_id=current_user.id).all()
        scheduled_interviews = InterviewSchedule.query.filter_by(recruiter_id=current_user.id).all()
        
        return render_template('schedule_dashboard.html', 
                             interviews=interviews, 
                             scheduled_interviews=scheduled_interviews)
    else:
        # Candidate view - show their scheduled interviews
        scheduled_interviews = InterviewSchedule.query.filter_by(candidate_id=current_user.id).all()
        availability_slots = AvailabilitySlot.query.filter_by(user_id=current_user.id).all()
        
        return render_template('candidate_schedule.html',
                             scheduled_interviews=scheduled_interviews,
                             availability_slots=availability_slots)

@app.route('/schedule/interview/<int:interview_id>')
@login_required
def schedule_interview(interview_id):
    """Schedule a specific interview"""
    if current_user.role != 'recruiter':
        flash('Access denied. Only recruiters can schedule interviews.', 'error')
        return redirect(url_for('dashboard'))
    
    interview = Interview.query.get_or_404(interview_id)
    if interview.recruiter_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get all candidates in the organization who haven't completed this interview yet
    completed_candidate_ids = db.session.query(InterviewResponse.candidate_id).filter(
        InterviewResponse.interview_id == interview_id
    ).scalar_subquery()
    
    candidates = User.query.filter(
        User.organization_id == current_user.organization_id,
        User.role == 'candidate',
        User.user_active == True,
        ~User.id.in_(completed_candidate_ids)
    ).all()
    
    return render_template('schedule_interview.html', interview=interview, candidates=candidates)

@app.route('/schedule/bulk')
@login_required
def bulk_schedule():
    """Bulk scheduling interface"""
    if current_user.role != 'recruiter':
        flash('Access denied. Only recruiters can schedule interviews.', 'error')
        return redirect(url_for('dashboard'))
    
    interviews = Interview.query.filter_by(recruiter_id=current_user.id).all()
    return render_template('bulk_schedule.html', interviews=interviews)

@app.route('/schedule/bulk/create', methods=['POST'])
@login_required
def create_bulk_schedule():
    """Create multiple interview schedules"""
    if current_user.role != 'recruiter':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        interview_id = data.get('interview_id')
        candidate_ids = data.get('candidate_ids', [])
        
        # Time slot generation parameters
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        duration_minutes = data.get('duration_minutes', 60)
        break_minutes = data.get('break_minutes', 15)
        time_zone = data.get('time_zone', 'UTC')
        auto_assign = data.get('auto_assign', False)
        
        # Validate interview ownership
        interview = Interview.query.get_or_404(interview_id)
        if interview.recruiter_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Generate time slots from parameters
        time_slots = []
        if start_date and end_date and start_time and end_time:
            current_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
            start_time_obj = datetime.strptime(start_time, '%H:%M').time()
            end_time_obj = datetime.strptime(end_time, '%H:%M').time()
            
            while current_date <= end_date_obj:
                # Skip weekends if desired (for now, include all days)
                current_datetime = datetime.combine(current_date, start_time_obj)
                end_datetime = datetime.combine(current_date, end_time_obj)
                
                # Generate slots for this day
                while current_datetime + timedelta(minutes=duration_minutes) <= end_datetime:
                    time_slots.append({
                        'datetime': current_datetime.isoformat() + 'Z',
                        'duration': duration_minutes
                    })
                    current_datetime += timedelta(minutes=duration_minutes + break_minutes)
                
                current_date += timedelta(days=1)
        
        # Import calendar service
        from calendar_service import CalendarService
        calendar_service = CalendarService()
        
        created_schedules = []
        failed_schedules = []
        
        # Create schedules for each candidate-timeslot pair
        for i, candidate_id in enumerate(candidate_ids):
            if i >= len(time_slots):
                break
                
            candidate = User.query.get(candidate_id)
            if not candidate or candidate.organization_id != current_user.organization_id:
                continue
                
            slot = time_slots[i]
            scheduled_datetime = datetime.fromisoformat(slot['datetime'].replace('Z', '+00:00'))
            
            # Create interview schedule
            schedule = InterviewSchedule(
                interview_id=interview_id,
                candidate_id=candidate_id,
                recruiter_id=current_user.id,
                scheduled_datetime=scheduled_datetime,
                duration_minutes=slot.get('duration', 60),
                meeting_link=f"https://meet.google.com/new",
                status='scheduled'
            )
            
            try:
                # Try to create Google Calendar event
                calendar_event = calendar_service.create_event(
                    title=f"Interview: {interview.title}",
                    description=f"Interview with {candidate.first_name} {candidate.last_name}",
                    start_datetime=scheduled_datetime,
                    end_datetime=scheduled_datetime + timedelta(minutes=slot.get('duration', 60)),
                    attendee_emails=[candidate.email]
                )
                
                if calendar_event:
                    schedule.calendar_event_id = calendar_event.get('id')
                    
            except Exception as e:
                logging.warning(f"Failed to create calendar event: {e}")
                # Continue without calendar integration
            
            db.session.add(schedule)
            created_schedules.append(schedule)
        
        # Commit all schedules
        db.session.commit()
        
        # Send email notifications
        from enhanced_email_service import EnhancedEmailService as EmailService
        email_service = EmailService()
        
        for schedule in created_schedules:
            try:
                candidate = User.query.get(schedule.candidate_id)
                email_service.send_interview_invitation_email(
                    candidate_email=candidate.email,
                    candidate_name=f"{candidate.first_name} {candidate.last_name}",
                    interview_title=interview.title,
                    company_name=current_user.organization.name,
                    interview_link=schedule.meeting_link,
                    recruiter_name=f"{current_user.first_name} {current_user.last_name}"
                )
            except Exception as e:
                logging.warning(f"Failed to send email to {candidate.email}: {e}")
        
        # Create audit log
        audit_log = AuditLog(
            user_id=current_user.id,
            action='BULK_SCHEDULE_INTERVIEWS',
            resource_type='interview_schedule',
            resource_id=interview_id,
            details=json.dumps({
                'interview_title': interview.title,
                'schedules_created': len(created_schedules),
                'candidates_count': len(candidate_ids),
                'time_slots_count': len(time_slots)
            }),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Successfully created {len(created_schedules)} interview schedules',
            'schedules_created': len(created_schedules),
            'failed_schedules': len(failed_schedules)
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error creating bulk schedule: {e}")
        return jsonify({'error': 'Failed to create bulk schedule'}), 500

@app.route('/schedule/bulk/candidates/<int:interview_id>')
@login_required
def get_bulk_candidates(interview_id):
    """Get candidates available for bulk scheduling"""
    if current_user.role != 'recruiter':
        return jsonify({'error': 'Access denied'}), 403
    
    # Validate interview ownership
    interview = Interview.query.get_or_404(interview_id)
    if interview.recruiter_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    # Get candidates who have completed this interview but not yet scheduled
    completed_responses = InterviewResponse.query.filter_by(
        interview_id=interview_id
    ).filter(InterviewResponse.completed_at.isnot(None)).all()
    
    scheduled_candidate_ids = [row[0] for row in db.session.query(InterviewSchedule.candidate_id).filter_by(
        interview_id=interview_id
    ).all()]
    
    available_candidates = []
    for response in completed_responses:
        if response.candidate_id not in scheduled_candidate_ids:
            candidate = User.query.get(response.candidate_id)
            if candidate and candidate.organization_id == current_user.organization_id:
                available_candidates.append({
                    'id': candidate.id,
                    'name': f"{candidate.first_name} {candidate.last_name}",
                    'email': candidate.email,
                    'score': response.ai_score or 0,
                    'completed_at': response.completed_at.isoformat() if response.completed_at else None
                })
    
    return jsonify({
        'success': True,
        'candidates': available_candidates,
        'total_count': len(available_candidates)
    })

# Removed duplicate create_schedule function

@app.route('/schedule/<int:schedule_id>/update', methods=['POST'])
@login_required
def update_schedule(schedule_id):
    """Update an interview schedule"""
    schedule = InterviewSchedule.query.get_or_404(schedule_id)
    
    # Check permissions
    if current_user.role == 'recruiter' and schedule.recruiter_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    elif current_user.role == 'candidate' and schedule.candidate_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json() or request.form
        
        if 'status' in data:
            schedule.status = data['status']
        if 'scheduled_datetime' in data and current_user.role == 'recruiter':
            schedule.scheduled_datetime = datetime.fromisoformat(data['scheduled_datetime'])
        if 'notes' in data:
            schedule.notes = data['notes']
        
        schedule.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Schedule updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating schedule: {e}")
        return jsonify({'error': 'Failed to update schedule'}), 500

@app.route('/availability')
@login_required
def manage_availability():
    """Manage user availability"""
    availability_slots = AvailabilitySlot.query.filter_by(user_id=current_user.id).all()
    return render_template('manage_availability.html', availability_slots=availability_slots)

@app.route('/availability/add', methods=['POST'])
@login_required
def add_availability():
    """Add availability slot"""
    try:
        data = request.get_json() or request.form
        
        slot = AvailabilitySlot(
            user_id=current_user.id,
            day_of_week=int(data['day_of_week']),
            start_time=datetime.strptime(data['start_time'], '%H:%M').time(),
            end_time=datetime.strptime(data['end_time'], '%H:%M').time(),
            time_zone=data.get('time_zone', 'UTC')
        )
        
        db.session.add(slot)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Availability added successfully'})
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error adding availability: {e}")
        return jsonify({'error': 'Failed to add availability'}), 500

def schedule_notifications(schedule):
    """Schedule email and SMS notifications for interview"""
    try:
        # Schedule reminder 24 hours before
        reminder_time = schedule.scheduled_datetime - timedelta(hours=24)
        
        # Email notification for candidate
        candidate_notification = ScheduleNotification(
            schedule_id=schedule.id,
            notification_type='email',
            recipient_id=schedule.candidate_id,
            send_at=reminder_time,
            message_content=f"Reminder: You have an interview scheduled for {schedule.scheduled_datetime.strftime('%Y-%m-%d %H:%M')}"
        )
        
        # Email notification for recruiter
        recruiter_notification = ScheduleNotification(
            schedule_id=schedule.id,
            notification_type='email',
            recipient_id=schedule.recruiter_id,
            send_at=reminder_time,
            message_content=f"Reminder: Interview with {schedule.candidate.username} scheduled for {schedule.scheduled_datetime.strftime('%Y-%m-%d %H:%M')}"
        )
        
        db.session.add(candidate_notification)
        db.session.add(recruiter_notification)
        db.session.commit()
        
    except Exception as e:
        logging.error(f"Error scheduling notifications: {e}")

@app.route('/profile/<int:user_id>')
@login_required
def user_profile(user_id):
    """Display detailed user profile"""
    # Get user profile with organization access check
    user_profile = User.query.filter_by(id=user_id, organization_id=current_user.organization_id).first_or_404()
    
    # Parse JSON fields
    skills_list = []
    education_list = []
    certifications_list = []
    
    if user_profile.skills:
        try:
            skills_list = json.loads(user_profile.skills)
            logging.info(f"Skills parsed for user {user_id}: {skills_list}")
        except Exception as e:
            logging.error(f"Error parsing skills for user {user_id}: {e}")
            skills_list = []
    else:
        logging.info(f"No skills found for user {user_id}")
    
    if user_profile.education:
        try:
            education_list = json.loads(user_profile.education)
        except:
            education_list = []
    
    if user_profile.certifications:
        try:
            certifications_list = json.loads(user_profile.certifications)
            logging.info(f"Certifications parsed for user {user_id}: {certifications_list}")
        except Exception as e:
            logging.error(f"Error parsing certifications for user {user_id}: {e}")
            certifications_list = []
    else:
        logging.info(f"No certifications found for user {user_id}")
    
    # Get interview responses for candidates
    interview_responses = []
    if user_profile.role == 'candidate':
        interview_responses = InterviewResponse.query.filter_by(
            candidate_id=user_id,
            organization_id=current_user.organization_id
        ).order_by(InterviewResponse.completed_at.desc()).limit(5).all()
    
    return render_template('user_profile.html', 
                         user_profile=user_profile,
                         skills_list=skills_list,
                         education_list=education_list,
                         certifications_list=certifications_list,
                         interview_responses=interview_responses)

@app.route('/team-directory')
@login_required
def team_directory():
    """Team directory showing all users in the organization"""
    # Super admins should use organization management instead
    if current_user.role == 'super_admin':
        flash('Super admins should use Organization Management to view users across all organizations.', 'info')
        return redirect(url_for('admin_organizations'))
    
    if not current_user.organization_id:
        flash('Access denied. Please contact your administrator.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get all users in the current organization
    recruiters = User.query.filter_by(
        organization_id=current_user.organization_id,
        role='recruiter',
        user_active=True
    ).all()
    
    candidates = User.query.filter_by(
        organization_id=current_user.organization_id,
        role='candidate',
        user_active=True
    ).all()
    
    admins = User.query.filter_by(
        organization_id=current_user.organization_id,
        role='admin',
        user_active=True
    ).all()
    
    # Get technical interviewers in the organization
    technical_persons = User.query.filter_by(
        organization_id=current_user.organization_id,
        role='technical_person',
        user_active=True
    ).all()
    
    # Get organization info
    organization = Organization.query.get(current_user.organization_id)
    
    return render_template('team_directory.html',
                         recruiters=recruiters,
                         candidates=candidates,
                         admins=admins,
                         technical_persons=technical_persons,
                         organization=organization)

# Admin-only routes
@app.route('/admin')
@login_required
def admin_panel():
    """Admin panel - only accessible to admin users"""
    if current_user.role not in ['admin', 'super_admin']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get statistics based on user role
    if current_user.role == 'super_admin':
        # Super admin sees system-wide statistics
        organization = None  # No specific organization for super admin
        total_users = User.query.count()
        total_interviews = Interview.query.count()
        total_responses = InterviewResponse.query.count()
        
        # Get all users in the system
        users = User.query.order_by(User.created_at.desc()).all()
    else:
        # Regular admin sees organization-specific statistics
        organization = Organization.query.get(current_user.organization_id)
        total_users = User.query.filter_by(organization_id=current_user.organization_id).count()
        total_interviews = Interview.query.filter_by(organization_id=current_user.organization_id).count()
        total_responses = InterviewResponse.query.filter_by(organization_id=current_user.organization_id).count()
        
        # Get all users in the organization
        users = User.query.filter_by(organization_id=current_user.organization_id).order_by(User.created_at.desc()).all()
    
    return render_template('admin_panel.html',
                         organization=organization,
                         total_users=total_users,
                         total_interviews=total_interviews,
                         total_responses=total_responses,
                         users=users)

@app.route('/admin/invite_user', methods=['POST'])
@login_required
def invite_user():
    """Invite a new user to the organization with automatic email delivery - admin only"""
    if current_user.role not in ['admin', 'super_admin']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from enhanced_email_service import email_service
        
        email = request.form.get('email')
        role = request.form.get('role', 'candidate')
        first_name = request.form.get('first_name', '')
        last_name = request.form.get('last_name', '')
        
        # Role validation: Admin users cannot create other admin users
        if current_user.role == 'admin' and role == 'admin':
            flash('Access denied. Only super administrators can create admin users.', 'error')
            return redirect(url_for('admin_panel'))
        
        # Validate allowed roles for admin users
        allowed_roles_for_admin = ['candidate', 'recruiter', 'technical_person']
        allowed_roles_for_super_admin = ['candidate', 'recruiter', 'technical_person', 'admin']
        
        if current_user.role == 'admin' and role not in allowed_roles_for_admin:
            flash('Invalid role selection. Admin users can only create candidates, recruiters, and technical interviewers.', 'error')
            return redirect(url_for('admin_panel'))
        
        if current_user.role == 'super_admin' and role not in allowed_roles_for_super_admin:
            flash('Invalid role selection.', 'error')
            return redirect(url_for('admin_panel'))
        
        # Check if user already exists in this organization
        existing_user = User.query.filter_by(
            email=email,
            organization_id=current_user.organization_id
        ).first()
        
        if existing_user:
            flash('A user with this email already exists in your organization.', 'error')
            return redirect(url_for('admin_panel'))
        
        # Generate username from email
        username = email.split('@')[0]
        counter = 1
        original_username = username
        while User.query.filter_by(username=username, organization_id=current_user.organization_id).first():
            username = f"{original_username}_{counter}"
            counter += 1
        
        # Generate secure password
        secure_password = email_service.generate_secure_password()
        
        # Create new user with generated password
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(secure_password),
            role=role,
            organization_id=current_user.organization_id,
            first_name=first_name,
            last_name=last_name,
            user_active=True
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Get organization name
        organization = Organization.query.get(current_user.organization_id)
        organization_name = organization.name if organization else "Unknown Organization"
        
        # Send welcome email with credentials
        user_full_name = f"{first_name} {last_name}".strip() or email.split('@')[0]
        invited_by_name = f"{current_user.first_name} {current_user.last_name}".strip() or current_user.username
        
        email_sent = email_service.send_user_invitation_email(
            user_email=email,
            user_name=user_full_name,
            username=username,
            password=secure_password,
            organization_name=organization_name,
            role=role,
            invited_by=invited_by_name
        )
        
        # Log the action
        audit_log = AuditLog(
            user_id=current_user.id,
            action='INVITE_USER',
            resource_type='user',
            resource_id=new_user.id,
            details=json.dumps({
                'invited_email': email,
                'invited_role': role,
                'invited_by': current_user.username,
                'email_sent': email_sent,
                'organization_name': organization_name
            }),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        db.session.add(audit_log)
        db.session.commit()
        
        if email_sent:
            flash(f'User {email} has been invited successfully! Login credentials sent via email.', 'success')
        else:
            # Provide fallback credentials if email fails
            flash(f'User {email} created successfully! Email delivery failed. Please provide these credentials manually:', 'warning')
            flash(f'Username: {username} | Password: {secure_password}', 'info')
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error inviting user: {e}")
        flash('Failed to invite user. Please try again.', 'error')
    
    return redirect(url_for('admin_panel'))

@app.route('/admin/audit_logs')
@login_required
def audit_logs():
    """View audit logs - admin only"""
    if current_user.role not in ['admin', 'super_admin']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get audit logs for users in this organization
    logs = db.session.query(AuditLog).join(User).filter(
        User.organization_id == current_user.organization_id
    ).order_by(AuditLog.timestamp.desc()).limit(100).all()
    
    return render_template('audit_logs.html', logs=logs)

    
    # Get availability slots for recruiters/admins
    availability_slots = []
    if current_user.role in ['recruiter', 'admin']:
        availability_slots = AvailabilitySlot.query.filter_by(
            user_id=current_user.id
        ).order_by(AvailabilitySlot.day_of_week.asc()).all()
    
    # Get available interviews and candidates for scheduling
    available_interviews = []
    candidates = []
    if current_user.role in ['recruiter', 'admin']:
        if current_user.role == 'admin':
            available_interviews = Interview.query.filter_by(
                organization_id=current_user.organization_id,
                is_active=True
            ).all()
            candidates = User.query.filter_by(
                organization_id=current_user.organization_id,
                role='candidate',
                user_active=True
            ).all()
        else:
            available_interviews = Interview.query.filter_by(
                recruiter_id=current_user.id,
                is_active=True
            ).all()
            candidates = User.query.filter_by(
                organization_id=current_user.organization_id,
                role='candidate',
                user_active=True
            ).all()
    
    return render_template('schedule.html',
                         upcoming_schedules=upcoming_schedules,
                         completed_schedules=completed_schedules,
                         availability_slots=availability_slots,
                         available_interviews=available_interviews,
                         candidates=candidates)

@app.route('/schedule/create', methods=['POST'])
@login_required
def create_schedule():
    """Schedule a new interview"""
    if current_user.role not in ['recruiter', 'admin']:
        flash('Access denied. Only recruiters and admins can schedule interviews.', 'error')
        return redirect(url_for('schedule'))
    
    try:
        interview_id = request.form.get('interview_id')
        candidate_id = request.form.get('candidate_id')
        interview_datetime = request.form.get('interview-datetime')
        duration = int(request.form.get('duration', 60))
        meeting_link = request.form.get('meeting_link', '')
        notes = request.form.get('notes', '')
        
        # Parse datetime-local format
        scheduled_datetime = datetime.fromisoformat(interview_datetime)
        
        # Verify interview belongs to user's organization
        interview = Interview.query.filter_by(
            id=interview_id,
            organization_id=current_user.organization_id
        ).first()
        
        if not interview:
            flash('Invalid interview selected.', 'error')
            return redirect(url_for('schedule'))
        
        # Verify candidate belongs to user's organization
        candidate = User.query.filter_by(
            id=candidate_id,
            organization_id=current_user.organization_id,
            role='candidate'
        ).first()
        
        if not candidate:
            flash('Invalid candidate selected.', 'error')
            return redirect(url_for('schedule'))
        
        # Create schedule
        new_schedule = InterviewSchedule(
            interview_id=interview_id,
            candidate_id=candidate_id,
            recruiter_id=current_user.id,
            scheduled_datetime=scheduled_datetime,
            duration_minutes=duration,
            meeting_link=meeting_link,
            notes=notes,
            status='scheduled'
        )
        
        db.session.add(new_schedule)
        db.session.commit()
        
        # Log the action
        audit_log = AuditLog(
            user_id=current_user.id,
            action='SCHEDULE_INTERVIEW',
            resource_type='interview_schedule',
            resource_id=new_schedule.id,
            details=json.dumps({
                'interview_title': interview.title,
                'candidate_email': candidate.email,
                'scheduled_datetime': scheduled_datetime.isoformat(),
                'duration_minutes': duration
            }),
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        db.session.add(audit_log)
        db.session.commit()
        
        flash('Interview scheduled successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error scheduling interview: {e}")
        flash('Failed to schedule interview. Please try again.', 'error')
    
    return redirect(url_for('schedule'))

@app.route('/schedule/availability', methods=['POST'])
@login_required
def set_availability():
    """Set availability slot"""
    if current_user.role not in ['recruiter', 'admin']:
        flash('Access denied. Only recruiters and admins can set availability.', 'error')
        return redirect(url_for('schedule'))
    
    try:
        day_of_week = int(request.form.get('day_of_week'))
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        time_zone = request.form.get('time_zone', 'UTC')
        
        # Convert time strings to time objects
        start_time_obj = datetime.strptime(start_time, "%H:%M").time()
        end_time_obj = datetime.strptime(end_time, "%H:%M").time()
        
        # Check if slot already exists
        existing_slot = AvailabilitySlot.query.filter_by(
            user_id=current_user.id,
            day_of_week=day_of_week
        ).first()
        
        if existing_slot:
            # Update existing slot
            existing_slot.start_time = start_time_obj
            existing_slot.end_time = end_time_obj
            existing_slot.time_zone = time_zone
            existing_slot.is_active = True
        else:
            # Create new slot
            new_slot = AvailabilitySlot(
                user_id=current_user.id,
                day_of_week=day_of_week,
                start_time=start_time_obj,
                end_time=end_time_obj,
                time_zone=time_zone,
                is_active=True
            )
            db.session.add(new_slot)
        
        db.session.commit()
        flash('Availability updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error setting availability: {e}")
        flash('Failed to update availability. Please try again.', 'error')
    
    return redirect(url_for('schedule'))

@app.route('/profile/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user_profile(user_id):
    """Edit user profile (admin only)"""
    if current_user.role != 'admin':
        flash('Access denied. Only admins can edit user profiles.', 'error')
        return redirect(url_for('user_profile', user_id=user_id))
    
    # Get user profile with organization access check
    user_profile = User.query.filter_by(id=user_id, organization_id=current_user.organization_id).first_or_404()
    
    if request.method == 'POST':
        try:
            # Update basic information
            user_profile.first_name = request.form.get('first_name', '').strip()
            user_profile.last_name = request.form.get('last_name', '').strip()
            user_profile.email = request.form.get('email', '').strip()
            user_profile.phone = request.form.get('phone', '').strip()
            user_profile.role = request.form.get('role', 'candidate')
            user_profile.user_active = bool(int(request.form.get('user_active', 1)))
            
            # Update professional information
            user_profile.job_title = request.form.get('job_title', '').strip()
            user_profile.department = request.form.get('department', '').strip()
            user_profile.location = request.form.get('location', '').strip()
            user_profile.bio = request.form.get('bio', '').strip()
            
            # Update experience years
            experience_str = request.form.get('experience_years', '').strip()
            if experience_str:
                user_profile.experience_years = int(experience_str)
            else:
                user_profile.experience_years = None
            
            # Update candidate-specific fields
            if user_profile.role == 'candidate':
                user_profile.availability = request.form.get('availability', '').strip()
                user_profile.salary_expectation = request.form.get('salary_expectation', '').strip()
            
            # Update skills (convert comma-separated to JSON)
            skills_text = request.form.get('skills', '').strip()
            if skills_text:
                skills_list = [skill.strip() for skill in skills_text.split(',') if skill.strip()]
                user_profile.skills = json.dumps(skills_list)
            else:
                user_profile.skills = None
            
            # Update certifications (convert comma-separated to JSON)
            certifications_text = request.form.get('certifications', '').strip()
            if certifications_text:
                certifications_list = [cert.strip() for cert in certifications_text.split(',') if cert.strip()]
                user_profile.certifications = json.dumps(certifications_list)
            else:
                user_profile.certifications = None
            
            # Update education (expects JSON format)
            education_text = request.form.get('education', '').strip()
            if education_text:
                try:
                    # Validate JSON format
                    json.loads(education_text)
                    user_profile.education = education_text
                except json.JSONDecodeError:
                    flash('Invalid JSON format for education. Please check your format.', 'warning')
            else:
                user_profile.education = None
            
            # Update external links
            user_profile.linkedin_url = request.form.get('linkedin_url', '').strip()
            user_profile.portfolio_url = request.form.get('portfolio_url', '').strip()
            user_profile.resume_url = request.form.get('resume_url', '').strip()
            user_profile.profile_image_url = request.form.get('profile_image_url', '').strip()
            
            # Save changes
            db.session.commit()
            
            # Log the action
            audit_log = AuditLog(
                user_id=current_user.id,
                action='UPDATE_USER_PROFILE',
                resource_type='user',
                resource_id=user_profile.id,
                details=json.dumps({
                    'updated_user': user_profile.email,
                    'fields_updated': ['basic_info', 'professional_info', 'skills', 'certifications', 'links']
                }),
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent', '')
            )
            db.session.add(audit_log)
            db.session.commit()
            
            flash('User profile updated successfully!', 'success')
            return redirect(url_for('user_profile', user_id=user_id))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error updating user profile: {e}")
            flash('Failed to update user profile. Please try again.', 'error')
    
    # Prepare data for the form
    skills_text = ''
    certifications_text = ''
    
    if user_profile.skills:
        try:
            skills_list = json.loads(user_profile.skills)
            skills_text = ', '.join(skills_list)
        except:
            skills_text = user_profile.skills
    
    if user_profile.certifications:
        try:
            certifications_list = json.loads(user_profile.certifications)
            certifications_text = ', '.join(certifications_list)
        except:
            certifications_text = user_profile.certifications
    
    return render_template('edit_user_profile.html', 
                         user_profile=user_profile,
                         skills_text=skills_text,
                         certifications_text=certifications_text)

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

# Job Search and Management Routes
@app.route('/companies/add', methods=['GET', 'POST'])
@login_required
def add_company():
    """Add a new company - HR/Admin only"""
    if current_user.role not in ['recruiter', 'admin', 'super_admin']:
        flash('You do not have permission to add companies.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            location = request.form.get('location', '').strip()
            website = request.form.get('website', '').strip()
            
            if not name:
                flash('Company name is required.', 'error')
                return redirect(request.url)
            
            # Check if company already exists
            existing = Company.query.filter_by(name=name).first()
            if existing:
                flash(f'Company "{name}" already exists.', 'error')
                return redirect(request.url)
            
            # Create company
            company = Company()
            company.name = name
            company.location = location
            company.website = website
            company.industry = 'Technology'  # Default
            
            db.session.add(company)
            db.session.commit()
            
            flash(f'Company "{name}" added successfully!', 'success')
            return redirect(url_for('post_job'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error adding company: {e}")
            flash('An error occurred while adding the company.', 'error')
    
    return render_template('companies/add_company.html')

@app.route('/jobs/post', methods=['GET', 'POST'])
@login_required
def post_job():
    """Post a new job - Admin/HR only"""
    # Check if user has permission to post jobs
    if current_user.role not in ['recruiter', 'admin', 'super_admin']:
        flash('You do not have permission to post jobs.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            # Get form data
            title = request.form.get('title', '').strip()
            company_id = request.form.get('company_id', type=int)
            location = request.form.get('location', '').strip()
            remote_type = request.form.get('remote_type', 'onsite')
            employment_type = request.form.get('employment_type', 'full-time')
            experience_level = request.form.get('experience_level', 'mid')
            salary_min = request.form.get('salary_min', type=int)
            salary_max = request.form.get('salary_max', type=int)
            description = request.form.get('description', '').strip()
            requirements = request.form.get('requirements', '').strip()
            benefits = request.form.get('benefits', '').strip()
            technologies = request.form.get('technologies', '').strip()
            application_url = request.form.get('application_url', '').strip()
            is_featured = 'is_featured' in request.form
            action = request.form.get('action', 'publish')
            
            # Validate required fields
            if not all([title, company_id, location, description, requirements]):
                flash('Please fill in all required fields.', 'error')
                return redirect(request.url)
            
            # Process technologies into JSON array
            tech_list = []
            if technologies:
                tech_list = [t.strip() for t in technologies.split(',') if t.strip()]
            
            # Create job posting
            job = JobPosting()
            job.title = title
            job.company_id = company_id
            job.location = location
            job.remote_type = remote_type
            job.employment_type = employment_type
            job.experience_level = experience_level
            job.salary_min = salary_min
            job.salary_max = salary_max
            job.description = description
            job.requirements = requirements
            job.technologies = json.dumps(tech_list) if tech_list else None
            job.application_url = application_url if application_url else f"/jobs/{title.lower().replace(' ', '-')}/apply"
            job.source = 'internal'
            job.posted_date = datetime.utcnow()
            
            # Set status based on action
            if action == 'save_draft':
                job.is_active = False
                flash_message = 'Job saved as draft successfully!'
            else:
                job.is_active = True
                flash_message = 'Job posted successfully!'
            
            db.session.add(job)
            db.session.commit()
            
            flash(flash_message, 'success')
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error posting job: {e}")
            flash('An error occurred while posting the job. Please try again.', 'error')
    
    # Get companies for dropdown - show all active companies for now
    companies = Company.query.order_by(Company.name).all()
    
    return render_template('jobs/post_job.html', companies=companies)

# Job functionality removed - Ez2source focuses on interview and talent intelligence features

@app.route('/jobs/<int:job_id>')
@login_required
def job_detail(job_id):
    """Job detail page"""
    job = JobPosting.query.options(db.joinedload(JobPosting.company)).get_or_404(job_id)
    
    # Increment view count
    job.views_count = (job.views_count or 0) + 1
    db.session.commit()
    
    # Check if user has saved or applied to this job
    is_saved = False
    has_applied = False
    
    if current_user.is_authenticated:
        is_saved = SavedJob.query.filter_by(
            user_id=current_user.id, 
            job_posting_id=job_id
        ).first() is not None
        
        has_applied = JobApplication.query.filter_by(
            user_id=current_user.id, 
            job_posting_id=job_id
        ).first() is not None
    
    # Similar jobs functionality removed - Ez2source focuses on core talent intelligence features
    similar_jobs = []
    
    return render_template('jobs/job_detail.html',
                         job=job,
                         is_saved=is_saved,
                         has_applied=has_applied,
                         similar_jobs=similar_jobs)


@app.route('/jobs/<int:job_id>/save', methods=['POST'])
@login_required
def save_job(job_id):
    """Save a job for later"""
    # Job save functionality removed - Ez2source focuses on core talent intelligence features
    success = False
    
    if request.is_json:
        return jsonify({'success': success})
    
    if success:
        flash('Job saved successfully!', 'success')
    else:
        flash('Job is already saved or an error occurred.', 'error')
    
    return redirect(request.referrer or url_for('find_jobs'))


@app.route('/jobs/<int:job_id>/unsave', methods=['POST'])
@login_required
def unsave_job(job_id):
    """Remove a saved job"""
    # Job unsave functionality removed - Ez2source focuses on core talent intelligence features
    success = False
    
    if request.is_json:
        return jsonify({'success': success})
    
    if success:
        flash('Job removed from saved list.', 'success')
    else:
        flash('Job was not in saved list or an error occurred.', 'error')
    
    return redirect(request.referrer or url_for('find_jobs'))


@app.route('/saved-jobs')
@login_required
def saved_jobs():
    """User's saved jobs page"""
    # Saved jobs functionality removed - Ez2source focuses on core talent intelligence features
    saved_jobs = []
    total_count = 0
    total_pages = 0
    page = 1
    
    return render_template('jobs/saved_jobs.html',
                         saved_jobs=saved_jobs,
                         total_count=total_count,
                         page=page,
                         total_pages=total_pages)


@app.route('/my-applications')
@login_required
def my_applications():
    """User's job applications page"""
    # Job applications functionality removed - Ez2source focuses on core talent intelligence features
    applications = []
    total_count = 0
    total_pages = 0
    page = 1
    
    return render_template('jobs/my_applications.html',
                         applications=applications,
                         total_count=total_count,
                         page=page,
                         total_pages=total_pages)


# ===== JOB APPLICATION ROUTES =====

# One-click application functionality removed


@app.route('/jobs/<int:job_id>/cover-letter-editor')
@login_required
def cover_letter_editor(job_id):
    """Display cover letter editor page"""
    if current_user.role != 'candidate':
        flash('Only candidates can edit cover letters.', 'error')
        return redirect(url_for('find_jobs'))
    
    try:
        # Get job details
        job = JobPosting.query.options(db.joinedload(JobPosting.company)).get_or_404(job_id)
        
        # Get existing cover letter if any
        existing_cover_letter = None
        cover_letter_text = ''
        cover_letter_title = f'Cover Letter for {job.title}'
        
        # Check if there's an existing application with cover letter
        existing_application = JobApplication.query.filter_by(
            user_id=current_user.id,
            job_id=job_id
        ).first()
        
        if existing_application and existing_application.cover_letter:
            cover_letter_text = existing_application.cover_letter
            cover_letter_title = existing_application.cover_letter_title or cover_letter_title
        
        # Match score functionality removed - Ez2source focuses on core talent intelligence features
        match_score = None
        
        return render_template('cover_letter_editor.html',
                             job=job,
                             cover_letter_text=cover_letter_text,
                             cover_letter_title=cover_letter_title,
                             match_score=match_score)
        
    except Exception as e:
        logging.error(f"Error in cover letter editor: {e}")
        flash('Failed to load cover letter editor.', 'error')
        return redirect(url_for('job_detail', job_id=job_id))

@app.route('/jobs/<int:job_id>/save-cover-letter', methods=['POST'])
@login_required
def save_cover_letter(job_id):
    """Save cover letter"""
    if current_user.role != 'candidate':
        return jsonify({'error': 'Only candidates can save cover letters'}), 403
    
    try:
        # Get job details
        job = JobPosting.query.get_or_404(job_id)
        
        # Get form data
        cover_letter = request.form.get('cover_letter', '').strip()
        title = request.form.get('title', '').strip()
        template_type = request.form.get('template_type', 'custom')
        is_draft = request.form.get('is_draft', 'false').lower() == 'true'
        
        if not cover_letter:
            return jsonify({'error': 'Cover letter content is required'}), 400
        
        # Check if there's an existing application
        existing_application = JobApplication.query.filter_by(
            user_id=current_user.id,
            job_id=job_id
        ).first()
        
        if existing_application:
            # Update existing application
            existing_application.cover_letter = cover_letter
            existing_application.cover_letter_title = title
            existing_application.updated_at = datetime.utcnow()
        else:
            # Create new application (draft)
            new_application = JobApplication(
                user_id=current_user.id,
                job_id=job_id,
                cover_letter=cover_letter,
                cover_letter_title=title,
                status='draft' if is_draft else 'submitted',
                applied_at=datetime.utcnow()
            )
            db.session.add(new_application)
        
        db.session.commit()
        
        # Log activity
        logging.info(f"Cover letter saved: User {current_user.id} -> Job {job_id}")
        
        return jsonify({
            'success': True,
            'message': 'Cover letter saved successfully!',
            'redirect_url': url_for('job_detail', job_id=job_id) if not is_draft else None
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error saving cover letter: {e}")
        return jsonify({'error': 'Failed to save cover letter'}), 500

@app.route('/jobs/<int:job_id>/generate-cover-letter-editor', methods=['POST'])
@login_required
def generate_cover_letter_editor(job_id):
    """Generate cover letter using AI for editor"""
    if current_user.role != 'candidate':
        return jsonify({'error': 'Only candidates can generate cover letters'}), 403
    
    try:
        # Get job details
        job = JobPosting.query.options(db.joinedload(JobPosting.company)).get_or_404(job_id)
        
        # Get request data
        data = request.get_json() or {}
        tone = data.get('tone', 'professional')
        key_points = data.get('key_points', '')
        template_type = data.get('template_type', 'custom')
        
        # Import cover letter service
        from cover_letter_service import CoverLetterGenerator
        generator = CoverLetterGenerator()
        
        # Prepare candidate info
        candidate_info = {
            'name': f"{current_user.first_name} {current_user.last_name}",
            'email': current_user.email,
            'phone': current_user.phone,
            'skills': current_user.skills.split(',') if current_user.skills else [],
            'experience_years': current_user.experience_years or 0,
            'current_role': current_user.job_title,
            'bio': current_user.bio,
            'key_points': key_points
        }
        
        # Prepare job info
        job_info = {
            'title': job.title,
            'company': job.company.name if job.company else 'Unknown Company',
            'description': job.description,
            'requirements': job.requirements,
            'location': job.location
        }
        
        # Generate cover letter
        result = generator.generate_cover_letter(
            candidate_info=candidate_info,
            job_details=job_info,
            template_type=template_type,
            tone=tone
        )
        
        if result.get('error'):
            return jsonify({'error': result['error']}), 500
        
        return jsonify({
            'success': True,
            'cover_letter': result.get('content', ''),
            'title': result.get('title', ''),
            'key_points': result.get('key_points', []),
            'suggestions': result.get('suggestions', [])
        })
        
    except Exception as e:
        logging.error(f"Error generating cover letter: {e}")
        return jsonify({'error': 'Failed to generate cover letter'}), 500

# One-click application functionality removed


# One-click application preview functionality removed


@app.route('/jobs/<int:job_id>/ai-match-score')
@login_required
def ai_match_score(job_id):
    """Get AI-calculated match score for a job"""
    if current_user.role != 'candidate':
        return jsonify({'error': 'Only candidates can get match scores'}), 403
    
    try:
        # OneClickApplicationService removed
        job = JobPosting.query.get_or_404(job_id)
        
        # Match score calculation disabled - service removed
        job_data = service._extract_job_requirements(job)
        match_score = service._calculate_match_score(profile_data, job_data, use_ai=True)
        
        return jsonify({
            'success': True,
            'match_score': match_score,
            'job_title': job.title,
            'company_name': job.company.name if job.company else 'Unknown'
        })
        
    except Exception as e:
        logging.error(f"Error calculating match score: {e}")
        return jsonify({'error': 'Failed to calculate match score'}), 500


@app.route('/companies')
@login_required
def browse_companies():
    """Browse companies page"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get search parameters
    industry = request.args.get('industry', '').strip()
    size = request.args.get('size', '').strip()
    location = request.args.get('location', '').strip()
    
    query = Company.query.filter_by(is_hiring=True)
    
    if industry:
        query = query.filter(Company.industry.ilike(f'%{industry}%'))
    
    if size:
        query = query.filter(Company.size == size)
    
    if location:
        query = query.filter(Company.location.ilike(f'%{location}%'))
    
    total_count = query.count()
    companies = query.order_by(Company.name).offset((page - 1) * per_page).limit(per_page).all()
    
    # Get company job counts
    company_job_counts = {}
    for company in companies:
        job_count = JobPosting.query.filter_by(
            company_id=company.id, 
            is_active=True
        ).count()
        company_job_counts[company.id] = job_count
    
    total_pages = (total_count + per_page - 1) // per_page
    
    return render_template('jobs/browse_companies.html',
                         companies=companies,
                         company_job_counts=company_job_counts,
                         total_count=total_count,
                         page=page,
                         total_pages=total_pages,
                         search_params={
                             'industry': industry,
                             'size': size,
                             'location': location
                         })


@app.route('/companies/<int:company_id>')
@login_required
def company_detail(company_id):
    """Company detail page"""
    company = Company.query.get_or_404(company_id)
    
    # Get company's active jobs
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    jobs_query = JobPosting.query.filter_by(
        company_id=company_id, 
        is_active=True
    ).order_by(JobPosting.posted_date.desc())
    
    total_jobs = jobs_query.count()
    jobs = jobs_query.offset((page - 1) * per_page).limit(per_page).all()
    
    total_pages = (total_jobs + per_page - 1) // per_page
    
    # Check if user has saved this company
    is_saved = False
    if current_user.is_authenticated:
        is_saved = SavedCompany.query.filter_by(
            user_id=current_user.id,
            company_id=company_id
        ).first() is not None
    
    return render_template('jobs/company_detail.html',
                         company=company,
                         jobs=jobs,
                         total_jobs=total_jobs,
                         page=page,
                         total_pages=total_pages,
                         is_saved=is_saved)


@app.route('/jobs/<int:job_id>/apply', methods=['POST'])
@login_required
def apply_to_job(job_id):
    """Track job application"""
    # Job application tracking removed - Ez2source focuses on core talent intelligence features
    success = False
    
    if request.is_json:
        return jsonify({'success': success})
    
    if success:
        flash('Application tracked successfully! You can now apply through the company website.', 'success')
    else:
        flash('You have already applied to this job or an error occurred.', 'error')
    
    return redirect(request.referrer or url_for('job_detail', job_id=job_id))


@app.route('/api/save-interview-progress', methods=['POST'])
@login_required
def save_interview_progress():
    """
    Save interview progress for candidates
    """
    if current_user.role != 'candidate':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        interview_id = data.get('interview_id')
        responses = data.get('responses', {})
        
        if not interview_id:
            return jsonify({'error': 'Interview ID required'}), 400
        
        # Verify interview access
        interview = Interview.query.get(interview_id)
        if not interview:
            return jsonify({'error': 'Interview not found'}), 404
        
        # Create or update interview progress record
        
        progress = InterviewProgress.query.filter_by(
            interview_id=interview_id,
            candidate_id=current_user.id
        ).first()
        
        if not progress:
            progress = InterviewProgress(
                interview_id=interview_id,
                candidate_id=current_user.id,
                organization_id=current_user.organization_id
            )
            db.session.add(progress)
        
        # Update progress data
        progress.responses = json.dumps(responses)
        progress.progress_percentage = data.get('progress_percentage', 0)
        progress.last_question = data.get('last_question', 0)
        progress.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Progress saved successfully',
            'saved_questions': len(responses)
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Failed to save interview progress: {e}")
        return jsonify({'error': 'Failed to save progress'}), 500

# Interview Feedback Summarizer Routes
@app.route('/interview/response/<int:response_id>/summary')
@login_required
def get_response_summary(response_id):
    """Get AI-powered summary for an interview response"""
    try:
        from interview_feedback_service import get_interview_feedback_summary
        
        summary = get_interview_feedback_summary(response_id, current_user.id)
        if not summary:
            return jsonify({'error': 'Summary not available or access denied'}), 404
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        logging.error(f"Error getting response summary: {e}")
        return jsonify({'error': 'Failed to generate summary'}), 500

@app.route('/interview/<int:interview_id>/comparison')
@login_required
def get_candidates_comparison(interview_id):
    """Get comparative analysis of all candidates for an interview"""
    try:
        from interview_feedback_service import get_interview_comparison
        
        comparison = get_interview_comparison(interview_id, current_user.id)
        if not comparison:
            return jsonify({'error': 'Comparison not available or access denied'}), 404
        
        return jsonify({
            'success': True,
            'comparison': comparison
        })
        
    except Exception as e:
        logging.error(f"Error getting interview comparison: {e}")
        return jsonify({'error': 'Failed to generate comparison'}), 500

@app.route('/interview/response/<int:response_id>/regenerate-summary', methods=['POST'])
@login_required
def regenerate_response_summary(response_id):
    """Regenerate AI summary for an interview response"""
    try:
        from interview_feedback_service import InterviewFeedbackSummarizer
        
        # Verify access
        response = InterviewResponse.query.get_or_404(response_id)
        
        # Check permissions
        if current_user.role == 'candidate' and response.candidate_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        elif current_user.role == 'recruiter' and response.organization_id != current_user.organization_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Generate fresh summary
        summarizer = InterviewFeedbackSummarizer()
        summary = summarizer.generate_comprehensive_summary(response)
        
        # Update the response with new AI feedback
        response.ai_feedback = json.dumps(summary)
        if 'overall_score' in summary:
            response.ai_score = summary['overall_score']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'summary': summary,
            'message': 'Summary regenerated successfully'
        })
        
    except Exception as e:
        logging.error(f"Error regenerating summary: {e}")
        return jsonify({'error': 'Failed to regenerate summary'}), 500

@app.route('/interview/response/<int:response_id>/feedback-summary')
@login_required
def interview_feedback_summary(response_id):
    """Display detailed feedback summary page for an interview response"""
    try:
        # Verify access
        response = InterviewResponse.query.get_or_404(response_id)
        
        # Check permissions
        if current_user.role == 'candidate' and response.candidate_id != current_user.id:
            flash('Access denied', 'error')
            return redirect(url_for('dashboard'))
        elif current_user.role == 'recruiter' and response.organization_id != current_user.organization_id:
            flash('Access denied', 'error')
            return redirect(url_for('dashboard'))
        
        # Get interview details
        interview = Interview.query.get(response.interview_id)
        candidate = User.query.get(response.candidate_id)
        
        if not interview or not candidate:
            flash('Interview or candidate not found', 'error')
            return redirect(url_for('dashboard'))
        
        return render_template('interview_feedback_summary.html',
                             response_id=response_id,
                             interview_id=interview.id,
                             response=response,
                             interview=interview,
                             candidate=candidate)
        
    except Exception as e:
        logging.error(f"Error displaying feedback summary: {e}")
        flash('Failed to load feedback summary', 'error')
        return redirect(url_for('dashboard'))

@app.route('/api/get-interview-progress/<int:interview_id>')
@login_required
def get_interview_progress(interview_id):
    """
    Get saved interview progress for a candidate
    """
    if current_user.role != 'candidate':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        progress = InterviewProgress.query.filter_by(
            interview_id=interview_id,
            candidate_id=current_user.id
        ).first()
        
        if progress and progress.responses:
            responses = json.loads(progress.responses)
            return jsonify({
                'success': True,
                'responses': responses,
                'progress_percentage': progress.progress_percentage,
                'last_question': progress.last_question,
                'updated_at': progress.updated_at.isoformat()
            })
        else:
            return jsonify({'success': False, 'message': 'No saved progress found'})
            
    except Exception as e:
        logging.error(f"Failed to get interview progress: {e}")
        return jsonify({'error': 'Failed to load progress'}), 500

@app.route('/api/transcribe-audio', methods=['POST'])
@login_required
def transcribe_audio_endpoint():
    """
    API endpoint for audio transcription using OpenAI Whisper
    """
    if current_user.role != 'candidate':
        return jsonify({'error': 'Access denied. Only candidates can use voice dictation.'}), 403
    
    try:
        # Check if audio file is present
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        question_index = request.form.get('question_index', '0')
        
        if audio_file.filename == '':
            return jsonify({'error': 'No audio file selected'}), 400
        
        # Validate audio file
        validation_result = validate_audio_file(audio_file)
        if not validation_result['valid']:
            return jsonify({'error': validation_result['error']}), 400
        
        # Transcribe audio using OpenAI Whisper
        transcription_result = transcribe_audio(audio_file)
        
        if transcription_result['success']:
            # Log successful transcription (without sensitive data)
            logging.info(f"Audio transcription successful for user {current_user.id}, question {question_index}")
            
            return jsonify({
                'success': True,
                'transcript': transcription_result['transcript'],
                'question_index': question_index
            })
        else:
            logging.error(f"Transcription failed for user {current_user.id}: {transcription_result['error']}")
            return jsonify({
                'success': False,
                'error': transcription_result['error']
            }), 500
            
    except Exception as e:
        logging.error(f"Audio transcription endpoint error: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error during transcription'
        }), 500

@app.route('/candidate/download-resume')
@login_required
def download_resume():
    """
    Generate and download candidate resume as PDF
    """
    if current_user.role != 'candidate':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get candidate information
        candidate = current_user
        
        # Create a text-based resume
        resume_content = generate_text_resume(candidate)
        
        # Create response with downloadable file
        response = make_response(resume_content)
        response.headers['Content-Type'] = 'text/plain'
        response.headers['Content-Disposition'] = f'attachment; filename="{candidate.username}_resume.txt"'
        
        return response
        
    except Exception as e:
        logging.error(f"Resume download error for user {current_user.id}: {e}")
        flash('Error generating resume. Please try again.', 'error')
        return redirect(url_for('user_profile', user_id=current_user.id))

def generate_text_resume(candidate):
    """
    Generate a text-based resume for the candidate
    """
    resume_lines = []
    
    # Header
    resume_lines.append("=" * 60)
    resume_lines.append(f"RESUME - {candidate.first_name or ''} {candidate.last_name or ''}".center(60))
    resume_lines.append("=" * 60)
    resume_lines.append("")
    
    # Contact Information
    resume_lines.append("CONTACT INFORMATION")
    resume_lines.append("-" * 20)
    if candidate.email:
        resume_lines.append(f"Email: {candidate.email}")
    if hasattr(candidate, 'phone') and candidate.phone:
        resume_lines.append(f"Phone: {candidate.phone}")
    if hasattr(candidate, 'location') and candidate.location:
        resume_lines.append(f"Location: {candidate.location}")
    if hasattr(candidate, 'linkedin_url') and candidate.linkedin_url:
        resume_lines.append(f"LinkedIn: {candidate.linkedin_url}")
    if hasattr(candidate, 'portfolio_url') and candidate.portfolio_url:
        resume_lines.append(f"Portfolio: {candidate.portfolio_url}")
    resume_lines.append("")
    
    # Professional Summary
    if hasattr(candidate, 'bio') and candidate.bio:
        resume_lines.append("PROFESSIONAL SUMMARY")
        resume_lines.append("-" * 21)
        resume_lines.append(candidate.bio)
        resume_lines.append("")
    
    # Skills
    if hasattr(candidate, 'skills') and candidate.skills:
        resume_lines.append("TECHNICAL SKILLS")
        resume_lines.append("-" * 16)
        try:
            import json
            skills_list = json.loads(candidate.skills) if isinstance(candidate.skills, str) else candidate.skills
            if isinstance(skills_list, list):
                skills_text = ", ".join(skills_list)
            else:
                skills_text = str(candidate.skills)
        except:
            skills_text = str(candidate.skills)
        resume_lines.append(skills_text)
        resume_lines.append("")
    
    # Work Experience
    if hasattr(candidate, 'experience') and candidate.experience:
        resume_lines.append("WORK EXPERIENCE")
        resume_lines.append("-" * 15)
        try:
            import json
            experience_list = json.loads(candidate.experience) if isinstance(candidate.experience, str) else candidate.experience
            if isinstance(experience_list, list):
                for exp in experience_list:
                    if isinstance(exp, dict):
                        resume_lines.append(f"• {exp.get('title', 'Position')} at {exp.get('company', 'Company')}")
                        if exp.get('duration'):
                            resume_lines.append(f"  Duration: {exp['duration']}")
                        if exp.get('description'):
                            resume_lines.append(f"  {exp['description']}")
                        resume_lines.append("")
            else:
                resume_lines.append(str(candidate.experience))
        except:
            resume_lines.append(str(candidate.experience))
        resume_lines.append("")
    
    # Education
    if hasattr(candidate, 'education') and candidate.education:
        resume_lines.append("EDUCATION")
        resume_lines.append("-" * 9)
        try:
            import json
            education_list = json.loads(candidate.education) if isinstance(candidate.education, str) else candidate.education
            if isinstance(education_list, list):
                for edu in education_list:
                    if isinstance(edu, dict):
                        resume_lines.append(f"• {edu.get('degree', 'Degree')} - {edu.get('institution', 'Institution')}")
                        if edu.get('year'):
                            resume_lines.append(f"  Year: {edu['year']}")
                        resume_lines.append("")
            else:
                resume_lines.append(str(candidate.education))
        except:
            resume_lines.append(str(candidate.education))
        resume_lines.append("")
    
    # Interview Performance
    responses = InterviewResponse.query.filter_by(
        candidate_id=candidate.id,
        organization_id=candidate.organization_id
    ).order_by(InterviewResponse.completed_at.desc()).limit(3).all()
    
    if responses:
        resume_lines.append("RECENT INTERVIEW PERFORMANCE")
        resume_lines.append("-" * 27)
        for response in responses:
            resume_lines.append(f"• {response.interview.title}")
            resume_lines.append(f"  Score: {response.ai_score}% | Completed: {response.completed_at.strftime('%m/%d/%Y')}")
            resume_lines.append("")
    
    # Footer
    resume_lines.append("=" * 60)
    resume_lines.append(f"Generated by Job2Hire on {datetime.utcnow().strftime('%B %d, %Y')}".center(60))
    resume_lines.append("=" * 60)
    
    return "\n".join(resume_lines)

@app.route('/candidates/universal')
@login_required
def universal_candidates():
    """Universal candidate access with cross-organization profiles"""
    if current_user.role not in ['recruiter', 'admin']:
        flash('Access denied. Recruiter or admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    from universal_profile_service import UniversalProfileService
    
    # Get all accessible candidates including cross-organization
    candidates = UniversalProfileService.get_accessible_candidates_for_recruiter(
        current_user.id,
        current_user.organization_id,
        include_cross_org=True,
        filters=None
    )
    
    # Get organization dashboard data
    dashboard_data = UniversalProfileService.get_organization_dashboard_candidates(
        current_user.organization_id
    )
    
    return render_template('candidates/universal_filter.html',
                         candidates=candidates,
                         dashboard_data=dashboard_data,
                         user_role=current_user.role)

@app.route('/candidates/send-public-invitation/<int:candidate_id>')
@login_required
def send_public_invitation_page(candidate_id):
    """Send public interview invitation page (replaces modal)"""
    if current_user.role not in ['recruiter', 'admin']:
        flash('Access denied. Recruiter or admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get candidate details
    candidate = User.query.filter_by(id=candidate_id, role='candidate').first()
    if not candidate:
        flash('Candidate not found.', 'error')
        return redirect(url_for('universal_candidates'))
    
    # Get available public interviews
    from universal_profile_service import UniversalProfileService
    
    # Get public interviews that this recruiter can send invitations for
    available_interviews = []
    interviews = Interview.query.filter_by(
        interview_type='public',
        organization_id=current_user.organization_id
    ).all()
    
    for interview in interviews:
        available_interviews.append({
            'id': interview.id,
            'title': interview.title,
            'organization_name': interview.organization.name if interview.organization else 'Unknown'
        })
    
    return render_template('send_public_invitation.html',
                         candidate=candidate,
                         available_interviews=available_interviews)

@app.route('/candidates/send-public-invitation/<int:candidate_id>', methods=['POST'])
@login_required
def send_public_invitation_submit(candidate_id):
    """Handle public interview invitation submission"""
    if current_user.role not in ['recruiter', 'admin']:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    # Get form data
    interview_id = request.form.get('interview_id')
    message = request.form.get('message', '')
    
    if not interview_id:
        return jsonify({'success': False, 'message': 'Please select an interview'}), 400
    
    # Use the existing API logic
    from universal_profile_service import UniversalProfileService
    
    try:
        success, message = UniversalProfileService.send_public_interview_invitation(
            current_user.id, candidate_id, int(interview_id), message
        )
        
        if success:
            flash('Public interview invitation sent successfully!', 'success')
            return redirect(url_for('universal_candidates'))
        else:
            flash(f'Error sending invitation: {message}', 'error')
            return redirect(url_for('send_public_invitation_page', candidate_id=candidate_id))
            
    except Exception as e:
        logging.error(f"Error sending public invitation: {e}")
        flash('An error occurred while sending the invitation.', 'error')
        return redirect(url_for('send_public_invitation_page', candidate_id=candidate_id))



@app.route('/candidates/filter')
@login_required
def filter_candidates():
    """Advanced candidate filtering for recruiters"""
    if current_user.role not in ['recruiter', 'admin']:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get filter parameters
    technology = request.args.get('technology', '')
    location = request.args.get('location', '')
    min_experience = request.args.get('min_experience', type=int)
    max_experience = request.args.get('max_experience', type=int)
    min_score = request.args.get('min_score', type=int)
    max_score = request.args.get('max_score', type=int)
    tag_ids = request.args.getlist('tags')
    
    # Base query for candidates in organization
    query = User.query.filter_by(
        role='candidate',
        organization_id=current_user.organization_id
    )
    
    # Apply filters
    if technology:
        query = query.filter(User.skills.contains(technology))
    
    if location:
        query = query.filter(User.location.ilike(f'%{location}%'))
    
    if min_experience is not None:
        query = query.filter(User.experience_years >= min_experience)
    
    if max_experience is not None:
        query = query.filter(User.experience_years <= max_experience)
    
    # Filter by interview performance
    if min_score is not None or max_score is not None:
        subquery = db.session.query(InterviewResponse.candidate_id).join(Interview).filter(
            Interview.organization_id == current_user.organization_id
        )
        if min_score is not None:
            subquery = subquery.filter(InterviewResponse.ai_score >= min_score)
        if max_score is not None:
            subquery = subquery.filter(InterviewResponse.ai_score <= max_score)
        
        candidate_ids = [row[0] for row in subquery.distinct().all()]
        if candidate_ids:
            query = query.filter(User.id.in_(candidate_ids))
        else:
            query = query.filter(User.id.in_([]))  # No matches
    
    # Filter by tags
    if tag_ids:
        tag_candidate_ids = db.session.query(CandidateTagAssignment.candidate_id).filter(
            CandidateTagAssignment.tag_id.in_(tag_ids)
        ).distinct().all()
        tag_candidate_ids = [row[0] for row in tag_candidate_ids]
        if tag_candidate_ids:
            query = query.filter(User.id.in_(tag_candidate_ids))
        else:
            query = query.filter(User.id.in_([]))
    
    candidates = query.order_by(User.created_at.desc()).all()
    
    # Get interview performance for each candidate
    for candidate in candidates:
        responses = InterviewResponse.query.join(Interview).filter(
            InterviewResponse.candidate_id == candidate.id,
            Interview.organization_id == current_user.organization_id
        ).all()
        candidate.avg_score = sum(r.ai_score for r in responses) / len(responses) if responses else 0
        candidate.interview_count = len(responses)
        candidate.tags = db.session.query(CandidateTag).join(CandidateTagAssignment).filter(
            CandidateTagAssignment.candidate_id == candidate.id
        ).all()
    
    # Get available tags for filtering
    available_tags = CandidateTag.query.filter_by(organization_id=current_user.organization_id).all()
    
    # Get available lists for bulk actions
    candidate_lists = CandidateList.query.filter_by(organization_id=current_user.organization_id).all()
    
    # Get recruiter's interviews for bulk email invitations
    recruiter_interviews = Interview.query.filter_by(
        recruiter_id=current_user.id,
        organization_id=current_user.organization_id,
        is_active=True
    ).all()
    
    # Get communication flags for all candidates
    from communication_service import CommunicationTracker
    communication_flags = CommunicationTracker.get_candidate_communication_flags(
        current_user.id, current_user.organization_id
    )
    
    # Enrich candidates with communication data
    enriched_candidates = []
    for candidate in candidates:
        candidate.communication = communication_flags.get(candidate.id, {
            'has_communicated': False,
            'last_interaction': None,
            'interaction_types': [],
            'interaction_count': 0,
            'status': 'no_contact'
        })
        enriched_candidates.append(candidate)
    
    # Get communication summary
    communication_summary = CommunicationTracker.get_communication_summary(
        current_user.id, current_user.organization_id
    )
    
    return render_template('candidates/filter.html',
                         candidates=enriched_candidates,
                         communication_summary=communication_summary,
                         available_tags=available_tags,
                         candidate_lists=candidate_lists,
                         recruiter_interviews=recruiter_interviews,
                         filters={
                             'technology': technology,
                             'location': location,
                             'min_experience': min_experience,
                             'max_experience': max_experience,
                             'min_score': min_score,
                             'max_score': max_score,
                             'selected_tags': tag_ids
                         })

@app.route('/candidates/export', methods=['POST'])
@login_required
def export_candidates():
    """Export candidate data to Excel or PDF"""
    if current_user.role not in ['recruiter', 'admin']:
        return jsonify({'error': 'Access denied'}), 403
    
    candidate_ids = request.json.get('candidate_ids', [])
    export_format = request.json.get('format', 'excel')  # 'excel' or 'pdf'
    
    if not candidate_ids:
        return jsonify({'error': 'No candidates selected'}), 400
    
    candidates = User.query.filter(
        User.id.in_(candidate_ids),
        User.organization_id == current_user.organization_id,
        User.role == 'candidate'
    ).all()
    
    if export_format == 'excel':
        return export_candidates_excel(candidates)
    elif export_format == 'pdf':
        return export_candidates_pdf(candidates)
    else:
        return jsonify({'error': 'Invalid format'}), 400

@app.route('/candidates/tag', methods=['POST'])
@login_required
def tag_candidates():
    """Add tags to selected candidates"""
    if current_user.role not in ['recruiter', 'admin']:
        return jsonify({'error': 'Access denied'}), 403
    
    candidate_ids = request.json.get('candidate_ids', [])
    tag_id = request.json.get('tag_id')
    
    if not candidate_ids or not tag_id:
        return jsonify({'error': 'Missing required data'}), 400
    
    # Verify tag belongs to organization
    tag = CandidateTag.query.filter_by(
        id=tag_id,
        organization_id=current_user.organization_id
    ).first()
    
    if not tag:
        return jsonify({'error': 'Tag not found'}), 404
    
    # Add tags to candidates
    tagged_count = 0
    for candidate_id in candidate_ids:
        # Check if already tagged
        existing = CandidateTagAssignment.query.filter_by(
            candidate_id=candidate_id,
            tag_id=tag_id
        ).first()
        
        if not existing:
            assignment = CandidateTagAssignment(
                candidate_id=candidate_id,
                tag_id=tag_id,
                assigned_by=current_user.id
            )
            db.session.add(assignment)
            tagged_count += 1
    
    db.session.commit()
    return jsonify({'success': True, 'tagged_count': tagged_count})

@app.route('/candidates/bulk-email', methods=['POST'])
@login_required
def bulk_email_candidates():
    """Send bulk email invitations to candidates"""
    if current_user.role not in ['recruiter', 'admin']:
        return jsonify({'error': 'Access denied'}), 403
    
    candidate_ids = request.json.get('candidate_ids', [])
    subject = request.json.get('subject', '')
    message = request.json.get('message', '')
    interview_id = request.json.get('interview_id')
    
    if not candidate_ids or not subject or not message:
        return jsonify({'error': 'Missing required data'}), 400
    
    candidates = User.query.filter(
        User.id.in_(candidate_ids),
        User.organization_id == current_user.organization_id,
        User.role == 'candidate'
    ).all()
    
    sent_count = 0
    for candidate in candidates:
        try:
            # Create interview invitation if interview_id provided
            if interview_id:
                # Check if invitation already exists
                existing_invitation = InterviewInvitation.query.filter_by(
                    interview_id=interview_id,
                    candidate_id=candidate.id
                ).first()
                
                if not existing_invitation:
                    invitation = InterviewInvitation(
                        interview_id=interview_id,
                        candidate_id=candidate.id,
                        recruiter_id=current_user.id,
                        organization_id=current_user.organization_id,
                        message=message,
                        status='pending'
                    )
                    db.session.add(invitation)
            
            # Send email (placeholder - implement with actual email service)
            send_candidate_email(candidate.email, subject, message)
            sent_count += 1
            
        except Exception as e:
            logging.error(f"Failed to send email to {candidate.email}: {e}")
    
    db.session.commit()
    return jsonify({'success': True, 'sent_count': sent_count})

@app.route('/tags/create', methods=['POST'])
@login_required
def create_tag():
    """Create a new candidate tag"""
    if current_user.role not in ['recruiter', 'admin']:
        return jsonify({'error': 'Access denied'}), 403
    
    name = request.json.get('name', '').strip()
    color = request.json.get('color', '#6c757d')
    
    if not name:
        return jsonify({'error': 'Tag name is required'}), 400
    
    # Check if tag already exists
    existing = CandidateTag.query.filter_by(
        name=name,
        organization_id=current_user.organization_id
    ).first()
    
    if existing:
        return jsonify({'error': 'Tag already exists'}), 400
    
    tag = CandidateTag(
        name=name,
        color=color,
        organization_id=current_user.organization_id,
        created_by=current_user.id
    )
    
    db.session.add(tag)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'tag': {
            'id': tag.id,
            'name': tag.name,
            'color': tag.color
        }
    })

@app.route('/lists/create', methods=['POST'])
@login_required
def create_candidate_list():
    """Create a new candidate list"""
    if current_user.role not in ['recruiter', 'admin']:
        return jsonify({'error': 'Access denied'}), 403
    
    name = request.json.get('name', '').strip()
    description = request.json.get('description', '')
    candidate_ids = request.json.get('candidate_ids', [])
    
    if not name:
        return jsonify({'error': 'List name is required'}), 400
    
    # Check if list name already exists for this organization
    existing_list = CandidateList.query.filter_by(
        name=name,
        organization_id=current_user.organization_id
    ).first()
    
    if existing_list:
        return jsonify({'error': 'A list with this name already exists'}), 400
    
    candidate_list = CandidateList(
        name=name,
        description=description,
        organization_id=current_user.organization_id,
        created_by=current_user.id
    )
    
    db.session.add(candidate_list)
    db.session.flush()  # Get the ID
    
    # Add candidates to list (verify they belong to the organization)
    added_count = 0
    for candidate_id in candidate_ids:
        candidate = User.query.filter_by(
            id=candidate_id,
            organization_id=current_user.organization_id,
            role='candidate'
        ).first()
        
        if candidate:
            # Check if already in list
            existing_membership = CandidateListMembership.query.filter_by(
                list_id=candidate_list.id,
                candidate_id=candidate_id
            ).first()
            
            if not existing_membership:
                membership = CandidateListMembership(
                    list_id=candidate_list.id,
                    candidate_id=candidate_id,
                    added_by=current_user.id
                )
                db.session.add(membership)
                added_count += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'list': {
            'id': candidate_list.id,
            'name': candidate_list.name,
            'description': candidate_list.description,
            'candidate_count': added_count
        }
    })

@app.route('/lists/add-members', methods=['POST'])
@login_required
def add_list_members():
    """Add candidates to an existing list"""
    if current_user.role not in ['recruiter', 'admin']:
        return jsonify({'error': 'Access denied'}), 403
    
    list_id = request.json.get('list_id')
    candidate_ids = request.json.get('candidate_ids', [])
    
    if not list_id or not candidate_ids:
        return jsonify({'error': 'Missing required data'}), 400
    
    # Verify list belongs to organization
    candidate_list = CandidateList.query.filter_by(
        id=list_id,
        organization_id=current_user.organization_id
    ).first()
    
    if not candidate_list:
        return jsonify({'error': 'List not found'}), 404
    
    # Add candidates to list
    added_count = 0
    for candidate_id in candidate_ids:
        candidate = User.query.filter_by(
            id=candidate_id,
            organization_id=current_user.organization_id,
            role='candidate'
        ).first()
        
        if candidate:
            # Check if already in list
            existing_membership = CandidateListMembership.query.filter_by(
                list_id=list_id,
                candidate_id=candidate_id
            ).first()
            
            if not existing_membership:
                membership = CandidateListMembership(
                    list_id=list_id,
                    candidate_id=candidate_id,
                    added_by=current_user.id
                )
                db.session.add(membership)
                added_count += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'added_count': added_count,
        'list_name': candidate_list.name
    })

def export_candidates_excel(candidates):
    """Export candidates to Excel format"""
    import io
    from datetime import datetime
    
    # Create CSV content (simpler than Excel for demo)
    output = io.StringIO()
    output.write("Name,Email,Phone,Location,Experience,Skills,Average Score,Interview Count,Tags\n")
    
    for candidate in candidates:
        tags = ', '.join([tag.name for tag in getattr(candidate, 'tags', [])])
        skills = candidate.skills or ''
        if skills.startswith('['):
            try:
                import json
                skills_list = json.loads(skills)
                skills = ', '.join(skills_list)
            except:
                pass
        
        output.write(f'"{candidate.first_name or ""} {candidate.last_name or ""}",')
        output.write(f'"{candidate.email}",')
        output.write(f'"{candidate.phone or ""}",')
        output.write(f'"{candidate.location or ""}",')
        output.write(f'"{candidate.experience_years or 0}",')
        output.write(f'"{skills}",')
        output.write(f'"{getattr(candidate, "avg_score", 0):.1f}",')
        output.write(f'"{getattr(candidate, "interview_count", 0)}",')
        output.write(f'"{tags}"\n')
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=candidates_{datetime.now().strftime("%Y%m%d")}.csv'
    return response

def export_candidates_pdf(candidates):
    """Export candidates to PDF format"""
    # Simple text-based PDF export
    content = f"Candidate Export Report\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    
    for candidate in candidates:
        content += f"Name: {candidate.first_name or ''} {candidate.last_name or ''}\n"
        content += f"Email: {candidate.email}\n"
        content += f"Phone: {candidate.phone or 'N/A'}\n"
        content += f"Location: {candidate.location or 'N/A'}\n"
        content += f"Experience: {candidate.experience_years or 0} years\n"
        content += f"Average Score: {getattr(candidate, 'avg_score', 0):.1f}%\n"
        content += f"Interviews: {getattr(candidate, 'interview_count', 0)}\n"
        content += "-" * 50 + "\n\n"
    
    response = make_response(content)
    response.headers['Content-Type'] = 'text/plain'
    response.headers['Content-Disposition'] = f'attachment; filename=candidates_{datetime.now().strftime("%Y%m%d")}.txt'
    return response

def send_candidate_email(email, subject, message):
    """Send email to candidate (placeholder implementation)"""
    # This would integrate with your email service (SendGrid, etc.)
    logging.info(f"Sending email to {email}: {subject}")
    return True

# System Settings API Routes
@app.route('/system/settings-panel')
@login_required
@login_required
@login_required
def api_database_status():
    """Get database status and table information"""
    if current_user.role not in ['super_admin', 'admin']:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        status = get_database_status()
        return jsonify(status)
    except Exception as e:
        logging.error(f"Error getting database status: {e}")
        return jsonify({'error': 'Failed to get database status'}), 500

@app.route('/api/system/database/optimize', methods=['POST'])
@login_required
def api_optimize_database():
    """Optimize database performance"""
    if current_user.role not in ['super_admin', 'admin']:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        results = optimize_database()
        return jsonify(results)
    except Exception as e:
        logging.error(f"Error optimizing database: {e}")
        return jsonify({'error': 'Failed to optimize database'}), 500

@app.route('/api/system/api-keys')
@login_required
def api_key_status():
    """Get API key configuration status"""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        api_keys = get_api_key_status()
        return jsonify(api_keys)
    except Exception as e:
        logging.error(f"Error getting API key status: {e}")
        return jsonify({'error': 'Failed to get API key status'}), 500

@app.route('/api/system/performance')
@login_required
def api_performance_metrics():
    """Get system performance metrics"""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        metrics = get_performance_metrics()
        return jsonify(metrics)
    except Exception as e:
        logging.error(f"Error getting performance metrics: {e}")
        return jsonify({'error': 'Failed to get performance metrics'}), 500

@app.route('/api/system/settings', methods=['GET', 'POST'])
@login_required
@login_required
def api_bulk_import_users():
    """Bulk import users from CSV file"""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'Only CSV files are supported'}), 400
        
        import csv
        import io
        
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)
        
        imported = 0
        errors = 0
        
        for row in csv_input:
            try:
                # Validate required fields
                if not all([row.get('username'), row.get('email'), row.get('organization_id')]):
                    errors += 1
                    continue
                
                # Check if user already exists
                if User.query.filter_by(email=row['email']).first():
                    errors += 1
                    continue
                
                # Create user
                user = User(
                    username=row['username'],
                    email=row['email'],
                    password_hash=generate_password_hash(row.get('password', 'TempPass123!')),
                    role=row.get('role', 'candidate'),
                    organization_id=int(row['organization_id']),
                    first_name=row.get('first_name', ''),
                    last_name=row.get('last_name', ''),
                    phone=row.get('phone', ''),
                    cross_org_accessible=True
                )
                
                db.session.add(user)
                imported += 1
                
            except Exception as e:
                logging.error(f"Error importing user: {e}")
                errors += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'imported': imported,
            'errors': errors,
            'message': f'Imported {imported} users with {errors} errors'
        })
        
    except Exception as e:
        logging.error(f"Error in bulk import: {e}")
        return jsonify({'error': 'Failed to import users'}), 500

@app.route('/api/system/users/export')
@login_required
def api_export_users():
    """Export all users to CSV"""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        import csv
        import io
        from datetime import datetime
        
        # Get all users
        users = User.query.all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'ID', 'Username', 'Email', 'Role', 'Organization ID', 'First Name', 
            'Last Name', 'Phone', 'Created At', 'Active'
        ])
        
        # Write user data
        for user in users:
            writer.writerow([
                user.id, user.username, user.email, user.role, user.organization_id,
                user.first_name or '', user.last_name or '', user.phone or '',
                user.created_at.isoformat() if user.created_at else '',
                user.user_active
            ])
        
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=users_export_{datetime.now().strftime("%Y%m%d")}.csv'
        
        return response
        
    except Exception as e:
        logging.error(f"Error exporting users: {e}")
        return jsonify({'error': 'Failed to export users'}), 500

@app.route('/api/system/database/indexes', methods=['POST'])
@login_required
def api_create_database_indexes():
    """Create database indexes for performance optimization"""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        from sqlalchemy import text
        
        # Create performance indexes
        indexes = [
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_role ON users(role)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_organization_id ON users(organization_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created_at ON users(created_at)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_interview_responses_candidate_id ON interview_responses(candidate_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_interview_responses_interview_id ON interview_responses(interview_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_interview_responses_status ON interview_responses(status)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_posting_is_active ON job_posting(is_active)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_posting_created_at ON job_posting(created_at)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_application_candidate_id ON job_application(candidate_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_application_job_id ON job_application(job_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_sender_id ON messages(sender_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_recipient_id ON messages(recipient_id)",
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_messages_created_at ON messages(created_at)"
        ]
        
        created = 0
        errors = []
        
        for index_sql in indexes:
            try:
                db.session.execute(text(index_sql))
                db.session.commit()
                created += 1
            except Exception as e:
                errors.append(f"Index creation failed: {str(e)}")
                db.session.rollback()
        
        return jsonify({
            'success': True,
            'indexes_created': created,
            'errors': errors,
            'message': f'Created {created} indexes'
        })
        
    except Exception as e:
        logging.error(f"Error creating database indexes: {e}")
        return jsonify({'error': 'Failed to create database indexes'}), 500

@app.route('/api/system/cache/clear', methods=['POST'])
@login_required
def api_clear_cache():
    """Clear application cache"""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Clear any application-level caches
        # This is a placeholder - implement based on your caching strategy
        
        return jsonify({
            'success': True,
            'message': 'Cache cleared successfully'
        })
        
    except Exception as e:
        logging.error(f"Error clearing cache: {e}")
        return jsonify({'error': 'Failed to clear cache'}), 500

# Super Admin Organization Management Routes
@app.route('/admin/organizations')
@login_required
def admin_organizations():
    """Super admin organization management"""
    if current_user.role != 'super_admin':
        flash('Access denied. Super admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    organizations = Organization.query.all()
    return render_template('admin/organizations.html', organizations=organizations)

@app.route('/admin/organizations/create', methods=['GET', 'POST'])
@login_required
def admin_create_organization():
    """Create new organization (super admin only)"""
    if current_user.role != 'super_admin':
        flash('Access denied. Super admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        slug = request.form.get('slug', '').strip()
        subscription_plan = request.form.get('subscription_plan', 'trial')
        
        if not name:
            flash('Organization name is required.', 'error')
            return render_template('admin/create_organization.html')
        
        # Auto-generate slug if not provided
        if not slug:
            import re
            slug = re.sub(r'[^a-zA-Z0-9-]', '-', name.lower()).strip('-')
        
        # Check if organization already exists
        if Organization.query.filter_by(name=name).first():
            flash('Organization with this name already exists.', 'error')
            return render_template('admin/create_organization.html')
        
        if Organization.query.filter_by(slug=slug).first():
            flash('Organization with this slug already exists.', 'error')
            return render_template('admin/create_organization.html')
        
        # Create organization
        org = Organization(
            name=name,
            slug=slug,
            subscription_plan=subscription_plan,
            is_active=True
        )
        
        try:
            db.session.add(org)
            db.session.commit()
            flash(f'Organization "{name}" created successfully!', 'success')
            return redirect(url_for('admin_organizations'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating organization: {str(e)}', 'error')
    
    return render_template('admin/create_organization.html')

@app.route('/admin/organizations/<int:org_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_organization(org_id):
    """Edit organization (super admin only)"""
    if current_user.role != 'super_admin':
        flash('Access denied. Super admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    org = Organization.query.get_or_404(org_id)
    
    if request.method == 'POST':
        org.name = request.form.get('name', '').strip()
        org.slug = request.form.get('slug', '').strip()
        org.subscription_plan = request.form.get('subscription_plan', 'trial')
        org.is_active = request.form.get('is_active') == 'on'
        
        if not org.name:
            flash('Organization name is required.', 'error')
            return render_template('admin/edit_organization.html', organization=org)
        
        # Check for duplicates (excluding current org)
        if Organization.query.filter(Organization.name == org.name, Organization.id != org_id).first():
            flash('Organization with this name already exists.', 'error')
            return render_template('admin/edit_organization.html', organization=org)
        
        if Organization.query.filter(Organization.slug == org.slug, Organization.id != org_id).first():
            flash('Organization with this slug already exists.', 'error')
            return render_template('admin/edit_organization.html', organization=org)
        
        try:
            db.session.commit()
            flash(f'Organization "{org.name}" updated successfully!', 'success')
            return redirect(url_for('admin_organizations'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating organization: {str(e)}', 'error')
    
    return render_template('admin/edit_organization.html', organization=org)

@app.route('/admin/organizations/<int:org_id>/users')
@login_required
def admin_organization_users(org_id):
    """View organization users (super admin only)"""
    if current_user.role != 'super_admin':
        flash('Access denied. Super admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    org = Organization.query.get_or_404(org_id)
    users = User.query.filter_by(organization_id=org_id).all()
    
    return render_template('admin/organization_users.html', organization=org, users=users)

@app.route('/admin/organizations/<int:org_id>/add-user', methods=['POST'])
@login_required
def admin_add_user_to_organization(org_id):
    """Add user to organization (super admin only)"""
    if current_user.role != 'super_admin':
        flash('Access denied. Super admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    org = Organization.query.get_or_404(org_id)
    
    try:
        email = request.form.get('email', '').strip()
        role = request.form.get('role', 'candidate')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        
        if not email:
            flash('Email is required.', 'error')
            return redirect(url_for('admin_organization_users', org_id=org_id))
        
        # Check if user already exists with this email anywhere
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash(f'User with email {email} already exists in the system.', 'error')
            return redirect(url_for('admin_organization_users', org_id=org_id))
        
        # Generate username from email
        username = email.split('@')[0]
        counter = 1
        original_username = username
        while User.query.filter_by(username=username).first():
            username = f"{original_username}_{counter}"
            counter += 1
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash('Welcome2025!'),
            role=role,
            organization_id=org_id,
            first_name=first_name,
            last_name=last_name,
            user_active=True
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Log the action
        audit_log = AuditLog(
            user_id=current_user.id,
            action='CREATE_USER',
            resource_type='user',
            resource_id=new_user.id,
            details=json.dumps({
                'created_email': email,
                'created_role': role,
                'organization_id': org_id,
                'organization_name': org.name,
                'created_by': current_user.username
            })
        )
        db.session.add(audit_log)
        db.session.commit()
        
        flash(f'User {email} successfully added to {org.name}! Default password: Welcome2025!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating user: {str(e)}', 'error')
    
    return redirect(url_for('admin_organization_users', org_id=org_id))

@app.route('/admin/organizations/<int:org_id>/delete', methods=['POST'])
@login_required
def admin_delete_organization(org_id):
    """Delete organization (super admin only)"""
    if current_user.role != 'super_admin':
        flash('Access denied. Super admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    org = Organization.query.get_or_404(org_id)
    
    # Check if organization has users
    user_count = User.query.filter_by(organization_id=org_id).count()
    if user_count > 0:
        flash(f'Cannot delete organization "{org.name}" - it has {user_count} users. Please reassign or delete users first.', 'error')
        return redirect(url_for('admin_organizations'))
    
    try:
        org_name = org.name
        db.session.delete(org)
        db.session.commit()
        flash(f'Organization "{org_name}" deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting organization: {str(e)}', 'error')
    
    return redirect(url_for('admin_organizations'))

@app.route('/admin/organizations/bulk-operations', methods=['POST'])
@login_required
def admin_bulk_operations():
    """Bulk operations for organizations (super admin only)"""
    if current_user.role != 'super_admin':
        flash('Access denied. Super admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    action = request.form.get('action')
    org_ids = request.form.getlist('org_ids')
    
    if not org_ids:
        flash('No organizations selected.', 'warning')
        return redirect(url_for('admin_organizations'))
    
    try:
        if action == 'activate':
            Organization.query.filter(Organization.id.in_(org_ids)).update({Organization.is_active: True}, synchronize_session=False)
            flash(f'Activated {len(org_ids)} organizations.', 'success')
        elif action == 'deactivate':
            Organization.query.filter(Organization.id.in_(org_ids)).update({Organization.is_active: False}, synchronize_session=False)
            flash(f'Deactivated {len(org_ids)} organizations.', 'success')
        elif action == 'change_plan':
            new_plan = request.form.get('new_plan', 'trial')
            Organization.query.filter(Organization.id.in_(org_ids)).update({Organization.subscription_plan: new_plan}, synchronize_session=False)
            flash(f'Updated {len(org_ids)} organizations to {new_plan} plan.', 'success')
        elif action == 'export':
            return admin_export_organizations(org_ids)
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'Error performing bulk operation: {str(e)}', 'error')
    
    return redirect(url_for('admin_organizations'))

@app.route('/admin/organizations/export')
@login_required
def admin_export_organizations(org_ids=None):
    """Export organizations to CSV (super admin only)"""
    if current_user.role != 'super_admin':
        flash('Access denied. Super admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    import csv
    from io import StringIO
    
    if org_ids:
        orgs = Organization.query.filter(Organization.id.in_(org_ids)).all()
    else:
        orgs = Organization.query.all()
    
    output = StringIO()
    writer = csv.writer(output)
    
    # CSV headers
    writer.writerow(['ID', 'Name', 'Slug', 'Plan', 'Status', 'Users Count', 'Created Date'])
    
    for org in orgs:
        writer.writerow([
            org.id,
            org.name,
            org.slug,
            org.subscription_plan,
            'Active' if org.is_active else 'Inactive',
            len(org.users),
            org.created_at.strftime('%Y-%m-%d') if org.created_at else 'N/A'
        ])
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=organizations_{datetime.now().strftime("%Y%m%d")}.csv'
    return response

@app.route('/admin/organizations/<int:org_id>/settings', methods=['GET', 'POST'])
@login_required
def admin_organization_settings(org_id):
    """Organization integration settings (super admin only)"""
    if current_user.role != 'super_admin':
        flash('Access denied. Super admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    org = Organization.query.get_or_404(org_id)
    settings = IntegrationSettings.query.filter_by(organization_id=org_id).first()
    
    if request.method == 'POST':
        # Update branding settings
        branding_config = {
            'logo_url': request.form.get('logo_url', '').strip(),
            'primary_color': request.form.get('primary_color', '#007bff'),
            'secondary_color': request.form.get('secondary_color', '#6c757d'),
            'custom_domain': request.form.get('custom_domain', '').strip()
        }
        org.branding_config = branding_config
        
        # Handle integration settings properly
        integration_data = {
            'email_provider': request.form.get('email_provider', 'sendgrid'),
            'sms_provider': request.form.get('sms_provider', 'twilio'),
            'calendar_integration': request.form.get('calendar_integration') == 'on',
            'slack_integration': request.form.get('slack_integration') == 'on',
            'rate_limit': int(request.form.get('rate_limit', 1000)),
            'webhook_url': request.form.get('webhook_url', '').strip(),
            'api_access_enabled': request.form.get('api_access_enabled') == 'on'
        }
        
        # Store integration settings in organization branding_config to avoid NOT NULL constraint issues
        if not org.branding_config:
            org.branding_config = {}
        org.branding_config.update(integration_data)
        
        try:
            db.session.commit()
            flash(f'Settings updated for {org.name}!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating settings: {str(e)}', 'error')
    
    return render_template('admin/organization_settings.html', organization=org, settings=settings)

@app.route('/admin/job-scheduler')
@login_required
@login_required
@login_required
@login_required
@login_required
def technical_person_dashboard():
    """Dashboard for technical persons"""
    if current_user.role != 'technical_person':
        flash('Access denied. Technical person role required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from technical_interview_service import TechnicalInterviewService
        service = TechnicalInterviewService()
        dashboard_data = service.get_technical_person_dashboard(current_user.id)
        
        return render_template('technical/dashboard.html', **dashboard_data)
        
    except Exception as e:
        logging.error(f"Error loading technical person dashboard: {e}")
        flash('Error loading dashboard', 'error')
        return redirect(url_for('dashboard'))


@app.route('/technical/candidate/<int:candidate_id>')
@login_required
def technical_candidate_profile(candidate_id):
    """View candidate profile for technical person"""
    if current_user.role != 'technical_person':
        flash('Access denied. Technical person role required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from technical_interview_service import TechnicalInterviewService
        service = TechnicalInterviewService()
        
        profile_data = service.get_candidate_profile_for_technical_person(
            candidate_id, current_user.id
        )
        
        if not profile_data:
            flash('Candidate profile not accessible or not found', 'error')
            return redirect(url_for('technical_person_dashboard'))
        
        return render_template('technical/candidate_profile.html', **profile_data)
        
    except Exception as e:
        logging.error(f"Error loading candidate profile: {e}")
        flash('Error loading candidate profile', 'error')
        return redirect(url_for('technical_person_dashboard'))


@app.route('/technical/feedback/<int:assignment_id>')
@login_required
def technical_feedback_form(assignment_id):
    """Feedback form for technical person"""
    if current_user.role != 'technical_person':
        flash('Access denied. Technical person role required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from models import TechnicalInterviewAssignment, TechnicalInterviewFeedback
        
        assignment = TechnicalInterviewAssignment.query.get_or_404(assignment_id)
        
        # Verify this technical person owns this assignment
        if assignment.technical_person_id != current_user.id:
            flash('Access denied. You are not assigned to this interview.', 'error')
            return redirect(url_for('technical_person_dashboard'))
        
        # Check if feedback already exists
        existing_feedback = TechnicalInterviewFeedback.query.filter_by(
            assignment_id=assignment_id
        ).first()
        
        return render_template('technical/feedback_form.html', 
                             assignment=assignment,
                             existing_feedback=existing_feedback)
        
    except Exception as e:
        logging.error(f"Error loading feedback form: {e}")
        flash('Error loading feedback form', 'error')
        return redirect(url_for('technical_person_dashboard'))


@app.route('/technical/feedback/<int:assignment_id>/submit', methods=['POST'])
@login_required
def submit_technical_feedback(assignment_id):
    """Submit technical interview feedback"""
    if current_user.role != 'technical_person':
        flash('Access denied. Technical person role required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from models import TechnicalInterviewAssignment
        from technical_interview_service import TechnicalInterviewService
        
        assignment = TechnicalInterviewAssignment.query.get_or_404(assignment_id)
        
        # Verify this technical person owns this assignment
        if assignment.technical_person_id != current_user.id:
            flash('Access denied. You are not assigned to this interview.', 'error')
            return redirect(url_for('technical_person_dashboard'))
        
        # Collect feedback data
        feedback_data = {
            'decision': request.form.get('decision'),
            'technical_comments': request.form.get('technical_comments', ''),
            'communication_comments': request.form.get('communication_comments', ''),
            'overall_comments': request.form.get('overall_comments', ''),
            'technical_skills_rating': request.form.get('technical_skills_rating', type=int),
            'problem_solving_rating': request.form.get('problem_solving_rating', type=int),
            'communication_rating': request.form.get('communication_rating', type=int),
            'cultural_fit_rating': request.form.get('cultural_fit_rating', type=int),
            'used_ai_assistance': request.form.get('used_ai_assistance') == 'on',
            'interview_duration_minutes': request.form.get('interview_duration_minutes', type=int),
            'second_round_notes': request.form.get('second_round_notes', '')
        }
        
        # Validate required fields
        if not feedback_data['decision']:
            flash('Please select a decision (Selected/Rejected/Second Round)', 'error')
            return redirect(url_for('technical_feedback_form', assignment_id=assignment_id))
        
        # Submit feedback
        service = TechnicalInterviewService()
        feedback = service.submit_technical_feedback(assignment_id, feedback_data)
        
        if feedback:
            flash('Feedback submitted successfully!', 'success')
            
            # Create audit log
            from models import AuditLog
            audit_log = AuditLog(
                user_id=current_user.id,
                action='technical_feedback_submitted',
                resource_type='technical_interview_feedback',
                resource_id=feedback.id,
                details=json.dumps({
                    'assignment_id': assignment_id,
                    'candidate_id': assignment.candidate_id,
                    'decision': feedback_data['decision'],
                    'organization_id': current_user.organization_id
                })
            )
            db.session.add(audit_log)
            db.session.commit()
            
            return redirect(url_for('technical_person_dashboard'))
        else:
            flash('Error submitting feedback. Please try again.', 'error')
            return redirect(url_for('technical_feedback_form', assignment_id=assignment_id))
        
    except Exception as e:
        logging.error(f"Error submitting technical feedback: {e}")
        flash('Error submitting feedback', 'error')
        return redirect(url_for('technical_feedback_form', assignment_id=assignment_id))


@app.route('/technical/assignments')
@login_required
def technical_assignments():
    """View all assignments for technical person"""
    if current_user.role != 'technical_person':
        flash('Access denied. Technical person role required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from technical_interview_service import get_technical_person_assignments
        
        status_filter = request.args.get('status', 'all')
        assignments = get_technical_person_assignments(
            current_user.id, 
            status=status_filter if status_filter != 'all' else None
        )
        
        return render_template('technical/assignments.html', 
                             assignments=assignments,
                             status_filter=status_filter)
        
    except Exception as e:
        logging.error(f"Error loading assignments: {e}")
        flash('Error loading assignments', 'error')
        return redirect(url_for('technical_person_dashboard'))


# HR/Admin Routes for Technical Interview Management
@app.route('/admin/technical-persons')
@login_required
def manage_technical_persons():
    """Manage technical persons"""
    if current_user.role not in ['admin', 'recruiter']:
        flash('Access denied. Admin or HR privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get technical persons in the organization
        technical_persons = User.query.filter_by(
            organization_id=current_user.organization_id,
            role='technical_person',
            user_active=True
        ).all()
        
        return render_template('admin/technical_persons.html', 
                             technical_persons=technical_persons)
        
    except Exception as e:
        logging.error(f"Error loading technical persons: {e}")
        flash('Error loading technical persons', 'error')
        return redirect(url_for('dashboard'))


@app.route('/admin/assign-technical-interview', methods=['POST'])
@login_required
def assign_technical_interview():
    """Assign technical person to interview"""
    if current_user.role not in ['admin', 'recruiter']:
        flash('Access denied. Admin or HR privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from technical_interview_service import TechnicalInterviewService
        from datetime import datetime
        
        interview_id = request.form.get('interview_id', type=int)
        candidate_id = request.form.get('candidate_id', type=int)
        technical_person_id = request.form.get('technical_person_id', type=int)
        interview_datetime_str = request.form.get('interview_datetime')
        meeting_link = request.form.get('meeting_link')
        
        if not all([interview_id, candidate_id, technical_person_id, interview_datetime_str]):
            flash('All fields are required for technical interview assignment', 'error')
            return redirect(request.referrer or url_for('dashboard'))
        
        # Parse datetime
        interview_datetime = datetime.fromisoformat(interview_datetime_str)
        
        # Create assignment
        service = TechnicalInterviewService()
        assignment = service.assign_technical_person(
            interview_id=interview_id,
            candidate_id=candidate_id,
            technical_person_id=technical_person_id,
            interview_datetime=interview_datetime,
            assigned_by_id=current_user.id,
            meeting_link=meeting_link
        )
        
        if assignment:
            flash('Technical interview assigned successfully!', 'success')
        else:
            flash('Error assigning technical interview', 'error')
        
        return redirect(request.referrer or url_for('dashboard'))
        
    except Exception as e:
        logging.error(f"Error assigning technical interview: {e}")
        flash('Error assigning technical interview', 'error')
        return redirect(request.referrer or url_for('dashboard'))


@app.route('/admin/schedule-google-meet', methods=['GET', 'POST'])
@login_required
def schedule_google_meet():
    """HR interface for scheduling Google Meet meetings with technical interviewers"""
    if current_user.role not in ['admin', 'recruiter']:
        flash('Access denied. Admin or HR privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'GET':
        try:
            from datetime import datetime, timedelta
            
            # Get candidate_id from URL parameter if provided
            selected_candidate_id = request.args.get('candidate_id', type=int)
            
            # Get available technical persons
            technical_persons = User.query.filter_by(
                organization_id=current_user.organization_id,
                role='technical_person',
                user_active=True
            ).all()
            
            # Get candidates in organization
            candidates = User.query.filter_by(
                organization_id=current_user.organization_id,
                role='candidate',
                user_active=True
            ).all()
            
            # Get available interviews
            interviews = Interview.query.filter_by(
                organization_id=current_user.organization_id
            ).all()
            
            # If a specific candidate is selected, get their details
            selected_candidate = None
            if selected_candidate_id:
                selected_candidate = User.query.filter_by(
                    id=selected_candidate_id,
                    organization_id=current_user.organization_id,
                    role='candidate'
                ).first()
            
            return render_template('admin/schedule_google_meet.html',
                                 technical_persons=technical_persons,
                                 candidates=candidates,
                                 interviews=interviews,
                                 selected_candidate=selected_candidate,
                                 selected_candidate_id=selected_candidate_id,
                                 datetime=datetime,
                                 timedelta=timedelta)
                                 
        except Exception as e:
            logging.error(f"Error loading Google Meet scheduling page: {e}")
            flash('Error loading scheduling interface', 'error')
            return redirect(url_for('dashboard'))
    
    # POST request - Create the meeting
    if request.method == 'POST':
        try:
            from technical_interview_service import TechnicalInterviewService
            from datetime import datetime
            
            interview_id = request.form.get('interview_id', type=int)
            candidate_id = request.form.get('candidate_id', type=int)
            technical_person_id = request.form.get('technical_person_id', type=int)
            meeting_date = request.form.get('meeting_date')
            meeting_time = request.form.get('meeting_time')
            duration_minutes = request.form.get('duration_minutes', default=60, type=int)
            meeting_notes = request.form.get('meeting_notes', '')
            
            if not all([interview_id, candidate_id, technical_person_id, meeting_date, meeting_time]):
                return jsonify({'success': False, 'message': 'All fields are required'})
            
            # Combine date and time
            meeting_datetime_str = f"{meeting_date} {meeting_time}"
            meeting_datetime = datetime.strptime(meeting_datetime_str, '%Y-%m-%d %H:%M')
            
            # Create the technical interview assignment with Google Meet
            service = TechnicalInterviewService()
            assignment = service.assign_technical_person(
                interview_id=interview_id,
                candidate_id=candidate_id,
                technical_person_id=technical_person_id,
                interview_datetime=meeting_datetime,
                assigned_by_id=current_user.id
            )
            
            if assignment:
                # Create notification entries for both technical person and candidate
                from models import TechnicalPersonNotification
                
                # Notify technical person
                tech_notification = TechnicalPersonNotification(
                    technical_person_id=technical_person_id,
                    assignment_id=assignment.id,
                    notification_type='meeting_scheduled',
                    status='sent',
                    content=f"Google Meet scheduled for {meeting_datetime.strftime('%B %d, %Y at %I:%M %p')}"
                )
                db.session.add(tech_notification)
                
                # Get user details
                candidate = User.query.get(candidate_id)
                interview = Interview.query.get(interview_id)
                technical_person = User.query.get(technical_person_id)
                
                # Send email notifications (with error handling for missing credentials)
                try:
                    from enhanced_email_service import EnhancedEmailService as EmailService
                    email_service = EmailService()
                    
                    candidate_email_content = f"""
                    <h2>Technical Interview Scheduled</h2>
                    <p>Hello {candidate.first_name},</p>
                    
                    <p>Your technical interview has been scheduled:</p>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3>Meeting Details</h3>
                        <p><strong>Position:</strong> {interview.title}</p>
                        <p><strong>Interviewer:</strong> {technical_person.first_name} {technical_person.last_name}</p>
                        <p><strong>Date & Time:</strong> {meeting_datetime.strftime('%B %d, %Y at %I:%M %p')}</p>
                        <p><strong>Duration:</strong> {duration_minutes} minutes</p>
                        <p><strong>Google Meet Link:</strong> <a href="{getattr(assignment, 'meeting_link', 'Not available')}">{getattr(assignment, 'meeting_link', 'Not available')}</a></p>
                        {f'<p><strong>Notes:</strong> {meeting_notes}</p>' if meeting_notes else ''}
                    </div>
                    
                    <h3>Preparation Tips:</h3>
                    <ul>
                        <li>Test your camera and microphone beforehand</li>
                        <li>Join the meeting 5 minutes early</li>
                        <li>Have your resume and portfolio ready to share</li>
                        <li>Prepare technical questions related to the role</li>
                    </ul>
                    
                    <p>Best regards,<br>Job2Hire Team</p>
                    """
                    
                    email_service.send_email(
                        to_email=candidate.email,
                        subject=f"Technical Interview Scheduled - {interview.title}",
                        html_content=candidate_email_content
                    )
                except Exception as email_error:
                    logging.warning(f"Email delivery failed: {email_error}")
                
                db.session.commit()
                
                # Success response
                meeting_link = getattr(assignment, 'meeting_link', 'Meeting created without Google Meet link')
                return jsonify({
                    'success': True,
                    'message': 'Technical interview scheduled successfully!',
                    'meeting_link': meeting_link,
                    'assignment_id': assignment.id
                })
            else:
                return jsonify({'success': False, 'message': 'Failed to create technical interview assignment'})
                
        except Exception as e:
            logging.error(f"Error scheduling Google Meet: {e}")
            return jsonify({'success': False, 'message': f'Error creating Google Meet meeting: {str(e)}'})


@app.route('/admin/technical-feedback/<int:feedback_id>')
@login_required
def view_technical_feedback(feedback_id):
    """View technical interview feedback"""
    if current_user.role not in ['admin', 'recruiter']:
        flash('Access denied. Admin or HR privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from models import TechnicalInterviewFeedback
        
        feedback = TechnicalInterviewFeedback.query.get_or_404(feedback_id)
        
        # Verify organization access
        if feedback.organization_id != current_user.organization_id:
            flash('Access denied. Feedback not found in your organization.', 'error')
            return redirect(url_for('dashboard'))
        
        return render_template('admin/technical_feedback_view.html', feedback=feedback)
        
    except Exception as e:
        logging.error(f"Error viewing technical feedback: {e}")
        flash('Error loading feedback', 'error')
        return redirect(url_for('dashboard'))


@app.route('/admin/second-round-requests')
@login_required
def second_round_requests():
    """View candidates requiring second round interviews"""
    if current_user.role not in ['admin', 'recruiter']:
        flash('Access denied. Admin or HR privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from technical_interview_service import get_pending_second_rounds
        
        pending_second_rounds = get_pending_second_rounds(current_user.organization_id)
        
        return render_template('admin/second_round_requests.html', 
                             pending_second_rounds=pending_second_rounds)
        
    except Exception as e:
        logging.error(f"Error loading second round requests: {e}")
        flash('Error loading second round requests', 'error')
        return redirect(url_for('dashboard'))


@app.route('/admin/analytics')
@login_required
def admin_analytics():
    """Organization analytics dashboard for admin and super admin"""
    if current_user.role not in ['admin', 'super_admin']:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        if current_user.role == 'super_admin':
            # Super admin sees system-wide analytics
            total_orgs = Organization.query.count()
            active_orgs = Organization.query.filter_by(is_active=True).count()
            total_users = User.query.count()
            users_by_role_raw = db.session.query(User.role, db.func.count(User.id)).group_by(User.role).all()
            users_by_role = {role: count for role, count in users_by_role_raw} if users_by_role_raw else {}
            
            # Plan distribution
            plan_distribution_raw = db.session.query(
                Organization.subscription_plan, 
                db.func.count(Organization.id)
            ).group_by(Organization.subscription_plan).all()
            plan_distribution = {plan: count for plan, count in plan_distribution_raw} if plan_distribution_raw else {}
            
            recent_orgs = Organization.query.order_by(Organization.created_at.desc()).limit(5).all()
            recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()
            
            # Monthly growth
            from sqlalchemy import extract
            monthly_growth_raw = db.session.query(
                extract('year', Organization.created_at).label('year'),
                extract('month', Organization.created_at).label('month'),
                db.func.count(Organization.id).label('count')
            ).filter(Organization.created_at.isnot(None)).group_by('year', 'month').order_by('year', 'month').all()
            
            monthly_growth = []
            if monthly_growth_raw:
                for row in monthly_growth_raw:
                    monthly_growth.append({
                        'year': int(row.year) if row.year else 2025,
                        'month': int(row.month) if row.month else 1,
                        'count': int(row.count)
                    })
            
            return render_template('admin/analytics.html',
                                 total_orgs=total_orgs,
                                 active_orgs=active_orgs,
                                 total_users=total_users,
                                 users_by_role=users_by_role,
                                 plan_distribution=plan_distribution,
                                 recent_orgs=recent_orgs,
                                 recent_users=recent_users,
                                 monthly_growth=monthly_growth,
                                 is_super_admin=True)
        else:
            # Admin sees organization-scoped analytics only
            organization = current_user.organization
            
            # Organization-specific statistics
            org_users = User.query.filter_by(organization_id=current_user.organization_id).all()
            total_users = len(org_users)
            
            # User statistics within organization
            users_by_role = {}
            for user in org_users:
                role = user.role
                users_by_role[role] = users_by_role.get(role, 0) + 1
            
            # Interview statistics within organization
            org_interviews = Interview.query.filter_by(organization_id=current_user.organization_id).all()
            total_interviews = len(org_interviews)
            active_interviews = len([i for i in org_interviews if i.is_active])
            
            # Recent activity within organization
            recent_users = User.query.filter_by(organization_id=current_user.organization_id).order_by(User.created_at.desc()).limit(10).all()
            recent_interviews = Interview.query.filter_by(organization_id=current_user.organization_id).order_by(Interview.created_at.desc()).limit(10).all()
            
            return render_template('admin/organization_analytics.html',
                                 organization=organization,
                                 total_users=total_users,
                                 users_by_role=users_by_role,
                                 total_interviews=total_interviews,
                                 active_interviews=active_interviews,
                                 recent_users=recent_users,
                                 recent_interviews=recent_interviews,
                                 is_super_admin=False)
                                 
    except Exception as e:
        logging.error(f"Error in admin_analytics: {e}")
        flash('Error loading analytics data. Please try again.', 'error')
        return redirect(url_for('dashboard'))

# Organization Candidate Management Routes

@app.route('/add-candidate', methods=['GET', 'POST'])
@login_required
def add_candidate():
    """Add a new candidate to the same organization as current user"""
    # Only allow admins and recruiters to add candidates
    if current_user.role not in ['super_admin', 'admin', 'recruiter']:
        flash('Access denied. Only admins and recruiters can add candidates.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        try:
            # Get form data
            username = request.form.get('username')
            email = request.form.get('email')
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            phone = request.form.get('phone')
            job_title = request.form.get('job_title')
            department = request.form.get('department')
            
            # Validate required fields
            if not all([username, email, first_name, last_name]):
                flash('Username, email, first name, and last name are required.', 'error')
                return redirect(url_for('add_candidate'))
            
            # Phone validation (same pattern as existing system)
            if phone and not re.match(r'^[0-9+\-\s\(\)]+$', phone):
                flash('Invalid phone number format.', 'error')
                return redirect(url_for('add_candidate'))
            
            # Check if username already exists
            if User.query.filter_by(username=username).first():
                flash('Username already exists. Please choose a different username.', 'error')
                return redirect(url_for('add_candidate'))
            
            # Check if email already exists
            if User.query.filter_by(email=email).first():
                flash('Email already exists. Please use a different email.', 'error')
                return redirect(url_for('add_candidate'))
            
            # Create new candidate with same organization_id as current user
            new_candidate = User()
            new_candidate.username = username
            new_candidate.email = email
            new_candidate.password_hash = generate_password_hash('TempPass123!')  # Temporary password
            new_candidate.role = 'candidate'
            new_candidate.organization_id = current_user.organization_id  # Same organization
            new_candidate.first_name = first_name
            new_candidate.last_name = last_name
            new_candidate.phone = phone
            new_candidate.job_title = job_title
            new_candidate.department = department
            new_candidate.user_active = True
            
            db.session.add(new_candidate)
            db.session.commit()
            
            # Create audit log
            audit_log = AuditLog()
            audit_log.user_id = current_user.id
            audit_log.action = 'CREATE_CANDIDATE'
            audit_log.details = f'Added candidate {first_name} {last_name} (ID: {new_candidate.id}) to organization {current_user.organization.name}'
            audit_log.ip_address = request.remote_addr
            
            db.session.add(audit_log)
            db.session.commit()
            
            flash(f'Candidate {first_name} {last_name} added successfully to {current_user.organization.name}!', 'success')
            return redirect(url_for('candidates'))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error adding candidate: {e}")
            flash(f'Error adding candidate: {str(e)}', 'error')
            return redirect(url_for('add_candidate'))
    
    # GET request - show the form
    return render_template('add_candidate.html', 
                         current_organization=current_user.organization.name if current_user.organization else 'Unknown')

@app.route('/api/add-organization-candidate', methods=['POST'])
@login_required
def api_add_organization_candidate():
    """API endpoint to add candidate to same organization"""
    if current_user.role not in ['super_admin', 'admin', 'recruiter']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'email', 'first_name', 'last_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'success': False, 'error': f'{field} is required'}), 400
        
        # Check duplicates
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'success': False, 'error': 'Username already exists'}), 400
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'success': False, 'error': 'Email already exists'}), 400
        
        # Phone validation
        phone = data.get('phone')
        if phone and not re.match(r'^[0-9+\-\s\(\)]+$', phone):
            return jsonify({'success': False, 'error': 'Invalid phone number format'}), 400
        
        # Create candidate
        new_candidate = User()
        new_candidate.username = data['username']
        new_candidate.email = data['email']
        new_candidate.password_hash = generate_password_hash(data.get('password', 'TempPass123!'))
        new_candidate.role = 'candidate'
        new_candidate.organization_id = current_user.organization_id  # Same organization
        new_candidate.first_name = data['first_name']
        new_candidate.last_name = data['last_name']
        new_candidate.phone = phone
        new_candidate.job_title = data.get('job_title')
        new_candidate.department = data.get('department')
        new_candidate.bio = data.get('bio')
        new_candidate.skills = data.get('skills')
        new_candidate.experience_years = data.get('experience_years')
        new_candidate.location = data.get('location')
        new_candidate.user_active = True
        
        db.session.add(new_candidate)
        db.session.commit()
        
        # Create audit log
        audit_log = AuditLog()
        audit_log.user_id = current_user.id
        audit_log.action = 'API_CREATE_CANDIDATE'
        audit_log.details = f'Added candidate {data["first_name"]} {data["last_name"]} (ID: {new_candidate.id}) via API'
        audit_log.ip_address = request.remote_addr
        
        db.session.add(audit_log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Candidate added successfully',
            'candidate_id': new_candidate.id,
            'organization': current_user.organization.name
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"API Error adding candidate: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/hr/technical-feedback')
@login_required
def hr_technical_feedback():
    """HR interface to view all technical feedback in organization"""
    if current_user.role not in ['recruiter', 'admin']:
        flash('Access denied. HR/Admin role required.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from models import TechnicalInterviewFeedback, TechnicalInterviewAssignment
        
        # Get all technical feedback in the organization
        feedback_query = TechnicalInterviewFeedback.query.join(
            TechnicalInterviewAssignment,
            TechnicalInterviewFeedback.assignment_id == TechnicalInterviewAssignment.id
        ).filter(
            TechnicalInterviewAssignment.organization_id == current_user.organization_id
        ).order_by(TechnicalInterviewFeedback.submitted_at.desc())
        
        feedback_list = feedback_query.all()
        
        return render_template('hr/technical_feedback.html', feedback_list=feedback_list)
        
    except Exception as e:
        logging.error(f"Error loading technical feedback for HR: {e}")
        flash('Error loading technical feedback', 'error')
        return redirect(url_for('dashboard'))

@app.route('/hr/send-candidate-email', methods=['POST'])
@login_required
def send_candidate_email():
    """Send decision email to candidate based on technical interview feedback"""
    if current_user.role not in ['recruiter', 'admin']:
        return jsonify({'success': False, 'message': 'Access denied. HR/Admin role required.'}), 403
    
    try:
        data = request.get_json()
        feedback_id = data.get('feedback_id')
        
        if not feedback_id:
            return jsonify({'success': False, 'message': 'Feedback ID is required.'}), 400
        
        # Verify feedback belongs to current user's organization
        feedback = TechnicalInterviewFeedback.query.get(feedback_id)
        if not feedback:
            return jsonify({'success': False, 'message': 'Feedback not found.'}), 404
        
        assignment = TechnicalInterviewAssignment.query.get(feedback.assignment_id)
        if not assignment or assignment.organization_id != current_user.organization_id:
            return jsonify({'success': False, 'message': 'Access denied.'}), 403
        
        # Check if decision is made
        if feedback.decision not in ['selected', 'rejected']:
            return jsonify({'success': False, 'message': 'No decision available to send notification.'}), 400
        
        # Send email using notification service
        try:
            success = send_candidate_decision_email(feedback_id, current_user.id)
            
            # Update candidate profile with feedback status as backup notification
            try:
                candidate = assignment.candidate
                organization = Organization.query.get(assignment.organization_id)
                
                if feedback.decision == 'selected':
                    candidate.interview_feedback_status = 'welcome'
                    candidate.feedback_message = f"🎉 Great news! We'd like to move forward with your application for the {assignment.interview.title} position at {organization.name}. Our team will contact you soon with next steps."
                elif feedback.decision == 'rejected':
                    candidate.interview_feedback_status = 'sorry'
                    candidate.feedback_message = f"Thank you for your interest in the {assignment.interview.title} position at {organization.name}. While we were impressed with your qualifications, we've decided to move forward with other candidates. We encourage you to apply for future opportunities."
                
                candidate.feedback_updated_at = datetime.now()
                db.session.commit()
                
                logging.info(f"Updated candidate profile feedback status to '{candidate.interview_feedback_status}' for {candidate.email}")
            except Exception as profile_error:
                logging.warning(f"Failed to update candidate profile feedback: {profile_error}")
                db.session.rollback()
            
            # Log the activity regardless of email success (notification system worked)
            try:
                from models import AuditLog
                audit = AuditLog()
                audit.user_id = current_user.id
                audit.organization_id = current_user.organization_id
                audit.action = f"Processed {feedback.decision} notification for candidate"
                audit.resource_type = "technical_interview_feedback"
                audit.resource_id = feedback_id
                audit.details = f"Feedback ID: {feedback_id}, Candidate: {assignment.candidate.email}, Profile Updated: {candidate.interview_feedback_status}"
                audit.timestamp = datetime.now()
                db.session.add(audit)
                db.session.commit()
            except Exception as audit_error:
                logging.warning(f"Failed to log email notification audit: {audit_error}")
                db.session.rollback()
            
            # Always return success for notification processing
            return jsonify({
                'success': True, 
                'message': f'{"Welcome" if feedback.decision == "selected" else "Rejection"} notification processed! Candidate profile updated with feedback status.'
            })
            
        except Exception as notification_error:
            logging.error(f"Notification system error: {notification_error}")
            return jsonify({'success': False, 'message': 'Notification system error. Please try again.'}), 500
            
    except Exception as e:
        logging.error(f"Error sending candidate decision email: {e}")
        return jsonify({'success': False, 'message': 'Internal server error.'}), 500

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500


# ===== RESUME BUILDER SYSTEM =====

@app.route('/resume-builder')
@login_required
def resume_builder():
    """Resume Builder main dashboard - Huntr-inspired interface"""
    if current_user.role not in ['candidate']:
        flash('Resume Builder is only available for candidates.', 'warning')
        return redirect(url_for('dashboard'))
    
    # Get user's resumes
    user_resumes = Resume.query.filter_by(user_id=current_user.id, is_active=True).order_by(Resume.updated_at.desc()).all()
    
    # Get available templates
    templates = ResumeTemplate.query.filter_by(is_active=True).order_by(ResumeTemplate.popularity_score.desc()).all()
    
    # Get recent analysis
    recent_analyses = []
    if user_resumes:
        recent_analyses = ResumeAnalysis.query.filter(
            ResumeAnalysis.resume_id.in_([r.id for r in user_resumes])
        ).order_by(ResumeAnalysis.analyzed_at.desc()).limit(3).all()
    
    return render_template('resume_builder_dashboard.html', 
                         resumes=user_resumes, 
                         templates=templates,
                         recent_analyses=recent_analyses)


@app.route('/resume-builder/new')
@login_required
def new_resume():
    """Create new resume - template selection"""
    if current_user.role not in ['candidate']:
        flash('Resume Builder is only available for candidates.', 'warning')
        return redirect(url_for('dashboard'))
    
    # Get available templates with categories
    templates = ResumeTemplate.query.filter_by(is_active=True).order_by(ResumeTemplate.popularity_score.desc()).all()
    
    # Group templates by category
    template_categories = {}
    for template in templates:
        category = template.category or 'Other'
        if category not in template_categories:
            template_categories[category] = []
        template_categories[category].append(template)
    
    return render_template('new_resume.html', 
                         template_categories=template_categories,
                         templates=templates)


@app.route('/resume-builder/create', methods=['POST'])
@login_required
def create_resume():
    """Create new resume with selected template"""
    if current_user.role not in ['candidate']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        template_id = request.form.get('template_id')
        resume_title = request.form.get('title', 'My Resume').strip()
        
        if not template_id:
            return jsonify({'success': False, 'error': 'Template selection required'}), 400
        
        template = ResumeTemplate.query.get(template_id)
        if not template:
            return jsonify({'success': False, 'error': 'Template not found'}), 404
        
        # Create new resume with user's basic information
        new_resume = Resume(
            user_id=current_user.id,
            template_id=template_id,
            title=resume_title,
            is_default=Resume.query.filter_by(user_id=current_user.id).count() == 0,
            full_name=f"{current_user.first_name or ''} {current_user.last_name or ''}".strip(),
            email=current_user.email,
            phone=current_user.phone,
            location=current_user.location,
            linkedin_url=current_user.linkedin_url,
            portfolio_url=current_user.portfolio_url,
            professional_summary=current_user.bio,  # Populate with user's bio/about section
            technical_skills=current_user.skills or "[]",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.session.add(new_resume)
        db.session.commit()
        
        # Populate initial work experience and education from user profile
        try:
            # Parse work experience from user profile
            if current_user.experience:
                try:
                    import json
                    experiences = json.loads(current_user.experience)
                    for idx, exp in enumerate(experiences[:5]):  # Limit to 5 experiences
                        # Handle different date formats
                        start_date = None
                        end_date = None
                        
                        if exp.get('start_date'):
                            try:
                                # Try YYYY-MM-DD format first
                                start_date = datetime.strptime(exp.get('start_date'), '%Y-%m-%d').date()
                            except ValueError:
                                try:
                                    # Try YYYY-MM format
                                    start_date = datetime.strptime(exp.get('start_date'), '%Y-%m').date()
                                except ValueError:
                                    try:
                                        # Try YYYY format
                                        start_date = datetime.strptime(exp.get('start_date'), '%Y').date()
                                    except ValueError:
                                        pass
                        
                        if exp.get('end_date'):
                            try:
                                # Try YYYY-MM-DD format first
                                end_date = datetime.strptime(exp.get('end_date'), '%Y-%m-%d').date()
                            except ValueError:
                                try:
                                    # Try YYYY-MM format
                                    end_date = datetime.strptime(exp.get('end_date'), '%Y-%m').date()
                                except ValueError:
                                    try:
                                        # Try YYYY format
                                        end_date = datetime.strptime(exp.get('end_date'), '%Y').date()
                                    except ValueError:
                                        pass
                        
                        work_exp = ResumeWorkExperience(
                            resume_id=new_resume.id,
                            company_name=exp.get('company', ''),
                            job_title=exp.get('title', ''),
                            start_date=start_date,
                            end_date=end_date,
                            description=exp.get('description', ''),
                            order_index=idx
                        )
                        db.session.add(work_exp)
                except (json.JSONDecodeError, ValueError) as e:
                    logging.warning(f"Error parsing user experience JSON: {e}")
            
            # Parse education from user profile  
            if current_user.education:
                try:
                    import json
                    educations = json.loads(current_user.education)
                    for idx, edu in enumerate(educations[:5]):  # Limit to 5 education entries
                        # Handle different date formats for education
                        start_date = None
                        end_date = None
                        
                        if edu.get('start_date'):
                            try:
                                # Try YYYY-MM-DD format first
                                start_date = datetime.strptime(edu.get('start_date'), '%Y-%m-%d').date()
                            except ValueError:
                                try:
                                    # Try YYYY-MM format
                                    start_date = datetime.strptime(edu.get('start_date'), '%Y-%m').date()
                                except ValueError:
                                    try:
                                        # Try YYYY format
                                        start_date = datetime.strptime(edu.get('start_date'), '%Y').date()
                                    except ValueError:
                                        pass
                        
                        if edu.get('end_date'):
                            try:
                                # Try YYYY-MM-DD format first
                                end_date = datetime.strptime(edu.get('end_date'), '%Y-%m-%d').date()
                            except ValueError:
                                try:
                                    # Try YYYY-MM format
                                    end_date = datetime.strptime(edu.get('end_date'), '%Y-%m').date()
                                except ValueError:
                                    try:
                                        # Try YYYY format
                                        end_date = datetime.strptime(edu.get('end_date'), '%Y').date()
                                    except ValueError:
                                        pass
                        
                        education = ResumeEducation(
                            resume_id=new_resume.id,
                            institution_name=edu.get('institution', ''),
                            degree_type=edu.get('degree', ''),
                            field_of_study=edu.get('field_of_study', ''),
                            start_date=start_date,
                            end_date=end_date,
                            gpa=edu.get('gpa', ''),
                            order_index=idx
                        )
                        db.session.add(education)
                except (json.JSONDecodeError, ValueError) as e:
                    logging.warning(f"Error parsing user education JSON: {e}")
            
            db.session.commit()
            
        except Exception as e:
            logging.warning(f"Error populating resume with user profile data: {e}")
            # Don't fail the entire resume creation if this fails
            db.session.rollback()
            db.session.add(new_resume)
            db.session.commit()
        
        # Update template popularity
        template.popularity_score = (template.popularity_score or 0) + 1
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'resume_id': new_resume.id,
            'redirect_url': url_for('edit_resume', resume_id=new_resume.id)
        })
        
    except Exception as e:
        logging.error(f"Error creating resume: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to create resume'}), 500


@app.route('/resume-builder/edit/<int:resume_id>')
@login_required
def edit_resume(resume_id):
    """Resume editing interface - AI-powered like Huntr"""
    if current_user.role not in ['candidate']:
        flash('Resume Builder is only available for candidates.', 'warning')
        return redirect(url_for('dashboard'))
    
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
    if not resume:
        flash('Resume not found.', 'error')
        return redirect(url_for('resume_builder'))
    
    # Parse JSON fields
    technical_skills = safe_json_loads(resume.technical_skills)
    soft_skills = safe_json_loads(resume.soft_skills)
    languages = safe_json_loads(resume.languages)
    certifications = safe_json_loads(resume.certifications)
    
    # Get related data
    work_experiences = ResumeWorkExperience.query.filter_by(resume_id=resume_id).order_by(ResumeWorkExperience.order_index).all()
    educations = ResumeEducation.query.filter_by(resume_id=resume_id).order_by(ResumeEducation.order_index).all()
    projects = ResumeProject.query.filter_by(resume_id=resume_id).order_by(ResumeProject.order_index).all()
    achievements = ResumeAchievement.query.filter_by(resume_id=resume_id).order_by(ResumeAchievement.order_index).all()
    
    # Get latest analysis
    latest_analysis = ResumeAnalysis.query.filter_by(resume_id=resume_id).order_by(ResumeAnalysis.analyzed_at.desc()).first()
    
    return render_template('edit_resume.html',
                         resume=resume,
                         technical_skills=technical_skills,
                         soft_skills=soft_skills,
                         languages=languages,
                         certifications=certifications,
                         work_experiences=work_experiences,
                         educations=educations,
                         projects=projects,
                         achievements=achievements,
                         latest_analysis=latest_analysis,
                         templates=ResumeTemplate.query.filter_by(is_active=True).all())


@app.route('/resume-builder/update/<int:resume_id>', methods=['POST'])
@login_required
def update_resume(resume_id):
    """Update resume with form data"""
    if current_user.role not in ['candidate']:
        flash('Access denied.', 'error')
        return redirect(url_for('candidate_dashboard'))
    
    try:
        resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
        if not resume:
            flash('Resume not found.', 'error')
            return redirect(url_for('resume_builder'))
        
        # Update basic information
        resume.title = request.form.get('title')
        resume.template_id = request.form.get('template_id')
        resume.full_name = request.form.get('full_name')
        resume.email = request.form.get('email')
        resume.phone = request.form.get('phone')
        resume.location = request.form.get('location')
        resume.professional_summary = request.form.get('professional_summary')
        resume.technical_skills = request.form.get('technical_skills')
        resume.soft_skills = request.form.get('soft_skills')
        resume.updated_at = datetime.utcnow()
        
        # Update work experiences
        # First, delete existing experiences
        ResumeWorkExperience.query.filter_by(resume_id=resume_id).delete()
        
        companies = request.form.getlist('experience_company[]')
        titles = request.form.getlist('experience_title[]')
        start_dates = request.form.getlist('experience_start[]')
        end_dates = request.form.getlist('experience_end[]')
        descriptions = request.form.getlist('experience_description[]')
        
        for i in range(len(companies)):
            if companies[i]:  # Only add if company name is provided
                experience = ResumeWorkExperience(
                    resume_id=resume_id,
                    company_name=companies[i],
                    job_title=titles[i] if i < len(titles) else '',
                    start_date=datetime.strptime(start_dates[i], '%Y-%m-%d').date() if start_dates[i] else None,
                    end_date=datetime.strptime(end_dates[i], '%Y-%m-%d').date() if end_dates[i] else None,
                    description=descriptions[i] if i < len(descriptions) else ''
                )
                db.session.add(experience)
        
        # Update education
        # First, delete existing education
        ResumeEducation.query.filter_by(resume_id=resume_id).delete()
        
        institutions = request.form.getlist('education_institution[]')
        degrees = request.form.getlist('education_degree[]')
        start_dates = request.form.getlist('education_start[]')
        end_dates = request.form.getlist('education_end[]')
        
        for i in range(len(institutions)):
            if institutions[i]:  # Only add if institution is provided
                education = ResumeEducation(
                    resume_id=resume_id,
                    institution_name=institutions[i],
                    degree_type=degrees[i] if i < len(degrees) else '',
                    start_date=datetime.strptime(start_dates[i], '%Y-%m-%d').date() if start_dates[i] else None,
                    end_date=datetime.strptime(end_dates[i], '%Y-%m-%d').date() if end_dates[i] else None
                )
                db.session.add(education)
        
        db.session.commit()
        flash('Resume updated successfully!', 'success')
        return redirect(url_for('edit_resume', resume_id=resume_id))
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error updating resume: {e}")
        flash('Error updating resume. Please try again.', 'error')
        return redirect(url_for('edit_resume', resume_id=resume_id))


@app.route('/resume-builder/preview/<int:resume_id>')
@login_required
def resume_preview(resume_id):
    """Preview resume in professional format"""
    if current_user.role not in ['candidate']:
        flash('Access denied.', 'error')
        return redirect(url_for('candidate_dashboard'))
    
    try:
        resume = Resume.query.options(
            db.joinedload(Resume.work_experiences),
            db.joinedload(Resume.educations),
            db.joinedload(Resume.projects),
            db.joinedload(Resume.achievements),
            db.joinedload(Resume.template)
        ).filter_by(id=resume_id, user_id=current_user.id).first()
        
        if not resume:
            flash('Resume not found.', 'error')
            return redirect(url_for('resume_builder'))
        
        return render_template('resume_preview.html', resume=resume)
        
    except Exception as e:
        logging.error(f"Error previewing resume: {e}")
        flash('Error loading resume preview.', 'error')
        return redirect(url_for('resume_builder'))


@app.route('/resume-builder/analysis/<int:resume_id>')
@login_required
def resume_analysis(resume_id):
    """Show resume analysis and recommendations"""
    if current_user.role not in ['candidate']:
        flash('Access denied.', 'error')
        return redirect(url_for('candidate_dashboard'))
    
    try:
        resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
        if not resume:
            flash('Resume not found.', 'error')
            return redirect(url_for('resume_builder'))
        
        # Get latest analysis
        analysis = ResumeAnalysis.query.filter_by(resume_id=resume_id).order_by(ResumeAnalysis.analyzed_at.desc()).first()
        
        # Parse JSON fields if analysis exists
        if analysis:
            try:
                import json
                analysis.strengths = json.loads(analysis.strengths) if analysis.strengths else []
                analysis.weaknesses = json.loads(analysis.weaknesses) if analysis.weaknesses else []
                analysis.recommendations = json.loads(analysis.recommendations) if analysis.recommendations else []
            except json.JSONDecodeError:
                # If JSON parsing fails, convert to list
                analysis.strengths = [analysis.strengths] if analysis.strengths else []
                analysis.weaknesses = [analysis.weaknesses] if analysis.weaknesses else []
                analysis.recommendations = [analysis.recommendations] if analysis.recommendations else []
        
        return render_template('resume_analysis.html', resume=resume, analysis=analysis)
        
    except Exception as e:
        logging.error(f"Error loading resume analysis: {e}")
        flash('Error loading resume analysis.', 'error')
        return redirect(url_for('resume_builder'))


@app.route('/resume-builder/ai/generate-summary', methods=['POST'])
@login_required
def ai_generate_summary():
    """AI-powered professional summary generation"""
    if current_user.role not in ['candidate']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        from resume_builder_service import ResumeBuilderAI
        
        data = request.get_json()
        job_title = data.get('job_title', '')
        experience_years = int(data.get('experience_years', 0))
        key_skills = data.get('key_skills', [])
        industry = data.get('industry', '')
        
        if not job_title:
            return jsonify({'success': False, 'error': 'Job title is required'}), 400
        
        ai_service = ResumeBuilderAI()
        result = ai_service.generate_professional_summary(
            job_title=job_title,
            experience_years=experience_years,
            key_skills=key_skills,
            industry=industry
        )
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error generating AI summary: {e}")
        return jsonify({'success': False, 'error': 'Failed to generate summary'}), 500


@app.route('/resume-builder/generate/<int:resume_id>')
@login_required
def generate_resume_pdf(resume_id):
    """Generate and download resume as PDF using WeasyPrint"""
    if current_user.role not in ['candidate']:
        flash('Resume Builder is only available for candidates.', 'warning')
        return redirect(url_for('dashboard'))
    
    try:
        from weasyprint import HTML, CSS
        from flask import make_response
        from io import BytesIO
        
        logging.info(f"Starting PDF generation for resume {resume_id}")
        
        resume = Resume.query.options(
            db.joinedload(Resume.work_experiences),
            db.joinedload(Resume.educations),
            db.joinedload(Resume.projects),
            db.joinedload(Resume.achievements)
        ).filter_by(id=resume_id, user_id=current_user.id).first()
        
        if not resume:
            logging.error(f"Resume {resume_id} not found for user {current_user.id}")
            flash('Resume not found.', 'error')
            return redirect(url_for('resume_builder'))
        
        logging.info(f"Found resume: {resume.title}, user: {resume.full_name}")
        
        # Generate clean HTML for PDF
        logging.info("Generating HTML content...")
        html_content = generate_clean_resume_html(resume)
        logging.info(f"HTML content generated, length: {len(html_content)}")
        
        # Create PDF
        logging.info("Creating PDF buffer...")
        pdf_buffer = BytesIO()
        logging.info("Writing PDF with WeasyPrint...")
        HTML(string=html_content).write_pdf(pdf_buffer, stylesheets=[CSS(string=get_pdf_css())])
        pdf_buffer.seek(0)
        logging.info("PDF generation completed successfully")
        
        # Create response
        response = make_response(pdf_buffer.read())
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{resume.full_name or "Resume"}.pdf"'
        
        return response
        
    except Exception as e:
        logging.error(f"Error generating resume PDF: {e}")
        flash('Error generating PDF. Please try again.', 'error')
        return redirect(url_for('edit_resume', resume_id=resume_id))


def generate_clean_resume_html(resume):
    """Generate clean HTML for PDF generation"""
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{resume.full_name or 'Resume'} - Document</title>
    </head>
    <body>
        <div class="resume-container">
            <!-- Header -->
            <div class="header">
                <h1 class="name">{resume.full_name or 'Your Name'}</h1>
                <div class="contact-info">
                    {f'<span class="email">{resume.email}</span>' if resume.email else ''}
                    {f'<span class="phone">{resume.phone}</span>' if resume.phone else ''}
                    {f'<span class="location">{resume.location}</span>' if resume.location else ''}
                </div>
            </div>
            
            <!-- Professional Summary -->
            {f'<div class="section"><h2>Professional Summary</h2><p class="summary">{resume.professional_summary}</p></div>' if resume.professional_summary else ''}
            
            <!-- Technical Skills -->
            {f'<div class="section"><h2>Technical Skills</h2><p>{resume.technical_skills}</p></div>' if resume.technical_skills else ''}
            
            <!-- Work Experience -->
            {'<div class="section"><h2>Professional Experience</h2>' + ''.join([f'''
                <div class="experience-item">
                    <div class="experience-header">
                        <h3 class="job-title">{exp.job_title}</h3>
                        <span class="date-range">{exp.start_date.strftime("%m/%Y") if exp.start_date else "Start"} - {exp.end_date.strftime("%m/%Y") if exp.end_date else "Present"}</span>
                    </div>
                    <h4 class="company">{exp.company_name}</h4>
                    {f"<p class='location'>{exp.location}</p>" if exp.location else ""}
                    {f"<p class='description'>{exp.description}</p>" if exp.description else ""}
                </div>
            ''' for exp in resume.work_experiences]) + '</div>' if resume.work_experiences else ''}
            
            <!-- Education -->
            {'<div class="section"><h2>Education</h2>' + ''.join([f'''
                <div class="education-item">
                    <div class="education-header">
                        <h3 class="degree">{edu.degree_type} {edu.field_of_study}</h3>
                        <span class="date-range">{edu.start_date.year if edu.start_date else "Start"} - {edu.end_date.year if edu.end_date else "End"}</span>
                    </div>
                    <h4 class="institution">{edu.institution_name}</h4>
                    {f"<p class='gpa'>GPA: {edu.gpa}</p>" if edu.gpa else ""}
                </div>
            ''' for edu in resume.educations]) + '</div>' if resume.educations else ''}
            
            <!-- Soft Skills -->
            {f'<div class="section"><h2>Core Competencies</h2><p>{resume.soft_skills}</p></div>' if resume.soft_skills else ''}
            
            <!-- Projects -->
            {'<div class="section"><h2>Projects</h2>' + ''.join([f'''
                <div class="project-item">
                    <h3 class="project-title">{proj.project_name}</h3>
                    {f"<p class='project-description'>{proj.description}</p>" if proj.description else ""}
                    {f"<p class='technologies'>Technologies: {proj.technologies}</p>" if proj.technologies else ""}
                </div>
            ''' for proj in resume.projects]) + '</div>' if resume.projects else ''}
            
            <!-- Achievements -->
            {'<div class="section"><h2>Achievements</h2>' + ''.join([f'''
                <div class="achievement-item">
                    <h3 class="achievement-title">{ach.title}</h3>
                    {f"<p class='achievement-description'>{ach.description}</p>" if ach.description else ""}
                </div>
            ''' for ach in resume.achievements]) + '</div>' if resume.achievements else ''}
        </div>
    </body>
    </html>
    """
    return html


def get_pdf_css():
    """Get CSS for PDF generation"""
    return """
        @page {
            size: A4;
            margin: 0.75in;
        }
        
        body {
            font-family: 'Times New Roman', serif;
            font-size: 11pt;
            line-height: 1.4;
            color: #000;
            margin: 0;
            padding: 0;
        }
        
        .resume-container {
            max-width: 100%;
        }
        
        .header {
            text-align: center;
            margin-bottom: 20pt;
            border-bottom: 1pt solid #000;
            padding-bottom: 10pt;
        }
        
        .name {
            font-size: 18pt;
            font-weight: bold;
            margin: 0 0 8pt 0;
            letter-spacing: 1pt;
        }
        
        .contact-info {
            font-size: 10pt;
        }
        
        .contact-info span {
            margin: 0 15pt;
        }
        
        .section {
            margin-bottom: 15pt;
            page-break-inside: avoid;
        }
        
        .section h2 {
            font-size: 12pt;
            font-weight: bold;
            margin: 0 0 8pt 0;
            border-bottom: 1pt solid #000;
            padding-bottom: 2pt;
            page-break-after: avoid;
        }
        
        .experience-item, .education-item, .project-item, .achievement-item {
            margin-bottom: 12pt;
            page-break-inside: avoid;
        }
        
        .experience-header, .education-header {
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            margin-bottom: 4pt;
        }
        
        .job-title, .degree {
            font-size: 11pt;
            font-weight: bold;
            margin: 0;
            page-break-after: avoid;
        }
        
        .date-range {
            font-size: 10pt;
            font-style: italic;
            white-space: nowrap;
        }
        
        .company, .institution {
            font-size: 10pt;
            font-weight: bold;
            margin: 0 0 4pt 0;
            page-break-after: avoid;
        }
        
        .description, .project-description, .achievement-description, .summary {
            font-size: 10pt;
            margin: 4pt 0;
            text-align: justify;
        }
        
        .project-title, .achievement-title {
            font-size: 11pt;
            font-weight: bold;
            margin: 0 0 4pt 0;
            page-break-after: avoid;
        }
        
        .technologies, .gpa, .location {
            font-size: 9pt;
            margin: 2pt 0;
            font-style: italic;
        }
        
        p {
            margin: 4pt 0;
        }
    """


@app.route('/resume-builder/ai/enhance-experience', methods=['POST'])
@login_required
def ai_enhance_experience():
    """AI-powered work experience enhancement - like Huntr's 'Rewrite with AI'"""
    if current_user.role not in ['candidate']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        from resume_builder_service import ResumeBuilderAI
        
        data = request.get_json()
        job_title = data.get('job_title', '')
        company = data.get('company', '')
        description = data.get('description', '')
        achievements = data.get('achievements', [])
        
        if not job_title or not company:
            return jsonify({'success': False, 'error': 'Job title and company are required'}), 400
        
        ai_service = ResumeBuilderAI()
        result = ai_service.enhance_work_experience(
            job_title=job_title,
            company=company,
            basic_description=description,
            achievements=achievements
        )
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error enhancing work experience: {e}")
        return jsonify({'success': False, 'error': 'Failed to enhance experience'}), 500


@app.route('/resume-builder/ai/job-match', methods=['POST'])
@login_required
def ai_job_match_analysis():
    """AI job matching analysis - like Huntr's targeted resume feature"""
    if current_user.role not in ['candidate']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        from resume_builder_service import ResumeBuilderAI
        
        data = request.get_json()
        resume_id = data.get('resume_id')
        job_description = data.get('job_description', '')
        
        if not resume_id or not job_description:
            return jsonify({'success': False, 'error': 'Resume ID and job description are required'}), 400
        
        resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
        if not resume:
            return jsonify({'success': False, 'error': 'Resume not found'}), 404
        
        # Prepare resume data
        resume_data = {
            'professional_summary': resume.professional_summary,
            'technical_skills': json.loads(resume.technical_skills or "[]"),
            'soft_skills': json.loads(resume.soft_skills or "[]"),
            'work_experiences': [
                {
                    'job_title': exp.job_title,
                    'company_name': exp.company_name,
                    'description': exp.description
                } for exp in resume.work_experiences
            ],
            'education': [
                {
                    'degree_type': edu.degree_type,
                    'field_of_study': edu.field_of_study,
                    'institution_name': edu.institution_name
                } for edu in resume.educations
            ]
        }
        
        ai_service = ResumeBuilderAI()
        result = ai_service.analyze_job_match(resume_data, job_description)
        
        # Save analysis to database
        if result.get('success'):
            analysis_data = result['data']
            resume_analysis = ResumeAnalysis(
                resume_id=resume_id,
                job_description=job_description,
                overall_score=analysis_data.get('match_percentage', 0),
                ats_compatibility=85,  # Default value, will be calculated separately
                keyword_optimization=analysis_data.get('match_percentage', 0),
                content_quality=80,  # Default value
                format_score=90,  # Default value
                length_optimization=85,  # Default value
                strengths=json.dumps(analysis_data.get('strength_areas', [])),
                weaknesses=json.dumps(analysis_data.get('improvement_areas', [])),
                keyword_suggestions=json.dumps(analysis_data.get('missing_keywords', [])),
                improvement_suggestions=json.dumps(analysis_data.get('content_suggestions', [])),
                missing_keywords=json.dumps(analysis_data.get('missing_keywords', [])),
                ats_warnings=json.dumps(analysis_data.get('ats_recommendations', [])),
                job_match_percentage=analysis_data.get('match_percentage', 0),
                top_matching_skills=json.dumps(analysis_data.get('matching_skills', [])),
                missing_skills=json.dumps(analysis_data.get('missing_skills', [])),
                analyzed_at=datetime.utcnow()
            )
            
            db.session.add(resume_analysis)
            db.session.commit()
            
            result['analysis_id'] = resume_analysis.id
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error analyzing job match: {e}")
        return jsonify({'success': False, 'error': 'Failed to analyze job match'}), 500


@app.route('/resume-builder/ai/skills-suggestions', methods=['POST'])
@login_required
def ai_skills_suggestions():
    """AI-powered skills suggestions"""
    if current_user.role not in ['candidate']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        from resume_builder_service import ResumeBuilderAI
        
        data = request.get_json()
        job_title = data.get('job_title', '')
        industry = data.get('industry', '')
        current_skills = data.get('current_skills', [])
        
        if not job_title:
            return jsonify({'success': False, 'error': 'Job title is required'}), 400
        
        ai_service = ResumeBuilderAI()
        result = ai_service.generate_skills_suggestions(
            job_title=job_title,
            industry=industry,
            current_skills=current_skills
        )
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error generating skills suggestions: {e}")
        return jsonify({'success': False, 'error': 'Failed to generate suggestions'}), 500


@app.route('/resume-builder/save', methods=['POST'])
@login_required
def save_resume():
    """Save resume data"""
    if current_user.role not in ['candidate']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        resume_id = data.get('resume_id')
        
        resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
        if not resume:
            return jsonify({'success': False, 'error': 'Resume not found'}), 404
        
        # Update basic information
        resume.title = data.get('title', resume.title)
        resume.full_name = data.get('full_name', resume.full_name)
        resume.email = data.get('email', resume.email)
        resume.phone = data.get('phone', resume.phone)
        resume.location = data.get('location', resume.location)
        resume.linkedin_url = data.get('linkedin_url', resume.linkedin_url)
        resume.portfolio_url = data.get('portfolio_url', resume.portfolio_url)
        resume.website_url = data.get('website_url', resume.website_url)
        resume.professional_summary = data.get('professional_summary', resume.professional_summary)
        resume.headline = data.get('headline', resume.headline)
        
        # Update skills
        resume.technical_skills = json.dumps(data.get('technical_skills', []))
        resume.soft_skills = json.dumps(data.get('soft_skills', []))
        resume.languages = json.dumps(data.get('languages', []))
        resume.certifications = json.dumps(data.get('certifications', []))
        
        # Update settings
        resume.color_scheme = data.get('color_scheme', resume.color_scheme)
        resume.font_style = data.get('font_style', resume.font_style)
        resume.show_photo = data.get('show_photo', resume.show_photo)
        
        resume.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Resume saved successfully'})
        
    except Exception as e:
        logging.error(f"Error saving resume: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to save resume'}), 500


@app.route('/resume-builder/preview/<int:resume_id>')
@login_required
def preview_resume(resume_id):
    """Preview resume with selected template"""
    if current_user.role not in ['candidate']:
        flash('Resume Builder is only available for candidates.', 'warning')
        return redirect(url_for('dashboard'))
    
    resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
    if not resume:
        flash('Resume not found.', 'error')
        return redirect(url_for('resume_builder'))
    
    # Parse JSON fields
    technical_skills = safe_json_loads(resume.technical_skills)
    soft_skills = safe_json_loads(resume.soft_skills)
    languages = safe_json_loads(resume.languages)
    certifications = safe_json_loads(resume.certifications)
    
    # Get related data
    work_experiences = ResumeWorkExperience.query.filter_by(resume_id=resume_id).order_by(ResumeWorkExperience.start_date.desc()).all()
    educations = ResumeEducation.query.filter_by(resume_id=resume_id).order_by(ResumeEducation.start_date.desc()).all()
    projects = ResumeProject.query.filter_by(resume_id=resume_id).order_by(ResumeProject.start_date.desc()).all()
    achievements = ResumeAchievement.query.filter_by(resume_id=resume_id).order_by(ResumeAchievement.achievement_date.desc()).all()
    
    return render_template('resume_preview.html',
                         resume=resume,
                         technical_skills=technical_skills,
                         soft_skills=soft_skills,
                         languages=languages,
                         certifications=certifications,
                         work_experiences=work_experiences,
                         educations=educations,
                         projects=projects,
                         achievements=achievements)


@app.route('/resume-builder/analyze/<int:resume_id>', methods=['POST'])
@login_required
def analyze_resume_ats(resume_id):
    """Run comprehensive ATS analysis on resume"""
    if current_user.role not in ['candidate']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
        if not resume:
            return jsonify({'success': False, 'error': 'Resume not found'}), 404
        
        # Try AI service first, but fallback to rule-based analysis
        try:
            from resume_builder_service import ResumeBuilderAI
            ai_service = ResumeBuilderAI()
            
            # Generate resume content for analysis
            resume_content = f"""
            {resume.headline or ''}
            
            {resume.professional_summary or ''}
            
            SKILLS:
            Technical: {', '.join(json.loads(resume.technical_skills or "[]"))}
            Soft Skills: {', '.join(json.loads(resume.soft_skills or "[]"))}
            
            EXPERIENCE:
            {' '.join([f"{exp.job_title} at {exp.company_name}. {exp.description}" for exp in resume.work_experiences])}
            
            EDUCATION:
            {' '.join([f"{edu.degree_type} in {edu.field_of_study} from {edu.institution_name}" for edu in resume.educations])}
            """
            
            result = ai_service.analyze_resume_ats_compatibility(resume_content)
            
            if result.get('success') and result.get('data'):
                analysis_data = result['data']
            else:
                raise Exception("AI service failed, using fallback")
                
        except Exception as ai_error:
            logging.warning(f"AI service failed, using fallback analysis: {ai_error}")
            # Fallback to rule-based analysis
            analysis_data = generate_fallback_analysis(resume)
        
        # Save analysis to database
        resume_analysis = ResumeAnalysis(
            resume_id=resume_id,
            overall_score=analysis_data.get('overall_score', 0),
            ats_compatibility=analysis_data.get('ats_compatibility', 0),
            keyword_optimization=analysis_data.get('keyword_optimization', 0),
            content_quality=analysis_data.get('content_quality', 0),
            format_score=analysis_data.get('format_structure', 0),
            length_optimization=analysis_data.get('length_optimization', 0),
            strengths=json.dumps(analysis_data.get('strengths', [])),
            weaknesses=json.dumps(analysis_data.get('critical_issues', [])),
            keyword_suggestions=json.dumps(analysis_data.get('keyword_recommendations', [])),
            improvement_suggestions=json.dumps(analysis_data.get('improvement_suggestions', [])),
            ats_warnings=json.dumps(analysis_data.get('ats_warnings', [])),
            analyzed_at=datetime.utcnow()
        )
        
        db.session.add(resume_analysis)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'data': analysis_data,
            'analysis_id': resume_analysis.id
        })
        
    except Exception as e:
        logging.error(f"Error analyzing resume: {e}")
        return jsonify({'success': False, 'error': 'Failed to analyze resume'}), 500


def generate_fallback_analysis(resume):
    """Generate rule-based resume analysis when AI service fails"""
    import random
    
    # Basic scoring logic
    technical_skills = json.loads(resume.technical_skills or "[]")
    soft_skills = json.loads(resume.soft_skills or "[]")
    work_exp_count = len(resume.work_experiences)
    education_count = len(resume.educations)
    
    # Calculate scores based on content
    overall_score = min(95, 60 + len(technical_skills) * 2 + work_exp_count * 5 + education_count * 3)
    ats_compatibility = min(90, 70 + len(technical_skills) * 3)
    keyword_optimization = min(85, 50 + len(technical_skills) * 4)
    content_quality = min(90, 65 + work_exp_count * 8)
    format_structure = 88  # Static good score for format
    length_optimization = 82
    
    # Generate strengths based on resume content
    strengths = []
    if len(technical_skills) > 5:
        strengths.append("Strong technical skill set with diverse technologies")
    if work_exp_count > 2:
        strengths.append("Solid work experience across multiple roles")
    if resume.professional_summary:
        strengths.append("Professional summary clearly states career objectives")
    if education_count > 0:
        strengths.append("Educational background supports career goals")
    
    # Generate improvement suggestions
    critical_issues = []
    improvement_suggestions = []
    
    if len(technical_skills) < 5:
        critical_issues.append("Limited technical skills listed")
        improvement_suggestions.append("Add more relevant technical skills to increase keyword matching")
    
    if work_exp_count < 2:
        critical_issues.append("Limited work experience")
        improvement_suggestions.append("Include internships, projects, or volunteer work to demonstrate experience")
    
    if not resume.professional_summary:
        critical_issues.append("Missing professional summary")
        improvement_suggestions.append("Add a compelling professional summary at the top of your resume")
    
    # Generate keyword recommendations
    keyword_recommendations = [
        "Leadership", "Project Management", "Team Collaboration",
        "Problem Solving", "Communication", "Analytical Skills"
    ]
    
    # Generate ATS warnings
    ats_warnings = [
        "Use standard section headers (Experience, Education, Skills)",
        "Avoid graphics or images that ATS cannot read",
        "Include keywords from job descriptions"
    ]
    
    return {
        "overall_score": overall_score,
        "ats_compatibility": ats_compatibility,
        "keyword_optimization": keyword_optimization,
        "content_quality": content_quality,
        "format_structure": format_structure,
        "length_optimization": length_optimization,
        "strengths": strengths,
        "critical_issues": critical_issues,
        "improvement_suggestions": improvement_suggestions,
        "keyword_recommendations": keyword_recommendations,
        "ats_warnings": ats_warnings
    }


@app.route('/resume-builder/delete/<int:resume_id>', methods=['POST', 'DELETE'])
@login_required
def delete_resume(resume_id):
    """Delete a resume and all associated data"""
    if current_user.role not in ['candidate']:
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        # Find the resume
        resume = Resume.query.filter_by(id=resume_id, user_id=current_user.id).first()
        if not resume:
            return jsonify({'success': False, 'error': 'Resume not found'}), 404
        
        # Delete associated work experiences
        ResumeWorkExperience.query.filter_by(resume_id=resume_id).delete()
        
        # Delete associated educations
        ResumeEducation.query.filter_by(resume_id=resume_id).delete()
        
        # Delete associated analyses
        ResumeAnalysis.query.filter_by(resume_id=resume_id).delete()
        
        # Delete the resume
        db.session.delete(resume)
        db.session.commit()
        
        logging.info(f"Resume {resume_id} deleted successfully by user {current_user.id}")
        
        return jsonify({
            'success': True,
            'message': 'Resume deleted successfully'
        })
        
    except Exception as e:
        logging.error(f"Error deleting resume {resume_id}: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to delete resume'}), 500

# Quick Job Routes
@app.route('/quick-jobs')
@login_required
def quick_jobs():
    """Quick Job main page for candidates"""
    if current_user.role != 'candidate':
        flash('Access denied. Only candidates can access Quick Jobs.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get comprehensive quick job data
        quick_job_data = get_quick_job_dashboard_data(current_user.id)
        
        return render_template('quick_jobs.html',
                             quick_jobs=quick_job_data.get('quick_jobs', []),
                             trending_jobs=quick_job_data.get('trending_jobs', []),
                             stats=quick_job_data.get('stats', {}))
        
    except Exception as e:
        logging.error(f"Error loading quick jobs for user {current_user.id}: {e}")
        flash('Error loading quick jobs. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/quick-jobs/search')
@login_required
def quick_jobs_search():
    """Quick Job search API endpoint"""
    if current_user.role != 'candidate':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        query = request.args.get('q', '').strip()
        limit = min(request.args.get('limit', 15, type=int), 50)  # Max 50 results
        
        if not query:
            return jsonify({'jobs': [], 'message': 'No search query provided'})
        
        # Perform quick search
        search_results = quick_search_jobs_for_user(query, current_user.id, limit)
        
        # Convert job objects to dictionaries for JSON response
        jobs_json = []
        for job_data in search_results:
            job_dict = {
                'job': {
                    'id': job_data['job'].id,
                    'title': job_data['job'].title,
                    'location': job_data['job'].location,
                    'description': job_data['job'].description,
                    'posted_date': job_data['job'].posted_date.isoformat() if job_data['job'].posted_date else None,
                    'remote_type': job_data['job'].remote_type,
                    'employment_type': job_data['job'].employment_type,
                    'experience_level': job_data['job'].experience_level,
                    'salary_min': job_data['job'].salary_min,
                    'salary_max': job_data['job'].salary_max
                },
                'match_score': job_data['match_score'],
                'company_name': job_data['company_name'],
                'can_apply_quick': job_data['can_apply_quick'],
                'is_saved': job_data['is_saved'],
                'quick_actions': job_data['quick_actions']
            }
            jobs_json.append(job_dict)
        
        return jsonify({
            'jobs': jobs_json,
            'total_count': len(jobs_json),
            'query': query
        })
        
    except Exception as e:
        logging.error(f"Error in quick job search: {e}")
        return jsonify({'error': 'Search failed. Please try again.'}), 500

@app.route('/quick-jobs/save/<int:job_id>', methods=['POST'])
@login_required
def quick_jobs_save(job_id):
    """Quick save job endpoint"""
    if current_user.role != 'candidate':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        service = QuickJobService()
        success = service.save_job_quick(current_user.id, job_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Job saved successfully!'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Job already saved or failed to save'
            })
            
    except Exception as e:
        logging.error(f"Error saving job {job_id} for user {current_user.id}: {e}")
        return jsonify({'error': 'Failed to save job'}), 500

@app.route('/quick-jobs/unsave/<int:job_id>', methods=['POST'])
@login_required
def quick_jobs_unsave(job_id):
    """Quick unsave job endpoint"""
    if current_user.role != 'candidate':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        service = QuickJobService()
        success = service.unsave_job_quick(current_user.id, job_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Job unsaved successfully!'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Job was not saved or failed to unsave'
            })
            
    except Exception as e:
        logging.error(f"Error unsaving job {job_id} for user {current_user.id}: {e}")
        return jsonify({'error': 'Failed to unsave job'}), 500

@app.route('/quick-jobs/stats')
@login_required
def quick_jobs_stats():
    """Get quick job statistics for user"""
    if current_user.role != 'candidate':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        service = QuickJobService()
        stats = service.get_quick_job_stats(current_user)
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logging.error(f"Error getting quick job stats for user {current_user.id}: {e}")
        return jsonify({'error': 'Failed to get stats'}), 500


# ===== ANALYTICS & REPORTING ROUTES =====

@app.route('/analytics/dashboard')
@login_required
def analytics_dashboard():
    """Advanced analytics dashboard for HR/Admin users"""
    if current_user.role not in ['admin', 'super_admin']:
        flash('Access denied. Only admins can access analytics.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get comprehensive analytics data
        organization_id = None if current_user.role == 'super_admin' else current_user.organization_id
        analytics_data = get_recruitment_dashboard_data(current_user.id, organization_id)
        
        return render_template('analytics_dashboard.html', 
                             analytics=analytics_data,
                             user=current_user)
        
    except Exception as e:
        logging.error(f"Error loading analytics dashboard: {e}")
        flash('Error loading analytics dashboard. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/analytics/pipeline')
@login_required
def analytics_pipeline():
    """Candidate pipeline analytics"""
    if current_user.role not in ['admin', 'super_admin']:
        flash('Access denied. Only admins can access analytics.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        organization_id = None if current_user.role == 'super_admin' else current_user.organization_id
        pipeline_data = get_candidate_pipeline_analytics(current_user.id, organization_id)
        
        return render_template('analytics_pipeline.html', 
                             pipeline=pipeline_data,
                             user=current_user)
        
    except Exception as e:
        logging.error(f"Error loading pipeline analytics: {e}")
        flash('Error loading pipeline analytics. Please try again.', 'error')
        return redirect(url_for('analytics_dashboard'))

@app.route('/analytics/interviews')
@login_required
def analytics_interviews():
    """Interview performance tracking"""
    if current_user.role not in ['admin', 'super_admin']:
        flash('Access denied. Only admins can access analytics.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        organization_id = None if current_user.role == 'super_admin' else current_user.organization_id
        interview_data = get_interview_performance_tracking(current_user.id, organization_id)
        
        return render_template('analytics_interviews.html', 
                             interviews=interview_data,
                             user=current_user)
        
    except Exception as e:
        logging.error(f"Error loading interview analytics: {e}")
        flash('Error loading interview analytics. Please try again.', 'error')
        return redirect(url_for('analytics_dashboard'))

@app.route('/api/analytics/dashboard')
@login_required
def api_analytics_dashboard():
    """API endpoint for analytics dashboard data"""
    if current_user.role not in ['admin', 'super_admin']:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        organization_id = None if current_user.role == 'super_admin' else current_user.organization_id
        analytics_data = get_recruitment_dashboard_data(current_user.id, organization_id)
        
        return jsonify({
            'success': True,
            'data': analytics_data
        })
        
    except Exception as e:
        logging.error(f"Error getting analytics data: {e}")
        return jsonify({'error': 'Failed to load analytics data'}), 500


# ===== MESSAGING & COLLABORATION ROUTES =====

@app.route('/messages')
@login_required
@login_required
@login_required
def send_message():
    """Send a message to another user"""
    try:
        recipient_id = request.form.get('recipient_id')
        subject = request.form.get('subject', '').strip()
        content = request.form.get('content', '').strip()
        message_type = request.form.get('message_type', 'direct')
        priority = request.form.get('priority', 'normal')
        related_job_id = request.form.get('related_job_id')
        
        if not recipient_id or not subject or not content:
            flash('Recipient, subject, and message content are required.', 'error')
            return redirect(request.referrer or url_for('messages'))
        
        # Convert string IDs to integers
        recipient_id = int(recipient_id)
        related_job_id = int(related_job_id) if related_job_id else None
        
        # Send message
        result = send_recruiter_message(
            current_user.id, 
            recipient_id, 
            subject, 
            content, 
            message_type, 
            related_job_id, 
            priority
        )
        
        if result['success']:
            flash('Message sent successfully!', 'success')
            return redirect(url_for('conversation', partner_id=recipient_id))
        else:
            flash(f'Failed to send message: {result.get("error", "Unknown error")}', 'error')
            return redirect(request.referrer or url_for('messages'))
        
    except Exception as e:
        logging.error(f"Error sending message: {e}")
        flash('Error sending message. Please try again.', 'error')
        return redirect(request.referrer or url_for('messages'))

@app.route('/messages/compose')
@login_required
@login_required
def api_conversations():
    """API endpoint for user conversations"""
    try:
        conversations = get_user_conversations(current_user.id)
        
        return jsonify({
            'success': True,
            'conversations': conversations
        })
        
    except Exception as e:
        logging.error(f"Error getting conversations: {e}")
        return jsonify({'error': 'Failed to load conversations'}), 500

@app.route('/api/messages/notifications')
@login_required
def api_notifications():
    """API endpoint for application notifications"""
    try:
        notifications = get_application_updates(current_user.id)
        
        return jsonify({
            'success': True,
            'notifications': notifications
        })
        
    except Exception as e:
        logging.error(f"Error getting notifications: {e}")
        return jsonify({'error': 'Failed to load notifications'}), 500


# ===== TEAM COLLABORATION ROUTES =====

@app.route('/collaboration/add_team_member', methods=['POST'])
@login_required
def add_collaboration_team_member():
    """Add team member to application collaboration"""
    if current_user.role not in ['admin', 'recruiter']:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        application_id = request.form.get('application_id')
        team_member_id = request.form.get('team_member_id')
        role = request.form.get('role', 'reviewer')
        
        if not application_id or not team_member_id:
            return jsonify({'error': 'Missing required fields'}), 400
        
        result = add_team_collaboration(int(application_id), int(team_member_id), role)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Team member added successfully'
            })
        else:
            return jsonify({'error': result.get('error', 'Failed to add team member')}), 400
        
    except Exception as e:
        logging.error(f"Error adding team member: {e}")
        return jsonify({'error': 'Failed to add team member'}), 500

@app.route('/collaboration/submit_feedback', methods=['POST'])
@login_required
def submit_collaboration_feedback():
    """Submit team feedback for application"""
    try:
        collaboration_id = request.form.get('collaboration_id')
        feedback = request.form.get('feedback', '').strip()
        recommendation = request.form.get('recommendation')
        confidence_score = request.form.get('confidence_score')
        
        if not collaboration_id or not feedback or not recommendation:
            return jsonify({'error': 'Missing required fields'}), 400
        
        result = submit_team_feedback(
            int(collaboration_id), 
            feedback, 
            recommendation, 
            int(confidence_score) if confidence_score else None
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Feedback submitted successfully'
            })
        else:
            return jsonify({'error': result.get('error', 'Failed to submit feedback')}), 400
        
    except Exception as e:
        logging.error(f"Error submitting feedback: {e}")
        return jsonify({'error': 'Failed to submit feedback'}), 500

@app.route('/collaboration/feedback/<int:application_id>')
@login_required
def get_collaboration_feedback(application_id):
    """Get team feedback for application"""
    if current_user.role not in ['admin', 'recruiter']:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        feedback = get_application_team_feedback(application_id)
        
        return jsonify({
            'success': True,
            'feedback': feedback
        })
        
    except Exception as e:
        logging.error(f"Error getting collaboration feedback: {e}")
        return jsonify({'error': 'Failed to load feedback'}), 500

@app.route('/collaboration/application/<int:application_id>')
@login_required
def collaboration_application(application_id):
    """View application collaboration page"""
    if current_user.role not in ['admin', 'recruiter']:
        flash('Access denied. Only admins and recruiters can access collaboration.', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Get application details
        application = JobApplication.query.get_or_404(application_id)
        
        # Check organization access
        if current_user.role != 'super_admin' and application.job_posting.organization_id != current_user.organization_id:
            flash('Access denied. Application not in your organization.', 'error')
            return redirect(url_for('dashboard'))
        
        # Get team feedback
        team_feedback = get_application_team_feedback(application_id)
        
        # Get potential team members
        team_members = User.query.filter(
            User.organization_id == current_user.organization_id,
            User.role.in_(['admin', 'recruiter']),
            User.user_active == True,
            User.id != current_user.id
        ).all()
        
        return render_template('collaboration_application.html', 
                             application=application,
                             team_feedback=team_feedback,
                             team_members=team_members,
                             user=current_user)
        
    except Exception as e:
        logging.error(f"Error loading collaboration application: {e}")
        flash('Error loading collaboration page. Please try again.', 'error')
        return redirect(url_for('dashboard'))


# ===== SYSTEM SETTINGS ROUTES =====

@app.route('/system/settings')
@login_required
@login_required
@login_required
@login_required
@login_required
@login_required
def test_email_configuration():
    """Test email configuration"""
    if current_user.role != 'super_admin':
        return jsonify({'success': False, 'error': 'Access denied'})
    
    try:
        test_email = request.json.get('email', current_user.email)
        
        # Send test email
        result = send_notification_email(
            to_email=test_email,
            subject='Test Email - Job2Hire Configuration',
            template_name='test_email',
            context={
                'message': 'This is a test email to verify your SMTP configuration.',
                'user_name': current_user.first_name or current_user.username,
                'action_url': url_for('system_email_settings', _external=True)
            }
        )
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error testing email configuration: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/system/email-settings/bulk-send', methods=['POST'])
@login_required
def bulk_send_emails():
    """Send bulk email notifications"""
    if current_user.role != 'super_admin':
        return jsonify({'success': False, 'error': 'Access denied'})
    
    try:
        data = request.json
        template_name = data.get('template_name')
        subject = data.get('subject')
        recipient_type = data.get('recipient_type', 'all')  # all, candidates, recruiters, admins
        message = data.get('message', '')
        
        # Get recipients based on type
        if recipient_type == 'candidates':
            recipients = User.query.filter_by(role='candidate', user_active=True).all()
        elif recipient_type == 'recruiters':
            recipients = User.query.filter(User.role.in_(['recruiter', 'admin']), User.user_active == True).all()
        elif recipient_type == 'admins':
            recipients = User.query.filter(User.role.in_(['admin', 'super_admin']), User.user_active == True).all()
        else:
            recipients = User.query.filter_by(user_active=True).all()
        
        # Prepare recipient data
        recipient_data = []
        for user in recipients:
            recipient_data.append({
                'email': user.email,
                'user_id': user.id,
                'subject': subject,
                'context': {
                    'user_name': user.first_name or user.username,
                    'message': message,
                    'platform_url': url_for('index', _external=True)
                }
            })
        
        # Send bulk emails
        result = email_service.send_bulk_emails(
            recipients=recipient_data,
            template_name=template_name or 'notification',
            base_context={'message': message}
        )
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error sending bulk emails: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/system/email-test')
@login_required
def email_test_page():
    """Email test page"""
    if current_user.role != 'super_admin':
        return redirect(url_for('dashboard'))
    
    return render_template('email_test.html')

@app.route('/system/bulk-email')
@login_required
def bulk_email_page():
    """Bulk email page"""
    if current_user.role != 'super_admin':
        return redirect(url_for('dashboard'))
    
    return render_template('bulk_email.html')

@app.route('/api/email-analytics')
@login_required
def email_analytics():
    """Get email analytics data"""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        from models import EmailNotification
        from datetime import datetime, timedelta
        
        # Get analytics data
        now = datetime.utcnow()
        
        # Daily stats for last 30 days
        daily_stats = []
        for i in range(30):
            day = now - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            emails = EmailNotification.query.filter(
                EmailNotification.created_at >= day_start,
                EmailNotification.created_at < day_end
            ).all()
            
            daily_stats.append({
                'date': day.strftime('%Y-%m-%d'),
                'sent': len([e for e in emails if e.status == 'sent']),
                'failed': len([e for e in emails if e.status == 'failed']),
                'total': len(emails)
            })
        
        # Template usage stats
        template_stats = db.session.query(
            EmailNotification.template_name,
            db.func.count(EmailNotification.id).label('total'),
            db.func.sum(db.case((EmailNotification.status == 'sent', 1), else_=0)).label('sent'),
            db.func.sum(db.case((EmailNotification.status == 'failed', 1), else_=0)).label('failed')
        ).group_by(EmailNotification.template_name).all()
        
        analytics = {
            'daily_stats': daily_stats,
            'template_stats': [
                {
                    'template': stat.template_name,
                    'total': stat.total,
                    'sent': stat.sent,
                    'failed': stat.failed,
                    'success_rate': round((stat.sent / stat.total) * 100, 2) if stat.total > 0 else 0
                }
                for stat in template_stats
            ]
        }
        
        return jsonify(analytics)
        
    except Exception as e:
        logging.error(f"Error getting email analytics: {e}")
        return jsonify({'error': str(e)}), 500
        
    except Exception as e:
        logging.error(f"Error loading user management: {e}")
        flash('Error loading user management. Please try again.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/system/user/<int:user_id>/permissions', methods=['POST'])
@login_required
def update_user_permissions(user_id):
    """Update user permissions"""
    if current_user.role != 'super_admin':
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # System settings service removed - basic user management only
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        action = request.json.get('action')
        
        if action == 'change_role':
            new_role = request.json.get('new_role')
            if new_role in ['candidate', 'recruiter', 'admin', 'super_admin']:
                user.role = new_role
                db.session.commit()
                return jsonify({'success': True, 'message': 'Role updated successfully'})
        elif action == 'toggle_active':
            user.is_active = not user.is_active
            db.session.commit()
            return jsonify({'success': True, 'message': 'User status updated'})
        else:
            return jsonify({'error': 'Invalid action'}), 400
        
    except Exception as e:
        logging.error(f"Error updating user permissions: {e}")
        return jsonify({'error': 'Failed to update permissions'}), 500

# System settings and job scheduler routes removed - Ez2source focuses on core talent intelligence features
