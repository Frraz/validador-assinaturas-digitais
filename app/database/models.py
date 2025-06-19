from sqlalchemy import Column, String, Integer, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class ValidationJob(Base):
    __tablename__ = "validation_jobs"
    
    id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.now)
    status = Column(String)
    progress = Column(Integer)
    report_path = Column(String, nullable=True)
    
    # Relacionamentos
    files = relationship("ValidationFile", back_populates="job", cascade="all, delete-orphan")
    rejected_files = relationship("RejectedFile", back_populates="job", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Converte o modelo para um dicionário"""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "progress": self.progress,
            "report_path": self.report_path,
            "files": [file.to_dict() for file in self.files],
            "rejected_files": [file.to_dict() for file in self.rejected_files]
        }


class ValidationFile(Base):
    __tablename__ = "validation_files"
    
    id = Column(String, primary_key=True)
    job_id = Column(String, ForeignKey("validation_jobs.id"))
    filename = Column(String)
    path = Column(String)
    status = Column(String)
    is_valid = Column(Boolean, nullable=True)
    error = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    
    # Relacionamentos
    job = relationship("ValidationJob", back_populates="files")
    
    def to_dict(self):
        """Converte o modelo para um dicionário"""
        return {
            "id": self.id,
            "filename": self.filename,
            "path": self.path,
            "status": self.status,
            "is_valid": self.is_valid,
            "error": self.error,
            "details": self.details
        }


class RejectedFile(Base):
    __tablename__ = "rejected_files"
    
    id = Column(String, primary_key=True)
    job_id = Column(String, ForeignKey("validation_jobs.id"))
    filename = Column(String)
    error = Column(Text)
    
    # Relacionamentos
    job = relationship("ValidationJob", back_populates="rejected_files")
    
    def to_dict(self):
        """Converte o modelo para um dicionário"""
        return {
            "id": self.id,
            "filename": self.filename,
            "error": self.error
        }