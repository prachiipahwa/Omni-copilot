import { getRecentEmails } from '../tools/gmail.js'

export async function gmailAgent(message) {
  console.log('Gmail agent activated')

  const searchTerm = message
    .replace(/email|emails|mail|inbox|show|get|my|recent|latest|any|check/gi, '')
    .trim()

  const results = await getRecentEmails(searchTerm || '')
  return results
}