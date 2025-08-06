import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with extensions
db.init_app(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Add custom template filters
@app.template_filter('from_json')
def from_json_filter(value):
    """Convert JSON string to Python object, handling severely malformed encoding"""
    import json
    import re
    try:
        if not value:
            return []
            
        # First try standard JSON parsing
        try:
            parsed = json.loads(value)
            if isinstance(parsed, (list, dict)):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Handle severely malformed JSON by extracting skill names directly (for skills field)
        # Pattern to match skill names within the encoded structure
        skill_pattern = r'\\\\\"([^\\\\]+)\\\\\"'
        matches = re.findall(skill_pattern, value)
        
        if matches:
            # Clean up the matched skills
            skills = []
            for match in matches:
                # Remove any remaining escape characters
                clean_skill = match.replace('\\"', '"').replace('\\\\', '\\').strip()
                if clean_skill and clean_skill not in skills:
                    skills.append(clean_skill)
            return skills
        
        # Fallback: try iterative JSON parsing for nested encoding
        result = value
        for _ in range(5):  # Try parsing up to 5 times
            try:
                parsed = json.loads(result)
                if isinstance(parsed, list):
                    # Return the parsed list as-is (for work experience and education)
                    return parsed
                elif isinstance(parsed, dict):
                    return parsed
                elif isinstance(parsed, str):
                    result = parsed
                else:
                    return []
            except (json.JSONDecodeError, TypeError):
                break
        
        # If all parsing attempts fail, return empty list
        return []
    except:
        return []

@app.template_filter('nl2br')
def nl2br_filter(value):
    """Convert newlines to HTML line breaks"""
    if not value:
        return ''
    from markupsafe import Markup
    return Markup(value.replace('\n', '<br>\n'))

@app.template_global()
def calculate_profile_completion(candidate):
    """Calculate profile completion percentage"""
    completed = 0
    total = 5
    
    if candidate.bio:
        completed += 1
    if candidate.skills:
        completed += 1
    if candidate.experience:
        completed += 1
    if candidate.education:
        completed += 1
    if candidate.profile_image_url:
        completed += 1
    
    return round((completed / total) * 100)

with app.app_context():
    # Make sure to import the models here or their tables won't be created
    import models  # noqa: F401
    db.create_all()
    logging.info("Database tables created")
    
    # Initialize job scheduler (avoid circular imports) - TEMPORARILY DISABLED
    # try:
    #     import job_scheduler
    #     job_scheduler.init_job_scheduler()
    #     logging.info("Job scheduler initialized")
    # except Exception as e:
    #     logging.error(f"Error initializing job scheduler: {e}")
