from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class DriveFileItem(BaseModel):
    id: str
    name: str
    mime_type: str
    web_view_link: str = ""
    created_at: str = ""
    updated_at: str = ""
    provider_source: str = "google_drive"

class EmailItem(BaseModel):
    id: str
    thread_id: Optional[str] = None
    subject: str = "No Subject"
    sender: str = "Unknown"
    snippet: str = ""
    body: Optional[str] = None # Hardening: Full indexed content
    date: str = ""
    provider_source: str = "gmail"

class CalendarEventItem(BaseModel):
    id: str
    summary: str
    description: str = ""
    start_time: str
    end_time: str
    html_link: str = ""
    provider_source: str = "google_calendar"

class DocumentContent(BaseModel):
    id: str
    title: str = "Unknown Document"
    text_content: str
    provider_source: str = "google_docs"
