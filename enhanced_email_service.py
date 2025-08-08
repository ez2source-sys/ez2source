"""
Enhanced Email Notification Service for Ez2Hire
Complete email integration with SMTP configuration, professional templates, and delivery tracking
"""

import os
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Dict, List, Optional, Any
from jinja2 import Template
from models import db, User, Organization, AuditLog, EmailNotification, NotificationPreference

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedEmailService:
    """Comprehensive email service with SMTP configuration and template management"""
    
    def __init__(self):
        self.smtp_config = self._load_smtp_config()
        self.template_cache = {}
        self.delivery_stats = {
            'total_sent': 0,
            'total_failed': 0,
            'last_sent': None
        }
    
    def _load_smtp_config(self) -> Dict[str, Any]:
        """Load SMTP configuration from environment variables"""
        return {
            'host': os.environ.get('SMTP_HOST', 'smtp.gmail.com'),
            'port': int(os.environ.get('SMTP_PORT', '587')),
            'username': os.environ.get('SMTP_USERNAME', ''),
            'password': os.environ.get('SMTP_PASSWORD', ''),
            'use_tls': os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true',
            'from_email': os.environ.get('SMTP_FROM_EMAIL', 'noreply@ez2source.com'),
            'from_name': os.environ.get('SMTP_FROM_NAME', 'Ez2source Platform')
        }
    
    def send_email(self, to_email: str, subject: str, template_name: str, 
                   context: Dict[str, Any], user_id: Optional[int] = None,
                   attachments: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Send email with professional template and delivery tracking
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            template_name: Template name (e.g., 'user_invitation', 'interview_reminder')
            context: Template context variables
            user_id: User ID for notification preferences
            attachments: List of file attachments
            
        Returns:
            Dict with success status and tracking information
        """
        try:
            # Check user notification preferences
            if user_id and not self._check_user_preferences(user_id, template_name):
                logger.info(f"Email skipped due to user preferences: {to_email}")
                return {
                    'success': False,
                    'error': 'User has disabled this notification type',
                    'skipped': True
                }
            
            # Load and render template
            html_content, text_content = self._render_template(template_name, context)
            
            # Create email message
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = f"{self.smtp_config['from_name']} <{self.smtp_config['from_email']}>"
            message['To'] = to_email
            
            # Add text and HTML parts
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            message.attach(text_part)
            message.attach(html_part)
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    self._add_attachment(message, attachment)
            
            # Send email
            delivery_result = self._send_smtp_email(message, to_email)
            
            # Log delivery attempt
            self._log_email_delivery(to_email, subject, template_name, user_id, delivery_result)
            
            return delivery_result
            
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _render_template(self, template_name: str, context: Dict[str, Any]) -> tuple:
        """Render email template with context"""
        try:
            # Get template from cache or load it
            if template_name not in self.template_cache:
                html_template = self._load_template(f"{template_name}.html")
                text_template = self._load_template(f"{template_name}.txt")
                self.template_cache[template_name] = {
                    'html': html_template,
                    'text': text_template
                }
            
            templates = self.template_cache[template_name]
            
            # Add common context variables
            context.update({
                'platform_name': 'Ez2source',
                'platform_url': 'https://ez2source.com',
                'support_email': 'support@ez2source.com',
                'current_year': datetime.now().year,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            # Render templates
            html_content = templates['html'].render(**context)
            text_content = templates['text'].render(**context)
            
            return html_content, text_content
            
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {e}")
            return self._get_fallback_template(context)
    
    def _load_template(self, template_file: str) -> Template:
        """Load template from file"""
        try:
            template_path = f"templates/email/{template_file}"
            with open(template_path, 'r', encoding='utf-8') as f:
                return Template(f.read())
        except FileNotFoundError:
            logger.warning(f"Template file not found: {template_file}")
            return Template(self._get_default_template())
    
    def _get_default_template(self) -> str:
        """Get default email template"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{{ subject }}</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #667eea; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f9f9f9; }
                .footer { background: #333; color: white; padding: 15px; text-align: center; font-size: 12px; }
                .btn { display: inline-block; padding: 12px 24px; background: #667eea; color: white; text-decoration: none; border-radius: 4px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{{ platform_name }}</h1>
                </div>
                <div class="content">
                    <p>{{ message | default('This is an automated notification from Ez2source.') }}</p>
                    {% if action_url %}
                    <p><a href="{{ action_url }}" class="btn">Take Action</a></p>
                    {% endif %}
                </div>
                <div class="footer">
                    <p>&copy; {{ current_year }} {{ platform_name }}. All rights reserved.</p>
                    <p>If you have questions, contact us at {{ support_email }}</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _get_fallback_template(self, context: Dict[str, Any]) -> tuple:
        """Get fallback template when template loading fails"""
        html_content = f"""
        <html>
        <body>
            <h2>Ez2source Notification</h2>
            <p>{context.get('message', 'This is an automated notification.')}</p>
            <p>Best regards,<br>Ez2source Team</p>
        </body>
        </html>
        """
        
        text_content = f"""
        Ez2source Notification
        
        {context.get('message', 'This is an automated notification.')}
        
        Best regards,
        Ez2source Team
        """
        
        return html_content, text_content
    
    def _send_smtp_email(self, message: MIMEMultipart, to_email: str) -> Dict[str, Any]:
        """Send email via SMTP"""
        try:
            # Create SMTP connection
            server = smtplib.SMTP(self.smtp_config['host'], self.smtp_config['port'])
            
            if self.smtp_config['use_tls']:
                server.starttls()
            
            if self.smtp_config['username'] and self.smtp_config['password']:
                server.login(self.smtp_config['username'], self.smtp_config['password'])
            
            # Send email
            server.send_message(message)
            server.quit()
            
            # Update delivery stats
            self.delivery_stats['total_sent'] += 1
            self.delivery_stats['last_sent'] = datetime.utcnow()
            
            logger.info(f"Email sent successfully to {to_email}")
            return {
                'success': True,
                'message': 'Email sent successfully',
                'timestamp': datetime.utcnow().isoformat(),
                'recipient': to_email
            }
            
        except Exception as e:
            self.delivery_stats['total_failed'] += 1
            logger.error(f"SMTP error sending to {to_email}: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _add_attachment(self, message: MIMEMultipart, attachment: Dict[str, Any]):
        """Add file attachment to email"""
        try:
            with open(attachment['path'], 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename= {attachment["filename"]}'
                )
                message.attach(part)
        except Exception as e:
            logger.error(f"Error adding attachment: {e}")
    
    def _check_user_preferences(self, user_id: int, template_name: str) -> bool:
        """Check if user has enabled this notification type"""
        try:
            preference = NotificationPreference.query.filter_by(
                user_id=user_id,
                notification_type=template_name
            ).first()
            
            if preference:
                return preference.enabled
            else:
                # Default to enabled if no preference set
                return True
                
        except Exception as e:
            logger.error(f"Error checking user preferences: {e}")
            return True
    
    def _log_email_delivery(self, to_email: str, subject: str, template_name: str, 
                           user_id: Optional[int], result: Dict[str, Any]):
        """Log email delivery attempt"""
        try:
            email_log = EmailNotification(
                user_id=user_id,
                to_email=to_email,
                subject=subject,
                template_name=template_name,
                status='sent' if result['success'] else 'failed',
                error_message=result.get('error'),
                sent_at=datetime.utcnow() if result['success'] else None,
                created_at=datetime.utcnow()
            )
            
            db.session.add(email_log)
            db.session.commit()
            
        except Exception as e:
            logger.error(f"Error logging email delivery: {e}")
    
    def get_delivery_stats(self) -> Dict[str, Any]:
        """Get email delivery statistics"""
        try:
            # Get recent delivery stats from database
            recent_emails = EmailNotification.query.filter(
                EmailNotification.created_at >= datetime.utcnow().date()
            ).all()
            
            stats = {
                'today_sent': len([e for e in recent_emails if e.status == 'sent']),
                'today_failed': len([e for e in recent_emails if e.status == 'failed']),
                'total_sent': self.delivery_stats['total_sent'],
                'total_failed': self.delivery_stats['total_failed'],
                'last_sent': self.delivery_stats['last_sent'],
                'smtp_configured': bool(self.smtp_config['username']),
                'smtp_host': self.smtp_config['host'],
                'smtp_port': self.smtp_config['port']
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting delivery stats: {e}")
            return {
                'today_sent': 0,
                'today_failed': 0,
                'total_sent': 0,
                'total_failed': 0,
                'error': str(e)
            }
    
    def send_bulk_emails(self, recipients: List[Dict[str, Any]], 
                        template_name: str, base_context: Dict[str, Any]) -> Dict[str, Any]:
        """Send bulk emails with personalized content"""
        results = {
            'sent': 0,
            'failed': 0,
            'skipped': 0,
            'details': []
        }
        
        for recipient in recipients:
            try:
                # Merge base context with recipient-specific context
                context = {**base_context, **recipient.get('context', {})}
                
                result = self.send_email(
                    to_email=recipient['email'],
                    subject=recipient.get('subject', base_context.get('subject', 'Ez2source Notification')),
                    template_name=template_name,
                    context=context,
                    user_id=recipient.get('user_id')
                )
                
                if result['success']:
                    results['sent'] += 1
                elif result.get('skipped'):
                    results['skipped'] += 1
                else:
                    results['failed'] += 1
                
                results['details'].append({
                    'email': recipient['email'],
                    'result': result
                })
                
            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'email': recipient['email'],
                    'result': {'success': False, 'error': str(e)}
                })
                logger.error(f"Error sending bulk email to {recipient['email']}: {e}")
        
        return results

# Global service instance
email_service = EnhancedEmailService()

# Convenience functions
def send_notification_email(to_email: str, subject: str, template_name: str, 
                          context: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
    """Send notification email"""
    return email_service.send_email(to_email, subject, template_name, context, user_id)

def send_user_invitation_email(user: User, organization: Organization, 
                              temporary_password: str) -> Dict[str, Any]:
    """Send user invitation email with credentials"""
    context = {
        'user_name': user.first_name or user.username,
        'username': user.username,
        'temporary_password': temporary_password,
        'organization_name': organization.name,
        'login_url': 'https://ez2source.com/login',
        'role': user.role.replace('_', ' ').title(),
        'message': f'Welcome to Ez2source! Your account has been created for {organization.name}.'
    }
    
    return email_service.send_email(
        to_email=user.email,
        subject=f'Welcome to Ez2source - {organization.name}',
        template_name='user_invitation',
        context=context,
        user_id=user.id
    )

def send_interview_reminder_email(user: User, interview_title: str, 
                                interview_date: str, interview_url: str) -> Dict[str, Any]:
    """Send interview reminder email"""
    context = {
        'user_name': user.first_name or user.username,
        'interview_title': interview_title,
        'interview_date': interview_date,
        'interview_url': interview_url,
        'message': f'Reminder: You have an upcoming interview scheduled for {interview_date}.'
    }
    
    return email_service.send_email(
        to_email=user.email,
        subject=f'Interview Reminder - {interview_title}',
        template_name='interview_reminder',
        context=context,
        user_id=user.id
    )

def send_job_application_notification(recruiter: User, candidate: User, 
                                    job_title: str, application_url: str) -> Dict[str, Any]:
    """Send job application notification to recruiter"""
    context = {
        'recruiter_name': recruiter.first_name or recruiter.username,
        'candidate_name': f"{candidate.first_name} {candidate.last_name}".strip() or candidate.username,
        'job_title': job_title,
        'application_url': application_url,
        'message': f'A new application has been received for {job_title}.'
    }
    
    return email_service.send_email(
        to_email=recruiter.email,
        subject=f'New Application - {job_title}',
        template_name='job_application_notification',
        context=context,
        user_id=recruiter.id
    )

def get_email_delivery_stats() -> Dict[str, Any]:
    """Get email delivery statistics"""
    return email_service.get_delivery_stats()