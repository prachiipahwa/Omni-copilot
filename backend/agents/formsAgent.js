import { getFormResponses } from '../tools/forms.js'

export async function formsAgent(message) {
  console.log('Forms agent activated')

  const searchTerm = message
    .replace(/\b(show|get|find|check|form|forms|responses|response|survey|answers|filled|submitted|how many|people|results|from|my|the|a|an|about|for|google)\b/gi, '')
    .trim()

  console.log('Forms searching for:', searchTerm)

  const results = await getFormResponses(searchTerm)
  return results
}