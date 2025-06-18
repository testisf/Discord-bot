import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from models import Base
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and sessions"""
    
    def __init__(self):
        self.engine = None
        self.Session = None
        self._initialized = False
    
    def initialize(self):
        """Initialize database connection"""
        if self._initialized:
            return
        
        try:
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                logger.warning("DATABASE_URL environment variable not set - running in no-database mode")
                self._initialized = True
                return
            
            # Fix postgres:// URL for SQLAlchemy compatibility
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)
            
            # Add SSL configuration for production databases
            if "localhost" not in database_url and "127.0.0.1" not in database_url:
                if "?" not in database_url:
                    database_url += "?sslmode=require"
                elif "sslmode=" not in database_url:
                    database_url += "&sslmode=require"
            
            # Create engine with connection pooling
            self.engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=300
            )
            
            # Test the connection first
            from sqlalchemy import text
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            
            # Create session factory
            self.Session = scoped_session(sessionmaker(bind=self.engine))
            
            # Create all tables
            Base.metadata.create_all(self.engine)
            
            self._initialized = True
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            logger.warning("Running bot in no-database mode - some features may be limited")
            self.engine = None
            self.Session = None
            self._initialized = True
    
    @contextmanager
    def get_session(self):
        """Get database session with automatic cleanup"""
        if not self._initialized:
            self.initialize()
        
        if not self.Session:
            logger.warning("No database session available - running in no-database mode")
            yield None
            return
        
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    def close(self):
        """Close database connections"""
        if self.Session:
            self.Session.remove()
        if self.engine:
            self.engine.dispose()
        self._initialized = False

# Global database manager instance
db_manager = DatabaseManager()