import { getCalendarEvents } from '../tools/calendar.js'

export async function calendarAgent(message) {
  console.log('Calendar agent activated')

  const searchTerm = message
    .replace(/calendar|schedule|meeting|meetings|event|events|show|get|my|what|are|any|check/gi, '')
    .trim()

  const results = await getCalendarEvents(searchTerm || '')
  return results
}