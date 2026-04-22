import express from 'express'
import cors from 'cors'
import dotenv from 'dotenv'
import { chatHandler } from './routes/chat.js'
import { googleAuthStart, googleAuthCallback } from './routes/auth.js'
dotenv.config()

const app = express()
app.use(cors())
app.use(express.json({ limit: '20mb' }))

app.get('/api/health', (req, res) => {
  res.json({ status: 'Omni Copilot backend is alive!' })
})

app.post('/api/chat', chatHandler)

// Google auth routes
app.get('/auth/google', googleAuthStart)
app.get('/auth/google/callback', googleAuthCallback)

app.listen(3001, () => {
  console.log('Backend running on http://localhost:3001')
})