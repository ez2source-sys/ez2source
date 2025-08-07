"""
Technical Interview Service for Job2Hire
Handles technical person workflow including scheduling, notifications, and feedback collection
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from flask import current_app
from sqlalchemy import and_, or_

from app import db
from models import (
    User, Interview, InterviewResponse, Organization,
    TechnicalInterviewAssignment, TechnicalInterviewFeedback,
    TechnicalPersonNotification, AuditLog
)
from enhanced_email_service import EnhancedEmailService as EmailService
from calendar_service import CalendarService
from ai_service import openai


class TechnicalInterviewService:
    """Service to handle technical interview workflow"""
    
    def __init__(self):
        self.email_service = EmailService()
        self.calendar_service = CalendarService()
        self.openai_client = openai

    def assign_technical_person(self, interview_id: int, candidate_id: int, 
                               technical_person_id: int, interview_datetime: datetime,
                               assigned_by_id: int, meeting_link: Optional[str] = None) -> Optional[TechnicalInterviewAssignment]:
        """
        Assign a technical person to conduct an interview with a candidate
        
        Args:
            interview_id: ID of the interview
            candidate_id: ID of the candidate
            technical_person_id: ID of the technical person
            interview_datetime: Scheduled interview date and time
            assigned_by_id: ID of the user making the assignment (HR/Admin)
        
        Returns:
            TechnicalInterviewAssignment object or None if failed
        """
        try:
            # Validate entities exist
            interview = Interview.query.get(interview_id)
            candidate = User.query.get(candidate_id)
            technical_person = User.query.get(technical_person_id)
            assigner = User.query.get(assigned_by_id)
            
            if not all([interview, candidate, technical_person, assigner]):
                logging.error("One or more entities not found for technical interview assignment")
                return None
            
            # Check if technical person has the right role
            if technical_person.role != 'technical_person':
                logging.error(f"User {technical_person_id} is not a technical person")
                return None
            
            # Check for duplicate assignment
            existing = TechnicalInterviewAssignment.query.filter_by(
                interview_id=interview_id,
                candidate_id=candidate_id,
                technical_person_id=technical_person_id
            ).first()
            
            if existing:
                logging.warning("Technical interview assignment already exists")
                return existing
            
            # Create assignment
            assignment = TechnicalInterviewAssignment(
                interview_id=interview_id,
                technical_person_id=technical_person_id,
                candidate_id=candidate_id,
                organization_id=interview.organization_id,
                assigned_by=assigned_by_id,
                interview_date=interview_datetime,
                meeting_link=meeting_link
            )
            
            db.session.add(assignment)
            db.session.flush()  # Get the ID
            
            # Send notifications
            self._send_assignment_notifications(assignment)
            
            # Create calendar event with Google Meet link
            calendar_result = self._create_calendar_event(assignment)
            if calendar_result:
                assignment.calendar_event_id = calendar_result.get('id')
                assignment.meeting_link = calendar_result.get('meeting_link') or calendar_result.get('hangout_link')
            
            db.session.commit()
            
            # Log the assignment
            self._log_assignment_activity(assignment, assigner)
            
            return assignment
            
        except Exception as e:
            logging.error(f"Error assigning technical person: {e}")
            db.session.rollback()
            return None

    def _send_assignment_notifications(self, assignment: TechnicalInterviewAssignment):
        """Send email and in-app notifications to technical person"""
        try:
            technical_person = assignment.technical_person
            candidate = assignment.candidate
            interview = assignment.interview
            
            # Email notification
            subject = f"Technical Interview Assignment - {candidate.first_name} {candidate.last_name}"
            
            email_content = f"""
            <h2>Technical Interview Assignment</h2>
            <p>Hello {technical_person.first_name},</p>
            
            <p>You have been assigned to conduct a technical interview:</p>
            
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3>Interview Details</h3>
                <p><strong>Position:</strong> {interview.title}</p>
                <p><strong>Candidate:</strong> {candidate.first_name} {candidate.last_name}</p>
                <p><strong>Email:</strong> {candidate.email}</p>
                <p><strong>Phone:</strong> {candidate.phone or 'Not provided'}</p>
                <p><strong>Date & Time:</strong> {assignment.interview_date.strftime('%B %d, %Y at %I:%M %p')}</p>
                {f'<p><strong>Google Meet Link:</strong> <a href="{assignment.meeting_link}">{assignment.meeting_link}</a></p>' if assignment.meeting_link else ''}
            </div>
            
            <h3>Next Steps:</h3>
            <ul>
                <li>Review the candidate's profile and resume</li>
                <li>Calendar invite has been sent automatically</li>
                <li>Access the interview platform on the scheduled date</li>
                <li>Submit feedback after the interview</li>
            </ul>
            
            <p>
                <a href="{current_app.config.get('BASE_URL', '')}/technical/candidate/{candidate.id}" 
                   style="background-color: #2563eb; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    View Candidate Profile
                </a>
            </p>
            
            <p>Best regards,<br>Job2Hire Team</p>
            """
            
            email_sent = self.email_service.send_email(
                to_email=technical_person.email,
                subject=subject,
                html_content=email_content
            )
            
            # Record notification
            notification = TechnicalPersonNotification(
                technical_person_id=technical_person.id,
                assignment_id=assignment.id,
                notification_type='email',
                status='sent' if email_sent else 'failed',
                content=subject
            )
            db.session.add(notification)
            
        except Exception as e:
            logging.error(f"Error sending assignment notifications: {e}")

    def _create_calendar_event(self, assignment: TechnicalInterviewAssignment) -> Optional[str]:
        """Create calendar event for the technical interview"""
        try:
            technical_person = assignment.technical_person
            candidate = assignment.candidate
            interview = assignment.interview
            
            event_title = f"Technical Interview - {candidate.first_name} {candidate.last_name}"
            event_description = f"""
            Technical Interview Details:
            
            Position: {interview.title}
            Candidate: {candidate.first_name} {candidate.last_name}
            Email: {candidate.email}
            Phone: {candidate.phone or 'Not provided'}
            
            Candidate Profile: {current_app.config.get('BASE_URL', '')}/technical/candidate/{candidate.id}
            Feedback Form: {current_app.config.get('BASE_URL', '')}/technical/feedback/{assignment.id}
            """
            
            start_time = assignment.interview_date
            end_time = start_time + timedelta(hours=1)  # Default 1 hour
            
            event_id = self.calendar_service.create_event(
                title=event_title,
                description=event_description,
                start_datetime=start_time,
                end_datetime=end_time,
                attendee_emails=[technical_person.email, candidate.email]
            )
            
            return event_id
            
        except Exception as e:
            logging.error(f"Error creating calendar event: {e}")
            return None

    def _log_assignment_activity(self, assignment: TechnicalInterviewAssignment, assigner: User):
        """Log the technical interview assignment activity"""
        try:
            audit_log = AuditLog(
                user_id=assigner.id,
                organization_id=assignment.organization_id,
                action='technical_interview_assigned',
                resource_type='technical_interview_assignment',
                resource_id=assignment.id,
                details=json.dumps({
                    'interview_id': assignment.interview_id,
                    'candidate_id': assignment.candidate_id,
                    'technical_person_id': assignment.technical_person_id,
                    'interview_date': assignment.interview_date.isoformat(),
                    'assigned_by': assigner.username
                })
            )
            db.session.add(audit_log)
            
        except Exception as e:
            logging.error(f"Error logging assignment activity: {e}")

    def get_technical_person_dashboard(self, technical_person_id: int) -> Dict:
        """Get dashboard data for technical person"""
        try:
            # Get pending interviews
            pending_assignments = TechnicalInterviewAssignment.query.filter_by(
                technical_person_id=technical_person_id,
                status='pending'
            ).order_by(TechnicalInterviewAssignment.interview_date.asc()).all()
            
            # Get completed interviews
            completed_assignments = TechnicalInterviewAssignment.query.filter_by(
                technical_person_id=technical_person_id,
                status='completed'
            ).order_by(TechnicalInterviewAssignment.interview_date.desc()).limit(10).all()
            
            # Get upcoming interviews (next 7 days)
            upcoming_date = datetime.utcnow() + timedelta(days=7)
            upcoming_assignments = TechnicalInterviewAssignment.query.filter(
                and_(
                    TechnicalInterviewAssignment.technical_person_id == technical_person_id,
                    TechnicalInterviewAssignment.interview_date >= datetime.utcnow(),
                    TechnicalInterviewAssignment.interview_date <= upcoming_date,
                    TechnicalInterviewAssignment.status == 'pending'
                )
            ).order_by(TechnicalInterviewAssignment.interview_date.asc()).all()
            
            return {
                'pending_count': len(pending_assignments),
                'completed_count': len(completed_assignments),
                'upcoming_interviews': upcoming_assignments,
                'recent_completed': completed_assignments
            }
            
        except Exception as e:
            logging.error(f"Error getting technical person dashboard: {e}")
            return {}

    def submit_technical_feedback(self, assignment_id: int, feedback_data: Dict) -> Optional[TechnicalInterviewFeedback]:
        """Submit technical interview feedback"""
        try:
            assignment = TechnicalInterviewAssignment.query.get(assignment_id)
            if not assignment:
                logging.error(f"Assignment {assignment_id} not found")
                return None
            
            # Check if feedback already exists
            existing_feedback = TechnicalInterviewFeedback.query.filter_by(
                assignment_id=assignment_id
            ).first()
            
            if existing_feedback:
                # Update existing feedback
                feedback = existing_feedback
            else:
                # Create new feedback
                feedback = TechnicalInterviewFeedback(
                    assignment_id=assignment_id,
                    technical_person_id=assignment.technical_person_id,
                    candidate_id=assignment.candidate_id,
                    interview_id=assignment.interview_id,
                    organization_id=assignment.organization_id
                )
            
            # Update feedback fields
            feedback.decision = feedback_data.get('decision', 'pending')
            feedback.technical_comments = feedback_data.get('technical_comments', '')
            feedback.communication_comments = feedback_data.get('communication_comments', '')
            feedback.overall_comments = feedback_data.get('overall_comments', '')
            
            # Ratings
            feedback.technical_skills_rating = feedback_data.get('technical_skills_rating')
            feedback.problem_solving_rating = feedback_data.get('problem_solving_rating')
            feedback.communication_rating = feedback_data.get('communication_rating')
            feedback.cultural_fit_rating = feedback_data.get('cultural_fit_rating')
            
            # AI integration
            feedback.used_ai_assistance = feedback_data.get('used_ai_assistance', False)
            feedback.interview_duration_minutes = feedback_data.get('interview_duration_minutes')
            
            # Second round handling
            feedback.requires_second_round = feedback_data.get('decision') == 'second_round'
            feedback.second_round_notes = feedback_data.get('second_round_notes', '')
            
            # Generate AI summary if requested
            if feedback.used_ai_assistance:
                ai_summary = self._generate_ai_feedback_summary(feedback_data)
                feedback.ai_summary = ai_summary
            
            db.session.add(feedback)
            
            # Update assignment status
            assignment.status = 'completed'
            
            db.session.commit()
            
            # Notify HR/Admin about feedback submission
            self._notify_feedback_submission(feedback)
            
            # Handle second round if needed
            if feedback.requires_second_round:
                self._handle_second_round_request(feedback)
            
            return feedback
            
        except Exception as e:
            logging.error(f"Error submitting technical feedback: {e}")
            db.session.rollback()
            return None

    def _generate_ai_feedback_summary(self, feedback_data: Dict) -> str:
        """Generate AI summary of the technical interview feedback"""
        try:
            if not self.openai_client:
                # Fallback when OpenAI is not available
                decision = feedback_data.get('decision', 'Not specified')
                tech_rating = feedback_data.get('technical_skills_rating', 0)
                comm_rating = feedback_data.get('communication_rating', 0)
                
                return f"""
                Technical Interview Summary
                
                Decision: {decision}
                Technical Skills: {tech_rating}/5
                Communication: {comm_rating}/5
                
                Key Comments:
                {feedback_data.get('technical_comments', 'No technical comments provided')}
                
                Note: AI analysis unavailable - manual review recommended.
                """
            
            prompt = f"""
            Based on the following technical interview feedback, provide a comprehensive summary:
            
            Decision: {feedback_data.get('decision', 'Not specified')}
            Technical Comments: {feedback_data.get('technical_comments', 'No comments')}
            Communication Comments: {feedback_data.get('communication_comments', 'No comments')}
            Overall Comments: {feedback_data.get('overall_comments', 'No comments')}
            
            Technical Skills Rating: {feedback_data.get('technical_skills_rating', 'Not rated')}/5
            Problem Solving Rating: {feedback_data.get('problem_solving_rating', 'Not rated')}/5
            Communication Rating: {feedback_data.get('communication_rating', 'Not rated')}/5
            Cultural Fit Rating: {feedback_data.get('cultural_fit_rating', 'Not rated')}/5
            
            Please provide:
            1. A concise summary of the candidate's performance
            2. Key strengths identified
            3. Areas for improvement
            4. Recommendation rationale
            
            Keep the summary professional and constructive.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert technical interview analyst. Provide clear, actionable feedback summaries."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Error generating AI feedback summary: {e}")
            return "AI summary generation failed"

    def _notify_feedback_submission(self, feedback: TechnicalInterviewFeedback):
        """Notify HR/Admin about feedback submission"""
        try:
            # Get HR/Admin users in the organization
            hr_users = User.query.filter(
                and_(
                    User.organization_id == feedback.organization_id,
                    or_(User.role == 'recruiter', User.role == 'admin')
                )
            ).all()
            
            technical_person = User.query.get(feedback.technical_person_id)
            candidate = User.query.get(feedback.candidate_id)
            interview = Interview.query.get(feedback.interview_id)
            
            subject = f"Technical Interview Feedback Received - {candidate.first_name} {candidate.last_name}"
            
            for hr_user in hr_users:
                email_content = f"""
                <h2>Technical Interview Feedback Received</h2>
                <p>Hello {hr_user.first_name},</p>
                
                <p>Technical interview feedback has been submitted:</p>
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3>Feedback Summary</h3>
                    <p><strong>Position:</strong> {interview.title}</p>
                    <p><strong>Candidate:</strong> {candidate.first_name} {candidate.last_name}</p>
                    <p><strong>Technical Person:</strong> {technical_person.first_name} {technical_person.last_name}</p>
                    <p><strong>Decision:</strong> {feedback.decision.replace('_', ' ').title()}</p>
                    <p><strong>Submitted:</strong> {feedback.submitted_at.strftime('%B %d, %Y at %I:%M %p')}</p>
                </div>
                
                <p>
                    <a href="{current_app.config.get('BASE_URL', '')}/technical/feedback/{feedback.id}" 
                       style="background-color: #2563eb; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                        View Full Feedback
                    </a>
                </p>
                
                <p>Best regards,<br>Job2Hire Team</p>
                """
                
                self.email_service.send_email(
                    to_email=hr_user.email,
                    subject=subject,
                    html_content=email_content
                )
                
        except Exception as e:
            logging.error(f"Error notifying feedback submission: {e}")

    def _handle_second_round_request(self, feedback: TechnicalInterviewFeedback):
        """Handle second round interview request"""
        try:
            # This could trigger automatic second round scheduling
            # For now, just log it for HR attention
            logging.info(f"Second round requested for candidate {feedback.candidate_id}")
            
        except Exception as e:
            logging.error(f"Error handling second round request: {e}")

    def get_candidate_profile_for_technical_person(self, candidate_id: int, technical_person_id: int) -> Optional[Dict]:
        """Get candidate profile data for technical person view"""
        try:
            # Verify technical person has assignment for this candidate
            assignment = TechnicalInterviewAssignment.query.filter_by(
                candidate_id=candidate_id,
                technical_person_id=technical_person_id
            ).first()
            
            if not assignment:
                return None
            
            candidate = User.query.get(candidate_id)
            if not candidate:
                return None
            
            # Get interview responses for this candidate
            responses = InterviewResponse.query.filter_by(
                candidate_id=candidate_id,
                organization_id=assignment.organization_id
            ).all()
            
            # Get previous technical feedback
            previous_feedback = TechnicalInterviewFeedback.query.filter_by(
                candidate_id=candidate_id,
                organization_id=assignment.organization_id
            ).all()
            
            return {
                'candidate': candidate,
                'assignment': assignment,
                'interview_responses': responses,
                'previous_feedback': previous_feedback,
                'skills': json.loads(candidate.skills) if candidate.skills else [],
                'experience': json.loads(candidate.experience) if candidate.experience else []
            }
            
        except Exception as e:
            logging.error(f"Error getting candidate profile: {e}")
            return None


# Utility functions for routes
def get_technical_person_assignments(technical_person_id: int, status: str = None) -> List[TechnicalInterviewAssignment]:
    """Get assignments for a technical person"""
    query = TechnicalInterviewAssignment.query.filter_by(technical_person_id=technical_person_id)
    if status:
        query = query.filter_by(status=status)
    return query.order_by(TechnicalInterviewAssignment.interview_date.desc()).all()


def get_pending_second_rounds(organization_id: int) -> List[TechnicalInterviewFeedback]:
    """Get feedback that requires second round interviews"""
    return TechnicalInterviewFeedback.query.filter_by(
        organization_id=organization_id,
        requires_second_round=True
    ).all()