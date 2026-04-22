import Groq from 'groq-sdk'
import dotenv from 'dotenv'
dotenv.config()

const groq = new Groq({ apiKey: process.env.GROQ_API_KEY })

export async function codeAgent(message, code, filename) {
  console.log('Code agent activated for:', filename)

  // Detect language from file extension
  const ext = filename?.split('.').pop()?.toLowerCase()
  const languageMap = {
    js: 'JavaScript', jsx: 'React JSX', ts: 'TypeScript',
    py: 'Python', java: 'Java', cpp: 'C++', c: 'C',
    cs: 'C#', go: 'Go', rb: 'Ruby', php: 'PHP',
    html: 'HTML', css: 'CSS', json: 'JSON', sql: 'SQL',
    rs: 'Rust', swift: 'Swift', kt: 'Kotlin'
  }
  const language = languageMap[ext] || 'code'

  // Figure out what user wants to do with the code
  const wantsFix     = /fix|bug|error|wrong|broken|issue|problem/i.test(message)
  const wantsExplain = /explain|what|how|understand|describe|tell me/i.test(message)
  const wantsImprove = /improve|optimize|better|refactor|clean|enhance/i.test(message)
  const wantsReview  = /review|check|look at|feedback|critique/i.test(message)

  let taskInstruction = message
  if (wantsFix)     taskInstruction = `Find and fix all bugs in this code. Show the fixed version with explanation of what was wrong.`
  if (wantsExplain) taskInstruction = `Explain this code clearly. Break it down line by line or section by section. Make it easy to understand for a beginner.`
  if (wantsImprove) taskInstruction = `Improve and optimize this code. Make it cleaner, faster, and more readable. Show the improved version.`
  if (wantsReview)  taskInstruction = `Do a thorough code review. Check for bugs, security issues, performance problems, and bad practices. Give specific feedback.`

  try {
    const response = await groq.chat.completions.create({
      model: 'llama-3.3-70b-versatile',
      messages: [
        {
          role: 'system',
          content: `You are an expert ${language} developer and code reviewer. 
          You give clear, accurate, helpful analysis of code.
          Always format code blocks with proper syntax highlighting markers.
          Be specific — reference actual line numbers and variable names from the code.`
        },
        {
          role: 'user',
          content: `Here is a ${language} file called "${filename}":\n\n\`\`\`${ext}\n${code}\n\`\`\`\n\n${taskInstruction}`
        }
      ],
      max_tokens: 2048   // more tokens for code responses
    })

    return response.choices[0].message.content

  } catch (err) {
    console.error('Code agent error:', err.message)
    return 'Failed to analyze code: ' + err.message
  }
}