"""
Calendar integration service for Google Calendar
"""
import os
import json
import logging
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class CalendarService:
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/calendar']
        self.service = None
        
    def get_authorization_url(self, redirect_uri):
        """Get the authorization URL for Google Calendar access"""
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": os.environ.get('GOOGLE_CLIENT_ID'),
                        "client_secret": os.environ.get('GOOGLE_CLIENT_SECRET'),
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [redirect_uri]
                    }
                },
                scopes=self.scopes
            )
            flow.redirect_uri = redirect_uri
            
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true'
            )
            return authorization_url, state
        except Exception as e:
            logging.error(f"Error getting authorization URL: {e}")
            return None, None
    
    def exchange_code_for_token(self, code, state, redirect_uri):
        """Exchange authorization code for access token"""
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": os.environ.get('GOOGLE_CLIENT_ID'),
                        "client_secret": os.environ.get('GOOGLE_CLIENT_SECRET'),
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [redirect_uri]
                    }
                },
                scopes=self.scopes,
                state=state
            )
            flow.redirect_uri = redirect_uri
            
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            return {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
        except Exception as e:
            logging.error(f"Error exchanging code for token: {e}")
            return None
    
    def initialize_service(self, credentials_dict):
        """Initialize the calendar service with credentials"""
        try:
            credentials = Credentials.from_authorized_user_info(credentials_dict, self.scopes)
            self.service = build('calendar', 'v3', credentials=credentials)
            return True
        except Exception as e:
            logging.error(f"Error initializing calendar service: {e}")
            return False
    
    def create_event(self, title, description, start_datetime, end_datetime, 
                    attendee_emails=None, time_zone='UTC'):
        """Create a calendar event with Google Meet link"""
        if not self.service:
            logging.error("Calendar service not initialized")
            return None
            
        try:
            event = {
                'summary': title,
                'description': description,
                'start': {
                    'dateTime': start_datetime.isoformat(),
                    'timeZone': time_zone,
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': time_zone,
                },
                'conferenceData': {
                    'createRequest': {
                        'requestId': f"meet-{start_datetime.isoformat()}",
                        'conferenceSolutionKey': {
                            'type': 'hangoutsMeet'
                        }
                    }
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 30},       # 30 minutes before
                    ],
                },
            }
            
            if attendee_emails:
                event['attendees'] = [{'email': email} for email in attendee_emails]
            
            # Use conferenceDataVersion=1 to enable Google Meet link creation
            created_event = self.service.events().insert(
                calendarId='primary', 
                body=event,
                conferenceDataVersion=1
            ).execute()
            
            # Return both event ID and meeting link
            meet_link = None
            if 'conferenceData' in created_event and 'entryPoints' in created_event['conferenceData']:
                for entry_point in created_event['conferenceData']['entryPoints']:
                    if entry_point['entryPointType'] == 'video':
                        meet_link = entry_point['uri']
                        break
            
            return {
                'id': created_event.get('id'),
                'meeting_link': meet_link,
                'hangout_link': created_event.get('hangoutLink'),  # Fallback
                'html_link': created_event.get('htmlLink')
            }
            
        except HttpError as error:
            logging.error(f"Error creating calendar event: {error}")
            return None
    
    def update_event(self, event_id, title=None, description=None, 
                    start_datetime=None, end_datetime=None, attendee_emails=None):
        """Update an existing calendar event"""
        if not self.service:
            logging.error("Calendar service not initialized")
            return False
            
        try:
            # Get existing event
            event = self.service.events().get(calendarId='primary', eventId=event_id).execute()
            
            # Update fields if provided
            if title:
                event['summary'] = title
            if description:
                event['description'] = description
            if start_datetime:
                event['start']['dateTime'] = start_datetime.isoformat()
            if end_datetime:
                event['end']['dateTime'] = end_datetime.isoformat()
            if attendee_emails:
                event['attendees'] = [{'email': email} for email in attendee_emails]
            
            updated_event = self.service.events().update(
                calendarId='primary', 
                eventId=event_id, 
                body=event
            ).execute()
            
            return True
            
        except HttpError as error:
            logging.error(f"Error updating calendar event: {error}")
            return False
    
    def delete_event(self, event_id):
        """Delete a calendar event"""
        if not self.service:
            logging.error("Calendar service not initialized")
            return False
            
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            return True
        except HttpError as error:
            logging.error(f"Error deleting calendar event: {error}")
            return False
    
    def get_free_busy(self, start_time, end_time, calendars=['primary']):
        """Get free/busy information for calendars"""
        if not self.service:
            logging.error("Calendar service not initialized")
            return None
            
        try:
            body = {
                'timeMin': start_time.isoformat() + 'Z',
                'timeMax': end_time.isoformat() + 'Z',
                'items': [{'id': cal} for cal in calendars]
            }
            
            response = self.service.freebusy().query(body=body).execute()
            return response.get('calendars', {})
            
        except HttpError as error:
            logging.error(f"Error getting free/busy information: {error}")
            return None

def send_email_notification(to_email, subject, body):
    """Send email notification for interview scheduling"""
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        api_key = os.environ.get('SENDGRID_API_KEY')
        if not api_key:
            logging.error("SendGrid API key not configured")
            return False
            
        message = Mail(
            from_email='noreply@interviewplatform.com',
            to_emails=to_email,
            subject=subject,
            html_content=body
        )
        
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        return response.status_code == 202
        
    except Exception as e:
        logging.error(f"Error sending email notification: {e}")
        return False

def send_sms_notification(phone_number, message):
    """Send SMS notification for interview scheduling"""
    try:
        from twilio.rest import Client
        
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        from_number = os.environ.get('TWILIO_PHONE_NUMBER')
        
        if not all([account_sid, auth_token, from_number]):
            logging.error("Twilio credentials not configured")
            return False
            
        client = Client(account_sid, auth_token)
        
        message = client.messages.create(
            body=message,
            from_=from_number,
            to=phone_number
        )
        
        return message.sid is not None
        
    except Exception as e:
        logging.error(f"Error sending SMS notification: {e}")
        return False