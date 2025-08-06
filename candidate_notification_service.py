"""
Candidate Notification Service for Ez2Hire
Handles automated email notifications for technical interview decisions
"""

import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from enhanced_email_service import EnhancedEmailService as EmailService
from models import User, TechnicalInterviewFeedback, TechnicalInterviewAssignment, Organization, db
from app import app

logger = logging.getLogger(__name__)

class CandidateNotificationService:
    """Service for sending automated candidate notifications based on interview decisions"""
    
    def __init__(self):
        self.email_service = EmailService()
    
    def send_decision_notification(self, feedback_id: int, hr_user_id: int) -> bool:
        """
        Send notification to candidate based on technical interview decision
        
        Args:
            feedback_id: ID of the technical interview feedback
            hr_user_id: ID of the HR user triggering the notification
            
        Returns:
            bool: True if notification sent successfully, False otherwise
        """
        try:
            # Get the feedback record
            feedback = TechnicalInterviewFeedback.query.get(feedback_id)
            if not feedback:
                logger.error(f"Feedback not found for ID: {feedback_id}")
                return False
            
            # Get the assignment to find candidate
            assignment = TechnicalInterviewAssignment.query.get(feedback.assignment_id)
            if not assignment:
                logger.error(f"Assignment not found for feedback ID: {feedback_id}")
                return False
            
            # Get candidate details
            candidate = User.query.get(assignment.candidate_id)
            if not candidate:
                logger.error(f"Candidate not found for assignment ID: {assignment.id}")
                return False
            
            # Get organization details
            organization = Organization.query.get(assignment.organization_id)
            if not organization:
                logger.error(f"Organization not found for assignment ID: {assignment.id}")
                return False
            
            # Get HR user details
            hr_user = User.query.get(hr_user_id)
            if not hr_user:
                logger.error(f"HR user not found for ID: {hr_user_id}")
                return False
            
            # Determine notification type based on decision
            if feedback.decision == 'selected':
                return self._send_acceptance_email(candidate, organization, assignment, hr_user)
            elif feedback.decision == 'rejected':
                return self._send_rejection_email(candidate, organization, assignment, hr_user)
            else:
                logger.warning(f"No notification sent - decision is '{feedback.decision}' for feedback ID: {feedback_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending decision notification: {str(e)}")
            return False
    
    def _send_acceptance_email(self, candidate: User, organization: Organization, 
                              assignment: TechnicalInterviewAssignment, hr_user: User) -> bool:
        """Send acceptance email to candidate"""
        
        candidate_name = f"{candidate.first_name} {candidate.last_name}" if candidate.first_name else candidate.username
        company_name = organization.name
        position_title = assignment.interview.title if assignment.interview else "Technical Position"
        
        subject = f"Congratulations and Welcome to {company_name}!"
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
                <h1 style="margin: 0; font-size: 28px;">Congratulations!</h1>
                <p style="margin: 10px 0 0 0; font-size: 18px;">Welcome to {company_name}</p>
            </div>
            
            <div style="background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #e2e8f0;">
                <p style="font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
                    Dear {candidate_name},
                </p>
                
                <p style="font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
                    I'm delighted to offer you the position of <strong>{position_title}</strong> at <strong>{company_name}</strong>. 
                    We were impressed by your technical expertise and believe you'll be a great fit for our team.
                </p>
                
                <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #2563eb; margin: 20px 0;">
                    <h3 style="color: #2563eb; margin: 0 0 15px 0;">Next Steps</h3>
                    <ul style="margin: 0; padding-left: 20px;">
                        <li style="margin-bottom: 8px;">A formal offer letter will be sent to you within 24 hours</li>
                        <li style="margin-bottom: 8px;">HR will contact you to discuss start date and salary details</li>
                        <li style="margin-bottom: 8px;">Please feel free to reach out with any questions</li>
                    </ul>
                </div>
                
                <p style="font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
                    Welcome aboard—we look forward to your contributions and to seeing you thrive here!
                </p>
                
                <p style="font-size: 16px; line-height: 1.6; margin-bottom: 10px;">
                    Best regards,<br>
                    <strong>{hr_user.first_name} {hr_user.last_name}</strong><br>
                    {company_name} - HR Department
                </p>
            </div>
            
            <div style="text-align: center; margin-top: 20px; padding: 20px; background: #f1f5f9; border-radius: 8px;">
                <p style="margin: 0; font-size: 14px; color: #64748b;">
                    This message was sent from Ez2Hire - AI-Powered Talent Intelligence Platform
                </p>
            </div>
        </div>
        """
        
        text_content = f"""
        Dear {candidate_name},
        
        I'm delighted to offer you the position of {position_title} at {company_name}. We were impressed by your technical expertise and believe you'll be a great fit for our team.
        
        Next Steps:
        - A formal offer letter will be sent to you within 24 hours
        - HR will contact you to discuss start date and salary details
        - Please feel free to reach out with any questions
        
        Welcome aboard—we look forward to your contributions and to seeing you thrive here!
        
        Best regards,
        {hr_user.first_name} {hr_user.last_name}
        {company_name} - HR Department
        """
        
        return self.email_service.send_email(
            to_email=candidate.email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
    
    def _send_rejection_email(self, candidate: User, organization: Organization, 
                             assignment: TechnicalInterviewAssignment, hr_user: User) -> bool:
        """Send rejection email to candidate"""
        
        candidate_name = f"{candidate.first_name} {candidate.last_name}" if candidate.first_name else candidate.username
        company_name = organization.name
        position_title = assignment.interview.title if assignment.interview else "Technical Position"
        
        subject = f"Your Application for {position_title} at {company_name}"
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #64748b 0%, #475569 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center;">
                <h1 style="margin: 0; font-size: 28px;">Thank You</h1>
                <p style="margin: 10px 0 0 0; font-size: 18px;">For Your Interest in {company_name}</p>
            </div>
            
            <div style="background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #e2e8f0;">
                <p style="font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
                    Dear {candidate_name},
                </p>
                
                <p style="font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
                    Thank you for taking the time to interview for the <strong>{position_title}</strong> role at <strong>{company_name}</strong>. 
                    We enjoyed learning more about your background and skills.
                </p>
                
                <p style="font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
                    After careful consideration, we have decided to move forward with another candidate whose experience more closely matches our current needs. 
                    This was not an easy decision—your qualifications are impressive, and we appreciate the effort you put into the process.
                </p>
                
                <div style="background: white; padding: 20px; border-radius: 8px; border-left: 4px solid #64748b; margin: 20px 0;">
                    <h3 style="color: #64748b; margin: 0 0 15px 0;">Looking Forward</h3>
                    <p style="margin: 0; font-size: 16px; line-height: 1.6;">
                        We will keep your resume on file, and should a more fitting opportunity arise, we would welcome the chance to reconnect. 
                        In the meantime, we wish you every success in your career.
                    </p>
                </div>
                
                <p style="font-size: 16px; line-height: 1.6; margin-bottom: 20px;">
                    Thank you again for your interest in {company_name}.
                </p>
                
                <p style="font-size: 16px; line-height: 1.6; margin-bottom: 10px;">
                    Best regards,<br>
                    <strong>{hr_user.first_name} {hr_user.last_name}</strong><br>
                    {company_name} - HR Department
                </p>
            </div>
            
            <div style="text-align: center; margin-top: 20px; padding: 20px; background: #f1f5f9; border-radius: 8px;">
                <p style="margin: 0; font-size: 14px; color: #64748b;">
                    This message was sent from Ez2Hire - AI-Powered Talent Intelligence Platform
                </p>
            </div>
        </div>
        """
        
        text_content = f"""
        Dear {candidate_name},
        
        Thank you for taking the time to interview for the {position_title} role at {company_name}. We enjoyed learning more about your background and skills.
        
        After careful consideration, we have decided to move forward with another candidate whose experience more closely matches our current needs. This was not an easy decision—your qualifications are impressive, and we appreciate the effort you put into the process.
        
        We will keep your resume on file, and should a more fitting opportunity arise, we would welcome the chance to reconnect. In the meantime, we wish you every success in your career.
        
        Thank you again for your interest in {company_name}.
        
        Best regards,
        {hr_user.first_name} {hr_user.last_name}
        {company_name} - HR Department
        """
        
        return self.email_service.send_email(
            to_email=candidate.email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
    
    def send_bulk_decision_notifications(self, feedback_ids: list, hr_user_id: int) -> Dict[str, int]:
        """
        Send decision notifications for multiple feedback records
        
        Args:
            feedback_ids: List of feedback IDs to process
            hr_user_id: ID of the HR user triggering the notifications
            
        Returns:
            Dict with counts of successful and failed notifications
        """
        results = {
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }
        
        for feedback_id in feedback_ids:
            try:
                if self.send_decision_notification(feedback_id, hr_user_id):
                    results['successful'] += 1
                else:
                    results['failed'] += 1
            except Exception as e:
                logger.error(f"Error processing feedback ID {feedback_id}: {str(e)}")
                results['failed'] += 1
        
        return results


# Utility functions for route integration
def send_candidate_decision_email(feedback_id: int, hr_user_id: int) -> bool:
    """
    Send decision notification email to candidate
    
    Args:
        feedback_id: ID of the technical interview feedback
        hr_user_id: ID of the HR user sending the notification
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    notification_service = CandidateNotificationService()
    return notification_service.send_decision_notification(feedback_id, hr_user_id)


def send_bulk_decision_emails(feedback_ids: list, hr_user_id: int) -> Dict[str, int]:
    """
    Send decision notifications for multiple candidates
    
    Args:
        feedback_ids: List of feedback IDs to process
        hr_user_id: ID of the HR user sending the notifications
        
    Returns:
        Dict with counts of successful and failed notifications
    """
    notification_service = CandidateNotificationService()
    return notification_service.send_bulk_decision_notifications(feedback_ids, hr_user_id)