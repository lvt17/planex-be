from app import create_app
from app.extensions import db
from app.models.content import Document, Spreadsheet
from app.models.whiteboard import Whiteboard
from app.models.user_feedback import UserSurvey, BugReport
from app.models.team import Team, TeamMembership, ChatMessage

app = create_app('production')
with app.app_context():
    db.create_all()
    print("Database tables created successfully (including Whiteboards).")
