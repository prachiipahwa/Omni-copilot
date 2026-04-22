import { google } from 'googleapis'
import dotenv from 'dotenv'
dotenv.config()

let storedTokens = null

function getOAuthClient() {
  const clientId = process.env.GOOGLE_CLIENT_ID
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET
  const redirectUri = process.env.GOOGLE_REDIRECT_URI

  // Debug — remove after confirming it works
  console.log('CLIENT_ID:', clientId ? 'found' : 'MISSING')
  console.log('SECRET:', clientSecret ? 'found' : 'MISSING')
  console.log('REDIRECT:', redirectUri)

  return new google.auth.OAuth2(clientId, clientSecret, redirectUri)
}

export function googleAuthStart(req, res) {
  const oauth2Client = getOAuthClient()

  const url = oauth2Client.generateAuthUrl({
    access_type: 'offline',
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
  return oauth2Client
}