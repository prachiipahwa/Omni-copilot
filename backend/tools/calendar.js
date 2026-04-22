import { google } from 'googleapis'
import { getAuthenticatedClient } from '../routes/auth.js'

export async function getCalendarEvents(query = '') {
  const auth = getAuthenticatedClient()

  if (!auth) {
    return 'Google Calendar is not connected. Please login first.'
  }

  const calendar = google.calendar({ version: 'v3', auth })

  try {
    const now = new Date()
    const oneWeekLater = new Date()
    oneWeekLater.setDate(now.getDate() + 7)

    const response = await calendar.events.list({
      calendarId: 'primary',
      timeMin: now.toISOString(),
      timeMax: oneWeekLater.toISOString(),
      maxResults: 10,
      singleEvents: true,
      orderBy: 'startTime',
      q: query || undefined   // filter by keyword if provided
    })

    const events = response.data.items
    if (!events || events.length === 0) {
      return `No upcoming events found${query ? ` matching "${query}"` : ''} in the next 7 days.`
    }

    return events.map(event => {
      const start = event.start.dateTime || event.start.date
      const date = new Date(start).toLocaleString('en-IN', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
      return `- ${event.summary || 'Untitled'} — ${date}${event.location ? ' @ ' + event.location : ''}`
    }).join('\n')

  } catch (err) {
    console.error('Calendar error:', err.message)
    return 'Failed to fetch calendar: ' + err.message
  }
}