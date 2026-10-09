from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler

# Initialize extensions without app context (application factory pattern)
db = SQLAlchemy()
cors = CORS()
scheduler = BackgroundScheduler(daemon=True)
