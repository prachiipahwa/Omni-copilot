from typing import Dict, Any, List
import urllib.parse
import datetime
import base64
from httpx import AsyncClient

from app.integrations.base import BaseConnector
from app.core.config import settings
from app.integrations.exceptions import (
    TokenExpiredError, 
    TokenRevokedError, 
    MissingScopeError, 
    ProviderAPIError
)

class GoogleConnector(BaseConnector):
    """
    Google Connector implementing OAuth flow for Google Drive, Gmail, & Calendar.
    Distinct from Identity Auth. This fetches long-lived Refresh tokens for the background orchestrator.
    """
    @property
    def provider_id(self) -> str:
        return "google"
        
    @property
    def required_scopes(self) -> List[str]:
        return [
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/calendar.readonly"
        ]

    async def get_auth_url(self, state: str) -> str:
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": f"{settings.API_V1_STR}/integrations/callback/google",
            "response_type": "code",
            "scope": " ".join(self.required_scopes),
            "state": state,
            "access_type": "offline",
            "prompt": "consent"
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    async def exchange_token(self, code: str) -> Dict[str, Any]:
        async with AsyncClient() as client:
            res = await client.post("https://oauth2.googleapis.com/token", data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": f"{settings.API_V1_STR}/integrations/callback/google",
            })
            if not res.is_success:
                raise ValueError(f"Failed to exchange token: {res.text}")
            return res.json()

    async def refresh_credentials(self, refresh_token: str) -> Dict[str, Any]:
        async with AsyncClient() as client:
            res = await client.post("https://oauth2.googleapis.com/token", data={
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token"
            })
            if not res.is_success:
                 raise TokenRevokedError(f"Token revoked or expired: {res.status_code}")
            return res.json()

    def _handle_google_error(self, res) -> None:
        if res.is_success:
            return
        if res.status_code == 401:
            raise TokenExpiredError("Access token expired")
        if res.status_code in (403,):
            raise MissingScopeError(f"Missing scopes or forbidden: {res.text}")
        raise ProviderAPIError(f"Google API failed with {res.status_code}: {res.text}")

    async def list_drive_files(self, access_token: str, max_results: int = 10) -> List[Dict[str, Any]]:
        headers = {"Authorization": f"Bearer {access_token}"}
        url = "https://www.googleapis.com/drive/v3/files"
        params = {
            "pageSize": max_results,
            "fields": "files(id, name, mimeType, webViewLink, createdTime, modifiedTime)",
            "orderBy": "modifiedTime desc"
        }
        async with AsyncClient() as client:
            res = await client.get(url, headers=headers, params=params)
            self._handle_google_error(res)
            
            files = res.json().get("files", [])
            return [
                {
                    "id": f.get("id"),
                    "name": f.get("name"),
                    "mime_type": f.get("mimeType"),
                    "web_view_link": f.get("webViewLink"),
                    "created_at": f.get("createdTime"),
                    "updated_at": f.get("modifiedTime")
                } for f in files
            ]

    async def get_document_text(self, access_token: str, document_id: str) -> str:
        headers = {"Authorization": f"Bearer {access_token}"}
        url = f"https://docs.googleapis.com/v1/documents/{document_id}"
        async with AsyncClient() as client:
            res = await client.get(url, headers=headers)
            self._handle_google_error(res)
            
            doc_data = res.json()
            text_content = ""
            for element in doc_data.get("body", {}).get("content", []):
                if "paragraph" in element:
                    for p_elem in element.get("paragraph", {}).get("elements", []):
                        if "textRun" in p_elem:
                            text_content += p_elem.get("textRun", {}).get("content", "")
            return text_content.strip()

    async def list_recent_emails(self, access_token: str, max_results: int = 10) -> List[Dict[str, Any]]:
        headers = {"Authorization": f"Bearer {access_token}"}
        url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
        async with AsyncClient() as client:
            res = await client.get(url, headers=headers, params={"maxResults": max_results})
            self._handle_google_error(res)
            
            messages = res.json().get("messages", [])
            hydrated = []
            for m in messages:
                # Fetch full message to get payload
                m_res = await client.get(f"{url}/{m['id']}", headers=headers)
                if m_res.is_success:
                    data = m_res.json()
                    headers_list = data.get("payload", {}).get("headers", [])
                    header_dict = {h["name"]: h["value"] for h in headers_list}
                    
                    # Extract body (prefer text/plain)
                    body = self._extract_email_body(data.get("payload", {}))
                    
                    hydrated.append({
                        "id": data.get("id"),
                        "thread_id": data.get("threadId"),
                        "snippet": body[:200] if body else data.get("snippet", ""),
                        "body": body,
                        "subject": header_dict.get("Subject", "No Subject"),
                        "sender": header_dict.get("From", "Unknown"),
                        "date": header_dict.get("Date", "")
                    })
            return hydrated

    def _extract_email_body(self, payload: Dict[str, Any]) -> str:
        """Recursive extraction of plain-text body from Gmail payload."""
        if payload.get("mimeType") == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode('utf-8')
        
        parts = payload.get("parts", [])
        for part in parts:
            body = self._extract_email_body(part)
            if body:
                return body
        return ""

    async def list_upcoming_events(self, access_token: str, max_results: int = 10) -> List[Dict[str, Any]]:
        headers = {"Authorization": f"Bearer {access_token}"}
        url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        async with AsyncClient() as client:
            res = await client.get(url, headers=headers, params={
                "timeMin": now,
                "maxResults": max_results,
                "singleEvents": True,
                "orderBy": "startTime"
            })
            self._handle_google_error(res)
            
            events = res.json().get("items", [])
            return [
                {
                    "id": e.get("id"),
                    "summary": e.get("summary", "No title"),
                    "description": e.get("description", ""),
                    "start_time": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
                    "end_time": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date"),
                    "html_link": e.get("htmlLink")
                } for e in events
            ]

    async def perform_search(self, query: str, credentials: Dict[str, Any], **kwargs) -> list[Dict[str, Any]]:
        return []

    async def ingest_data(self, credentials: Dict[str, Any]) -> Any:
        pass
