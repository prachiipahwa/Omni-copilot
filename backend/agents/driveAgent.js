import { searchDrive } from '../tools/gdrive.js'

export async function driveAgent(message) {
  console.log('Drive agent activated')

  // Only remove connecting/filler words, keep the actual subject
  const searchTerm = message
    .replace(/\b(find|search|show|get|look for|do i have|can you find|check|in|my|the|a|an|please|for me)\b/gi, '')
    .trim()

  console.log('Drive searching for:', searchTerm)

  const results = await searchDrive(searchTerm || message)
  return results
}