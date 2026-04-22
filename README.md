# Omni Copilot

An AI-powered workspace assistant that connects your Google Workspace (Drive, Gmail, Calendar, Forms) and Notion into a single chat interface. Ask questions in plain English and get live answers pulled from your actual data.

---

## What it does

- **Chat with your workspace** — ask about emails, files, meetings, or notes and get real answers
- **Google Drive** — search files by name or content
- **Gmail** — find emails with smart filtering (date, sender, read/unread, attachments)
- **Google Calendar** — check upcoming events for the next 7 days
- **Google Forms** — view response counts and latest submissions
- **Notion** — search pages and read content previews
- **Code analysis** — upload a code file and ask it to explain, fix, improve, or review it
- **Vision** — upload an image and ask questions about it
- **Conversation memory** — maintains context across messages in a session

---

## Architecture

```
Frontend (React + Vite, port 5173)
    └── POST /api/chat
            ↓
Backend (Express, port 3001)
    └── Orchestrator
            ├── Groq LLM routes the query to relevant agents
            ├── Agents run in parallel (Drive, Gmail, Calendar, Notion, Forms)
            ├── Code agent (file upload path)
            ├── Vision agent (image upload path)
            └── Groq LLM generates final response with live data as context
```

### Project structure

```
omni-copilot/
├── backend/
│   ├── index.js              # Express server (port 3001)
│   ├── routes/
│   │   ├── auth.js           # Google OAuth2 flow
│   │   └── chat.js           # Chat endpoint handler
│   ├── agents/
│   │   ├── orchestrator.js   # Routes queries to the right agents
│   │   ├── driveAgent.js
│   │   ├── gmailAgent.js
│   │   ├── calendarAgent.js
│   │   ├── notionAgent.js
│   │   ├── formsAgent.js
│   │   ├── codeAgent.js
│   │   └── visionAgent.js
│   └── tools/
│       ├── gdrive.js         # Google Drive API calls
│       ├── gmail.js          # Gmail API calls
│       ├── calendar.js       # Google Calendar API calls
│       ├── forms.js          # Google Forms API calls
│       └── notion.js         # Notion SDK calls
└── frontend/
    └── src/
        ├── App.jsx
        └── components/
            ├── ChatWindow.jsx
            └── Sidebar.jsx
```

---

## Prerequisites

- Node.js 18+
- A [Groq API key](https://console.groq.com) (free tier available)
- A Google Cloud project with OAuth 2.0 credentials (for Google integrations)
- A Notion integration token (for Notion search)

---

## Setup

### 1. Install dependencies

From the project root:

```bash
npm install
npm install --prefix backend
npm install --prefix frontend
```

### 2. Configure environment variables

Create a `.env` file inside the `backend/` folder:

```env
# Required — Groq LLM (routing + responses)
GROQ_API_KEY=your_groq_api_key_here

# Required for Google integrations (Drive, Gmail, Calendar, Forms)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:3001/auth/google/callback

# Required for Notion integration
NOTION_TOKEN=your_notion_integration_token
```

### 3. Google OAuth setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project and enable these APIs:
   - Google Drive API
   - Gmail API
   - Google Calendar API
   - Google Forms API
3. Create OAuth 2.0 credentials (Web application type)
4. Add `http://localhost:3001/auth/google/callback` as an authorized redirect URI
5. Copy the Client ID and Secret into your `.env`

### 4. Notion setup

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Create a new integration and copy the token
3. Share the pages/databases you want to query with the integration

---

## Running locally

From the project root (starts both frontend and backend):

```bash
npm run dev
```

Or run them separately:

```bash
npm run backend    # http://localhost:3001
npm run frontend   # http://localhost:5173
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

To connect Google, click **Connect Google** in the sidebar and complete the OAuth flow.

---

## Usage examples

| What you type | What happens |
|---|---|
| `Find my resume in Drive` | Searches Drive by filename and content |
| `Show unread emails` | Fetches unread inbox emails |
| `What meetings do I have today?` | Pulls today's calendar events |
| `How many people filled my feedback form?` | Reads Forms response count |
| `Search my Notion notes about project X` | Searches Notion pages |
| Upload a `.js` file + `explain this` | Code agent analyzes the file |
| Upload an image + `what's in this?` | Vision agent describes the image |

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 8 |
| Backend | Node.js, Express 5 |
| LLM | Groq (llama-3.3-70b-versatile, llama-4-scout-17b for vision) |
| Google APIs | googleapis SDK |
| Notion | @notionhq/client |
| Concurrency | concurrently (root dev script) |

---

## Notes

- **OAuth tokens are stored in memory** — reconnecting Google is required after a server restart
- **Conversation history** is also in-memory and resets on restart
- The frontend is hardcoded to `localhost:3001` — update `ChatWindow.jsx` and `Sidebar.jsx` for production deployments
- The `@anthropic-ai/sdk` package is installed but not currently used
