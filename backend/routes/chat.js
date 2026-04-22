import dotenv from 'dotenv'
import { orchestrator } from '../agents/orchestrator.js'
dotenv.config()

export async function chatHandler(req, res) {
  const { message, image, code, filename } = req.body

  if (!message && !image && !code) {
    return res.status(400).json({ error: 'No input provided' })
  }

  try {
    const reply = await orchestrator(message, image, code, filename)
    res.json({ reply })
  } catch (error) {
    console.error('Orchestrator error:', error.message)
    res.status(500).json({ error: 'Something went wrong: ' + error.message })
  }
}