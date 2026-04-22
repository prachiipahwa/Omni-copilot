import Groq from 'groq-sdk'
import dotenv from 'dotenv'
import { driveAgent } from './driveAgent.js'
import { gmailAgent } from './gmailAgent.js'
import { calendarAgent } from './calendarAgent.js'
import { notionAgent } from './notionAgent.js'
import { visionAgent } from './visionAgent.js'
import { codeAgent } from './codeAgent.js'
import { formsAgent } from './formsAgent.js'
dotenv.config()

const groq = new Groq({ apiKey: process.env.GROQ_API_KEY })
const conversationHistory = []

export async function orchestrator(message, image, code, filename) {

  // Code file takes priority if attached
  if (code) {
    const reply = await codeAgent(message, code, filename)
    conversationHistory.push({ role: 'user', content: `[Uploaded ${filename}] ${message}` })
    conversationHistory.push({ role: 'assistant', content: reply })
    return reply
  }

  // Image flow
  if (image) {
    const reply = await visionAgent(message, image)
    conversationHistory.push({ role: 'user', content: message || 'analyze image' })
    conversationHistory.push({ role: 'assistant', content: reply })
    return reply
  }

  // Normal routing flow — rest of your existing orchestrator code stays exactly the same
  const routingResponse = await groq.chat.completions.create({
    model: 'llama-3.3-70b-versatile',
    messages: [
      {
        role: 'system',
        content: `You are a routing agent. Given a user message, decide which specialist agents are needed.
        
Available agents:
- drive: searches Google Drive files and documents
- gmail: reads emails from Gmail inbox  
- calendar: checks Google Calendar events and schedule
- notion: searches Notion pages and notes
- forms: reads Google Forms responses and survey results
- none: general conversation, no tools needed

Reply with ONLY a JSON array of agent names needed. Examples:
- "find my resume" → ["drive"]
- "do i have meetings today" → ["calendar"]
- "show form responses" → ["forms"]
- "how many people filled my survey" → ["forms"]
- "check feedback form results" → ["forms"]
- "any emails about the project doc" → ["gmail", "drive"]
- "hello how are you" → ["none"]

Reply with JSON only, no explanation.`
      },
      { role: 'user', content: message }
    ],
    max_tokens: 100
  })

  let agentsNeeded = ['none']
  try {
    const raw = routingResponse.choices[0].message.content.trim()
    agentsNeeded = JSON.parse(raw)
    console.log('Agents selected:', agentsNeeded)
  } catch {
    console.log('Routing parse failed, using no tools')
  }

  const agentPromises = agentsNeeded.map(agent => {
    switch (agent) {
  case 'drive':    return driveAgent(message)
  case 'gmail':    return gmailAgent(message)
  case 'calendar': return calendarAgent(message)
  case 'notion':   return notionAgent(message)
  case 'forms':    return formsAgent(message)
  default:         return Promise.resolve(null)
}
  })

  const agentResults = await Promise.all(agentPromises)

  let toolContext = ''
  agentsNeeded.forEach((agent, i) => {
    if (agentResults[i] && agent !== 'none') {
      toolContext += `\n\n[${agent.toUpperCase()} AGENT RESULTS]:\n${agentResults[i]}`
    }
  })

  conversationHistory.push({ role: 'user', content: message })

  const finalResponse = await groq.chat.completions.create({
    model: 'llama-3.3-70b-versatile',
    messages: [
      {
        role: 'system',
        content: `You are Omni Copilot, a smart AI assistant with access to the user's entire workspace.
        ${toolContext
          ? `\nThe following specialist agents have fetched live data for you:\n${toolContext}
          \nUse this real data to give an accurate, helpful answer. Reference specific names, dates, links.`
          : '\nNo workspace tools were needed for this message. Just reply conversationally.'
        }`
      },
      ...conversationHistory
    ],
    max_tokens: 1024
  })

  const reply = finalResponse.choices[0].message.content
  conversationHistory.push({ role: 'assistant', content: reply })
  return reply
}