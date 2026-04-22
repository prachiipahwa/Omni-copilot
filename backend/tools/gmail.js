import { google } from 'googleapis'
import { getAuthenticatedClient } from '../routes/auth.js'

export async function getRecentEmails(query = '') {
  const auth = getAuthenticatedClient()
  if (!auth) return 'Gmail is not connected. Please login first.'

  const gmail = google.gmail({ version: 'v1', auth })

  try {
    const gmailQuery = buildGmailQuery(query)
    console.log('Gmail query:', gmailQuery)

    const response = await gmail.users.messages.list({
      userId: 'me',
      q: gmailQuery,
      maxResults: 15
    })

    const messages = response.data.messages
    if (!messages || messages.length === 0) {
      return `No emails found for: "${gmailQuery}".`
    }

    const emailDetails = await Promise.all(
      messages.map(async (msg) => {
        const detail = await gmail.users.messages.get({
          userId: 'me',
          id: msg.id,
          format: 'metadata',
          metadataHeaders: ['Subject', 'From', 'Date', 'To']
        })
        const headers = detail.data.payload.headers
        const subject  = headers.find(h => h.name === 'Subject')?.value || 'No subject'
        const from     = headers.find(h => h.name === 'From')?.value || 'Unknown'
        const date     = headers.find(h => h.name === 'Date')?.value || ''
        const hasAttachment = detail.data.payload.parts?.some(
          p => p.filename && p.filename.length > 0
        )
        return `- From: ${from}\n  Subject: ${subject}\n  Date: ${date}${hasAttachment ? '\n  [Has attachment]' : ''}`
      })
    )

    return `Found ${emailDetails.length} email(s) matching "${gmailQuery}":\n\n` + emailDetails.join('\n\n')

  } catch (err) {
    console.error('Gmail error:', err.message)
    return 'Failed to fetch emails: ' + err.message
  }
}

function buildGmailQuery(userMessage) {
  let parts = []

  // --- Date filters ---
  if (/\btoday\b/i.test(userMessage)) {
    const d = new Date()
    parts.push(`after:${d.getFullYear()}/${pad(d.getMonth()+1)}/${pad(d.getDate())}`)
  } else if (/\byesterday\b/i.test(userMessage)) {
    const d = new Date()
    d.setDate(d.getDate() - 1)
    const d2 = new Date()
    parts.push(`after:${d.getFullYear()}/${pad(d.getMonth()+1)}/${pad(d.getDate())}`)
    parts.push(`before:${d2.getFullYear()}/${pad(d2.getMonth()+1)}/${pad(d2.getDate())}`)
  } else if (/last\s*week|past\s*week/i.test(userMessage)) {
    parts.push('newer_than:7d')
  } else if (/last\s*month|past\s*month/i.test(userMessage)) {
    parts.push('newer_than:30d')
  } else if (/last\s*(\d+)\s*days?/i.test(userMessage)) {
    const match = userMessage.match(/last\s*(\d+)\s*days?/i)
    parts.push(`newer_than:${match[1]}d`)
  }

  // --- Read/unread filters ---
  if (/\bunread\b/i.test(userMessage)) {
    parts.push('is:unread')
  } else if (/\bread\b/i.test(userMessage) && !/unread/i.test(userMessage)) {
    parts.push('is:read')
  }

  // --- Attachment filter ---
  if (/attachment|attached|with file|has file/i.test(userMessage)) {
    parts.push('has:attachment')
  }

  // --- Folder/label filters ---
  if (/\bspam\b/i.test(userMessage)) {
    parts.push('in:spam')
  } else if (/\bsent\b/i.test(userMessage)) {
    parts.push('in:sent')
  } else if (/\bdraft\b/i.test(userMessage)) {
    parts.push('in:drafts')
  } else if (/\bpromotion|promotional\b/i.test(userMessage)) {
    parts.push('category:promotions')
  } else if (/\bsocial\b/i.test(userMessage)) {
    parts.push('category:social')
  } else {
    parts.push('in:inbox')
  }

  // --- From filter ---
  const fromMatch = userMessage.match(/from\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/i)
  if (fromMatch) {
    parts.push(`from:${fromMatch[1]}`)
  } else {
    // Try matching "from Google" or "from Amazon" style
    const fromNameMatch = userMessage.match(/from\s+([a-zA-Z]+)/i)
    if (fromNameMatch && !['my', 'the', 'a', 'an', 'show', 'get', 'find'].includes(fromNameMatch[1].toLowerCase())) {
      parts.push(`from:${fromNameMatch[1]}`)
    }
  }

  // --- Subject/keyword filter ---
  const stopWords = /\b(show|get|find|check|email|emails|mail|inbox|me|my|all|any|have|i|do|the|a|an|about|please|unread|read|today|yesterday|recent|latest|new|old|from|sent|spam|draft|attachment|attached|last|week|month|days|with|has|file|and|or|in)\b/gi
  const keyword = userMessage.replace(stopWords, '').trim()

  if (keyword.length > 2) {
    parts.push(keyword)
  }

  return parts.join(' ').trim() || 'in:inbox'
}

function pad(n) {
  return String(n).padStart(2, '0')
}