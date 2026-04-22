import { google } from 'googleapis'
import dotenv from 'dotenv'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
dotenv.config()

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const TOKEN_PATH = path.join(__dirname, '..', 'tokens.json')

// Load tokens from disk on startup
let storedTokens = null
try {
  if (fs.existsSync(TOKEN_PATH)) {
    storedTokens = JSON.parse(fs.readFileSync(TOKEN_PATH, 'utf-8'))
    console.log('Google tokens loaded from disk ✓')
  }
} catch (err) {
  console.warn('Could not load saved tokens:', err.message)
}

function saveTokens(tokens) {
  try {
    fs.writeFileSync(TOKEN_PATH, JSON.stringify(tokens, null, 2))
    console.log('Google tokens saved to disk ✓')
  } catch (err) {
    console.warn('Could not save tokens:', err.message)
  }
}

function getOAuthClient() {
  const clientId     = process.env.GOOGLE_CLIENT_ID
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET
  const redirectUri  = process.env.GOOGLE_REDIRECT_URI
  return new google.auth.OAuth2(clientId, clientSecret, redirectUri)
}

export function googleAuthStart(req, res) {
  const oauth2Client = getOAuthClient()

  const url = oauth2Client.generateAuthUrl({
    access_type: 'offline',
    prompt: 'consent',   // force refresh_token to be returned every time
    scope: [
      'https://www.googleapis.com/auth/drive.readonly',
      'https://www.googleapis.com/auth/gmail.readonly',
      'https://www.googleapis.com/auth/calendar.readonly',
      'https://www.googleapis.com/auth/spreadsheets.readonly',
      'https://www.googleapis.com/auth/forms.responses.readonly'
    ]
  })

  res.redirect(url)
}

export async function googleAuthCallback(req, res) {
  const { code } = req.query
  const oauth2Client = getOAuthClient()

  try {
    const { tokens } = await oauth2Client.getToken(code)
    storedTokens = tokens
    saveTokens(tokens)
    res.redirect('http://localhost:5173?connected=true')
  } catch (err) {
    console.error('Auth error:', err.message)
    res.status(500).send('Authentication failed: ' + err.message)
  }
}

export function getAuthenticatedClient() {
  if (!storedTokens) return null
  const oauth2Client = getOAuthClient()
  oauth2Client.setCredentials(storedTokens)

  // Auto-refresh: if access token is expired, googleapis will use refresh_token automatically
  oauth2Client.on('tokens', (newTokens) => {
    if (newTokens.refresh_token) {
      storedTokens = { ...storedTokens, ...newTokens }
    } else {
      storedTokens = { ...storedTokens, access_token: newTokens.access_token, expiry_date: newTokens.expiry_date }
    }
    saveTokens(storedTokens)
  })

  return oauth2Client
}

// Expose whether tokens are loaded (for health/status checks)
export function isGoogleConnected() {
  return storedTokens !== null
}