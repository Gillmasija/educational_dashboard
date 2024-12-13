from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import logging

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

def init_db(app):
    """Initialize the database and verify connection."""
    try:
        # Initialize the database
        db.init_app(app)
        
        with app.app_context():
            # Test database connection
            result = db.session.execute('SELECT 1')
            result.scalar()
            logger.info("Database connection verified successfully")
            
            # Create all tables
            db.create_all()
            logger.info("Database tables created successfully")
            
            return True
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        logger.exception(e)  # Log the full stack trace
        raise
    finally:
        try:
            db.session.remove()
        except Exception:
            pass
