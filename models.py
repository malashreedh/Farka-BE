import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database import Base


class PathEnum(str, enum.Enum):
    job_seeker = "job_seeker"
    business_starter = "business_starter"
    undecided = "undecided"


class TradeCategoryEnum(str, enum.Enum):
    construction = "construction"
    hospitality = "hospitality"
    manufacturing = "manufacturing"
    agriculture = "agriculture"
    domestic = "domestic"
    transport = "transport"
    tech = "tech"
    other = "other"


class LanguageEnum(str, enum.Enum):
    en = "en"
    ne = "ne"


class SavingsRangeEnum(str, enum.Enum):
    under_5L = "under_5L"
    five_to_20L = "5L_to_20L"
    twenty_to_50L = "20L_to_50L"
    above_50L = "above_50L"


class WorkflowStageEnum(str, enum.Enum):
    initial = "initial"
    language_set = "language_set"
    collecting_basics = "collecting_basics"
    collecting_experience = "collecting_experience"
    path_decision = "path_decision"
    collecting_skills = "collecting_skills"
    collecting_business_details = "collecting_business_details"
    profile_complete = "profile_complete"
    job_matching = "job_matching"
    checklist_generated = "checklist_generated"


class OrgTypeEnum(str, enum.Enum):
    government = "government"
    ngo = "ngo"
    private = "private"


class ExperienceLevelEnum(str, enum.Enum):
    entry = "entry"
    mid = "mid"
    senior = "senior"


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=True)
    phone = Column(String, unique=True, nullable=True)
    current_location = Column(String, nullable=True)
    path = Column(Enum(PathEnum), nullable=False, default=PathEnum.undecided)
    trade_category = Column(Enum(TradeCategoryEnum), nullable=True)
    years_experience = Column(Integer, nullable=True)
    skills = Column(JSON, nullable=True, default=list)
    language_pref = Column(Enum(LanguageEnum), nullable=False, default=LanguageEnum.en)
    district_target = Column(String, nullable=True)
    has_savings = Column(Boolean, nullable=False, default=False)
    savings_range = Column(Enum(SavingsRangeEnum), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    chat_sessions = relationship("ChatSession", back_populates="profile")
    job_matches = relationship("JobMatch", back_populates="profile")
    business_checklists = relationship("BusinessChecklist", back_populates="profile")


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(String, ForeignKey("profiles.id"), nullable=True)
    messages = Column(JSON, nullable=False, default=list)
    workflow_stage = Column(Enum(WorkflowStageEnum), nullable=False, default=WorkflowStageEnum.initial)
    language = Column(Enum(LanguageEnum), nullable=False, default=LanguageEnum.en)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    profile = relationship("Profile", back_populates="chat_sessions")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    org_name = Column(String, nullable=False)
    org_type = Column(Enum(OrgTypeEnum), nullable=False)
    district = Column(String, nullable=False)
    trade_category = Column(String, nullable=False)
    skill_tags = Column(JSON, nullable=False, default=list)
    experience_level = Column(Enum(ExperienceLevelEnum), nullable=False)
    description = Column(Text, nullable=False)
    salary_range = Column(String, nullable=True)
    apply_url = Column(String, nullable=False, default="#")
    is_active = Column(Boolean, nullable=False, default=True)
    posted_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    job_matches = relationship("JobMatch", back_populates="job")


class JobMatch(Base):
    __tablename__ = "job_matches"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(String, ForeignKey("profiles.id"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)
    match_score = Column(Float, nullable=False)
    matched_tags = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    profile = relationship("Profile", back_populates="job_matches")
    job = relationship("Job", back_populates="job_matches")


class BusinessChecklist(Base):
    __tablename__ = "business_checklists"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(String, ForeignKey("profiles.id"), nullable=False)
    trade = Column(String, nullable=False)
    district = Column(String, nullable=False)
    checklist_items = Column(JSON, nullable=False, default=list)
    raw_ai_output = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    profile = relationship("Profile", back_populates="business_checklists")
