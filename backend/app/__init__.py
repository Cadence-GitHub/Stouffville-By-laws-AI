# Stouffville By-laws AI Assistant
# This package contains utility modules for the backend Flask application 

from flask_sqlalchemy import SQLAlchemy
from app.chroma_retriever import ChromaDBRetriever
from app.gemini_handler import get_gemini_response, transform_query_for_enhanced_search, get_provincial_law_info, ALLOWED_MODELS
from app.prompts import get_bylaws_prompt_template, BASE_BYLAWS_PROMPT_TEMPLATE, LAYMANS_PROMPT_TEMPLATE, ENHANCED_SEARCH_PROMPT_TEMPLATE
from app.token_counter import count_tokens, MODEL_PRICING 
from datetime import datetime

db = SQLAlchemy()

class Evaluation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    ai_response = db.Column(db.Text, nullable=False)
    reference_answer = db.Column(db.Text)
    evaluator = db.Column(db.String(50), nullable=False)
    response_generated = db.Column(db.Boolean, nullable=False)
    accuracy = db.Column(db.Integer)
    hallucination = db.Column(db.Integer)
    completeness = db.Column(db.Integer)
    authoritative = db.Column(db.Integer)
    usefulness = db.Column(db.Integer)
    comments = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    pass_fail = db.Column(db.String(10))
    __table_args__ = (db.UniqueConstraint('evaluator', 'question', name='uq_evaluation_evaluator_question'),)

class Evaluator(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False) 

class EvalStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    evaluator = db.Column(db.String(50), nullable=False)
    question_idx = db.Column(db.Integer, nullable=False)
    bookmarked = db.Column(db.Boolean, default=False)
    skipped = db.Column(db.Boolean, default=False)
    __table_args__ = (db.UniqueConstraint('evaluator', 'question_idx', name='uq_evalstatus_evaluator_qidx'),) 