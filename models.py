from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Poll(db.Model):
    """Model for Polls table. Each poll has a question and a list of votes"""
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship between Poll and Vote
    votes = db.relationship('Vote', backref='poll', lazy=True)

    def __repr__(self):
        return f'<Poll {self.question}>'
    

class Vote(db.Model):
    """Model for Votes table. Each vote has a choice and a timestamp"""
    id = db.Column(db.Integer, primary_key=True)
    choice = db.Column(db.String(200), nullable=False)
    count = db.Column(db.Integer, nullable=False, default=0)
    poll_id = db.Column(db.Integer, db.ForeignKey('poll.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Vote {self.choice}>'

