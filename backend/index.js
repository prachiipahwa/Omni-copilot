import express from 'express'
import cors from 'cors'
import dotenv from 'dotenv'
import { chatHandler } from './routes/chat.js'
import { googleAuthStart, googleAuthCallback, isGoogleConnected } from './routes/auth.js'
dotenv.config()

const app = express()

// CORS — allow only the known frontend origins
const allowedOrigins = [
  'http://localhost:5173',
  'https://omni-copilot-aic9.vercel.app',
  process.env.FRONTEND_URL,
].filter(Boolean)

app.use(cors({
  origin: (origin, callback) => {
    // Allow requests with no origin (curl, Postman, server-to-server)
    if (!origin) return callback(null, true)
    if (allowedOrigins.includes(origin)) return callback(null, true)
    callback(new Error(`CORS: origin ${origin} not allowed`))
  },
  credentials: true
}))

app.use(express.json({ limit: '20mb' }))

app.get('/api/health', (req, res) => {
  res.json({ status: 'Omni Copilot backend is alive!' })
})

app.get('/api/auth/status', (req, res) => {
  res.json({ connected: isGoogleConnected() })
})

app.post('/api/chat', chatHandler)

// Google auth routes
app.get('/auth/google', googleAuthStart)
app.get('/auth/google/callback', googleAuthCallback)

const PORT = process.env.PORT || 3001
app.listen(PORT, () => {
  console.log(`Backend running on port ${PORT}`)
})