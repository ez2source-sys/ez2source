"""
Communication & Collaboration Service for Job2Hire
Recruiter-candidate messaging system, notifications, and team collaboration
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, text, and_, or_, desc
from sqlalchemy.orm import joinedload
from app import db
from models import User, Organization, JobPosting, JobApplication, Interview, AuditLog, Message, NotificationSettings, TeamCollaboration

class MessagingService:
    """Comprehensive messaging and communication service"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def send_message(self, sender_id: int, recipient_id: int, subject: str, content: str, 
                    message_type: str = 'direct', related_job_id: Optional[int] = None, 
                    related_application_id: Optional[int] = None, priority: str = 'normal') -> Dict:
        """
        Send a message between users
        
        Args:
            sender_id: ID of the sender
            recipient_id: ID of the recipient
            subject: Message subject
            content: Message content
            message_type: Type of message (direct, application, interview, system)
            related_job_id: Optional related job posting ID
            related_application_id: Optional related application ID
            priority: Message priority (low, normal, high, urgent)
            
        Returns:
            Dict with success status and message details
        """
        try:
            # Validate users
            sender = User.query.get(sender_id)
            recipient = User.query.get(recipient_id)
            
            if not sender or not recipient:
                return {'success': False, 'error': 'Invalid sender or recipient'}
            
            # Check permissions
            if not self._can_send_message(sender, recipient):
                return {'success': False, 'error': 'Permission denied'}
            
            # Create message
            message = Message(
                sender_id=sender_id,
                recipient_id=recipient_id,
                subject=subject,
                content=content,
                message_type=message_type,
                related_job_id=related_job_id,
                related_application_id=related_application_id,
                priority=priority
            )
            
            db.session.add(message)
            db.session.commit()
            
            # Send notification if enabled
            self._send_message_notification(recipient, message)
            
            # Log activity
            self._log_message_activity(sender_id, recipient_id, message.id, 'sent')
            
            return {
                'success': True,
                'message_id': message.id,
                'sent_at': message.created_at.isoformat()
            }
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error sending message: {e}")
            return {'success': False, 'error': 'Failed to send message'}
    
    def get_conversations(self, user_id: int, limit: int = 50) -> List[Dict]:
        """
        Get user's conversations with latest messages
        
        Args:
            user_id: User ID
            limit: Number of conversations to return
            
        Returns:
            List of conversation dictionaries
        """
        try:
            # Get latest messages for each conversation
            conversations = db.session.query(Message).filter(
                or_(Message.sender_id == user_id, Message.recipient_id == user_id)
            ).order_by(desc(Message.created_at)).limit(limit * 2).all()
            
            # Group by conversation partner
            conversation_map = {}
            for message in conversations:
                partner_id = message.recipient_id if message.sender_id == user_id else message.sender_id
                
                if partner_id not in conversation_map:
                    partner = User.query.get(partner_id)
                    if partner:
                        conversation_map[partner_id] = {
                            'partner_id': partner_id,
                            'partner_name': f"{partner.first_name} {partner.last_name}",
                            'partner_role': partner.role,
                            'partner_organization': partner.organization.name if partner.organization else None,
                            'latest_message': {
                                'id': message.id,
                                'subject': message.subject,
                                'content': message.content,
                                'created_at': message.created_at.strftime('%Y-%m-%d'),
                                'created_at_time': message.created_at.strftime('%H:%M'),
                                'is_read': message.is_read,
                                'sender_id': message.sender_id,
                                'recipient_id': message.recipient_id
                            },
                            'unread_count': 0
                        }
                
                # Count unread messages
                if message.recipient_id == user_id and not message.is_read:
                    conversation_map[partner_id]['unread_count'] += 1
            
            # Convert to list and sort by latest message
            conversations_list = list(conversation_map.values())
            # Sort by the original message object's created_at since we need it for sorting
            conversations_list.sort(key=lambda x: Message.query.get(x['latest_message']['id']).created_at, reverse=True)
            
            return conversations_list[:limit]
            
        except Exception as e:
            self.logger.error(f"Error getting conversations: {e}")
            return []
    
    def get_messages(self, user_id: int, partner_id: int, limit: int = 50) -> List[Dict]:
        """
        Get messages between two users
        
        Args:
            user_id: Current user ID
            partner_id: Conversation partner ID
            limit: Number of messages to return
            
        Returns:
            List of message dictionaries
        """
        try:
            messages = db.session.query(Message).filter(
                or_(
                    and_(Message.sender_id == user_id, Message.recipient_id == partner_id),
                    and_(Message.sender_id == partner_id, Message.recipient_id == user_id)
                )
            ).order_by(desc(Message.created_at)).limit(limit).all()
            
            # Mark messages as read
            unread_messages = db.session.query(Message).filter(
                Message.sender_id == partner_id,
                Message.recipient_id == user_id,
                Message.is_read == False
            ).all()
            
            for message in unread_messages:
                message.is_read = True
                message.read_at = datetime.utcnow()
            
            db.session.commit()
            
            # Format messages
            formatted_messages = []
            for message in reversed(messages):
                formatted_messages.append({
                    'id': message.id,
                    'sender_id': message.sender_id,
                    'sender_name': f"{message.sender.first_name} {message.sender.last_name}",
                    'subject': message.subject,
                    'content': message.content,
                    'message_type': message.message_type,
                    'priority': message.priority,
                    'created_at': message.created_at.isoformat(),
                    'is_read': message.is_read,
                    'read_at': message.read_at.isoformat() if message.read_at else None
                })
            
            return formatted_messages
            
        except Exception as e:
            self.logger.error(f"Error getting messages: {e}")
            return []
    
    def get_application_notifications(self, user_id: int) -> List[Dict]:
        """
        Get application update notifications for user
        
        Args:
            user_id: User ID
            
        Returns:
            List of notification dictionaries
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return []
            
            notifications = []
            
            if user.role == 'candidate':
                # Get application status updates
                applications = db.session.query(JobApplication).filter(
                    JobApplication.user_id == user_id,
                    JobApplication.response_received == True
                ).order_by(desc(JobApplication.response_received_date)).limit(10).all()
                
                for app in applications:
                    notifications.append({
                        'type': 'application_update',
                        'title': f"Application Update - {app.job_posting.title}",
                        'message': f"Your application status has been updated to: {app.status}",
                        'job_title': app.job_posting.title,
                        'company': app.job_posting.company.name,
                        'status': app.status,
                        'date': app.response_received_date.isoformat() if app.response_received_date else None
                    })
            
            elif user.role in ['admin', 'super_admin']:
                # Get new applications for admin
                recent_apps = db.session.query(JobApplication).join(JobPosting).filter(
                    JobApplication.application_date >= datetime.utcnow() - timedelta(days=7)
                ).order_by(desc(JobApplication.application_date)).limit(10).all()
                
                for app in recent_apps:
                    notifications.append({
                        'type': 'new_application',
                        'title': f"New Application - {app.job_posting.title}",
                        'message': f"New application from {app.user.first_name} {app.user.last_name}",
                        'candidate_name': f"{app.user.first_name} {app.user.last_name}",
                        'job_title': app.job_posting.title,
                        'date': app.application_date.isoformat()
                    })
            
            return notifications
            
        except Exception as e:
            self.logger.error(f"Error getting application notifications: {e}")
            return []
    
    def create_team_collaboration(self, application_id: int, team_member_id: int, role: str) -> Dict:
        """
        Add team member to application collaboration
        
        Args:
            application_id: Application ID
            team_member_id: Team member user ID
            role: Role in collaboration (reviewer, decision_maker, observer)
            
        Returns:
            Dict with success status
        """
        try:
            # Check if collaboration already exists
            existing = db.session.query(TeamCollaboration).filter(
                TeamCollaboration.application_id == application_id,
                TeamCollaboration.team_member_id == team_member_id
            ).first()
            
            if existing:
                return {'success': False, 'error': 'Team member already added'}
            
            # Create collaboration
            collaboration = TeamCollaboration(
                application_id=application_id,
                team_member_id=team_member_id,
                role=role
            )
            
            db.session.add(collaboration)
            db.session.commit()
            
            return {'success': True, 'collaboration_id': collaboration.id}
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error creating team collaboration: {e}")
            return {'success': False, 'error': 'Failed to add team member'}
    
    def add_team_feedback(self, collaboration_id: int, feedback: str, recommendation: str, confidence_score: int) -> Dict:
        """
        Add team member feedback to application
        
        Args:
            collaboration_id: Collaboration ID
            feedback: Feedback text
            recommendation: Recommendation (hire, reject, interview, hold)
            confidence_score: Confidence score (1-10)
            
        Returns:
            Dict with success status
        """
        try:
            collaboration = TeamCollaboration.query.get(collaboration_id)
            if not collaboration:
                return {'success': False, 'error': 'Collaboration not found'}
            
            collaboration.feedback = feedback
            collaboration.recommendation = recommendation
            collaboration.confidence_score = confidence_score
            collaboration.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            return {'success': True, 'updated_at': collaboration.updated_at.isoformat()}
            
        except Exception as e:
            db.session.rollback()
            self.logger.error(f"Error adding team feedback: {e}")
            return {'success': False, 'error': 'Failed to add feedback'}
    
    def get_team_feedback(self, application_id: int) -> List[Dict]:
        """
        Get team feedback for application
        
        Args:
            application_id: Application ID
            
        Returns:
            List of feedback dictionaries
        """
        try:
            feedback_list = db.session.query(TeamCollaboration).filter(
                TeamCollaboration.application_id == application_id
            ).all()
            
            formatted_feedback = []
            for feedback in feedback_list:
                formatted_feedback.append({
                    'id': feedback.id,
                    'team_member_name': f"{feedback.team_member.first_name} {feedback.team_member.last_name}",
                    'role': feedback.role,
                    'feedback': feedback.feedback,
                    'recommendation': feedback.recommendation,
                    'confidence_score': feedback.confidence_score,
                    'created_at': feedback.created_at.isoformat(),
                    'updated_at': feedback.updated_at.isoformat()
                })
            
            return formatted_feedback
            
        except Exception as e:
            self.logger.error(f"Error getting team feedback: {e}")
            return []
    
    def _can_send_message(self, sender: User, recipient: User) -> bool:
        """Check if sender can send message to recipient"""
        # Same organization members can message each other
        if sender.organization_id == recipient.organization_id:
            return True
        
        # Super admin can message anyone
        if sender.role == 'super_admin':
            return True
        
        # Cross-organizational candidates can be messaged by any recruiter
        if recipient.role == 'candidate' and recipient.cross_org_accessible:
            return True
        
        return False
    
    def _send_message_notification(self, recipient: User, message: Message):
        """Send notification about new message"""
        try:
            # Check user notification settings
            settings = NotificationSettings.query.filter_by(user_id=recipient.id).first()
            
            if not settings or not settings.message_notifications:
                return
            
            # Send email notification if enabled
            if settings.email_notifications:
                self._send_email_notification(recipient, message)
            
            # Send push notification if enabled
            if settings.push_notifications:
                self._send_push_notification(recipient, message)
                
        except Exception as e:
            self.logger.error(f"Error sending message notification: {e}")
    
    def _send_email_notification(self, recipient: User, message: Message):
        """Send email notification about new message"""
        # This would integrate with email service
        pass
    
    def _send_push_notification(self, recipient: User, message: Message):
        """Send push notification about new message"""
        # This would integrate with push notification service
        pass
    
    def _log_message_activity(self, sender_id: int, recipient_id: int, message_id: int, action: str):
        """Log message activity for audit trail"""
        try:
            audit_log = AuditLog(
                user_id=sender_id,
                action=f"message_{action}",
                resource_type="message",
                resource_id=message_id,
                details=f"Message {action} to user {recipient_id}",
                timestamp=datetime.utcnow()
            )
            db.session.add(audit_log)
            db.session.commit()
            
        except Exception as e:
            self.logger.error(f"Error logging message activity: {e}")

# Service function wrappers
def send_recruiter_message(sender_id: int, recipient_id: int, subject: str, content: str, 
                          message_type: str = 'direct', related_job_id: Optional[int] = None, 
                          priority: str = 'normal') -> Dict:
    """Send message from recruiter to candidate"""
    service = MessagingService()
    return service.send_message(sender_id, recipient_id, subject, content, message_type, related_job_id, None, priority)

def get_user_conversations(user_id: int, limit: int = 50) -> List[Dict]:
    """Get user's conversations"""
    service = MessagingService()
    return service.get_conversations(user_id, limit)

def get_conversation_messages(user_id: int, partner_id: int, limit: int = 50) -> List[Dict]:
    """Get messages between two users"""
    service = MessagingService()
    return service.get_messages(user_id, partner_id, limit)

def get_application_updates(user_id: int) -> List[Dict]:
    """Get application update notifications"""
    service = MessagingService()
    return service.get_application_notifications(user_id)

def add_team_collaboration(application_id: int, team_member_id: int, role: str) -> Dict:
    """Add team member to application collaboration"""
    service = MessagingService()
    return service.create_team_collaboration(application_id, team_member_id, role)

def submit_team_feedback(collaboration_id: int, feedback: str, recommendation: str, confidence_score: int) -> Dict:
    """Submit team feedback for application"""
    service = MessagingService()
    return service.add_team_feedback(collaboration_id, feedback, recommendation, confidence_score)

def get_application_team_feedback(application_id: int) -> List[Dict]:
    """Get team feedback for application"""
    service = MessagingService()
    return service.get_team_feedback(application_id)