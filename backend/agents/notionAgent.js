import { searchNotion } from '../tools/notion.js'

export async function notionAgent(message) {
  console.log('Notion agent activated')

  const searchTerm = message
    .replace(/notion|note|notes|page|pages|find|search|show|get|my|in|about|for/gi, '')
    .trim()

  const results = await searchNotion(searchTerm || message)
  return results
}