import Groq from 'groq-sdk'
import dotenv from 'dotenv'
dotenv.config()

const groq = new Groq({ apiKey: process.env.GROQ_API_KEY })

export async function visionAgent(message, image) {
  console.log('Vision agent activated')

  const response = await groq.chat.completions.create({
    model: 'meta-llama/llama-4-scout-17b-16e-instruct',
    messages: [
      {
        role: 'user',
        content: [
          { type: 'image_url', image_url: { url: image } },
          { type: 'text', text: message || 'Describe this image in detail.' }
        ]
      }
    ],
    max_tokens: 1024
  })

  return response.choices[0].message.content
}