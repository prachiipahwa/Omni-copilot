import { google } from 'googleapis'
import { getAuthenticatedClient } from '../routes/auth.js'

export async function getFormResponses(query = '') {
  const auth = getAuthenticatedClient()
  if (!auth) return 'Google is not connected. Please login first.'

  try {
    // Step 1 — Find forms in Google Drive
    const drive = google.drive({ version: 'v3', auth })

    const searchQuery = query && query.length > 2
      ? `mimeType='application/vnd.google-apps.form' and name contains '${query}' and trashed=false`
      : `mimeType='application/vnd.google-apps.form' and trashed=false`

    console.log('Forms search query:', searchQuery)

    const formsResponse = await drive.files.list({
      q: searchQuery,
      fields: 'files(id, name, modifiedTime)',
      pageSize: 5,
      orderBy: 'modifiedTime desc'
    })

    const forms = formsResponse.data.files
    if (!forms || forms.length === 0) {
      return `No Google Forms found${query ? ` matching "${query}"` : ''} in your Drive.`
    }

    console.log(`Found ${forms.length} form(s)`)

    // Step 2 — For each form get responses via Forms API
    const forms_api = google.forms({ version: 'v1', auth })
    const sheets    = google.sheets({ version: 'v4', auth })

    const results = await Promise.all(forms.map(async (form) => {
      try {
        // Get form details
        const formDetail = await forms_api.forms.get({ formId: form.id })
        const title      = formDetail.data.info.title || form.name
        const questions  = formDetail.data.items || []

        // Get responses
        const responsesData = await forms_api.forms.responses.list({
          formId: form.id
        })

        const responses  = responsesData.data.responses || []
        const totalCount = responses.length

        if (totalCount === 0) {
          return `Form: "${title}"\nResponses: 0 (no one has filled this form yet)`
        }

        // Build question map for readable answers
        const questionMap = {}
        questions.forEach(item => {
          if (item.questionItem) {
            questionMap[item.questionItem.question.questionId] = item.title
          }
        })

        // Get latest 3 responses
        const latest = responses.slice(-3).reverse()
        const responseSummaries = latest.map((r, i) => {
          const answers = Object.entries(r.answers || {}).map(([qId, ans]) => {
            const question = questionMap[qId] || 'Question'
            const answer   = ans.textAnswers?.answers?.[0]?.value
              || ans.grade?.score
              || 'No answer'
            return `    Q: ${question}\n    A: ${answer}`
          }).join('\n')

          const submitted = new Date(r.lastSubmittedTime).toLocaleString('en-IN')
          return `  Response ${i + 1} (submitted: ${submitted}):\n${answers}`
        }).join('\n\n')

        return `Form: "${title}"\nTotal responses: ${totalCount}\n\nLatest ${latest.length} response(s):\n${responseSummaries}`

      } catch (err) {
        return `Form: "${form.name}" — Could not read responses: ${err.message}`
      }
    }))

    return results.join('\n\n' + '─'.repeat(40) + '\n\n')

  } catch (err) {
    console.error('Forms error:', err.message)
    return 'Failed to fetch form responses: ' + err.message
  }
}

// Get summary stats for a specific form
export async function getFormStats(formId, auth) {
  const forms_api = google.forms({ version: 'v1', auth })

  const [formDetail, responsesData] = await Promise.all([
    forms_api.forms.get({ formId }),
    forms_api.forms.responses.list({ formId })
  ])

  const responses  = responsesData.data.responses || []
  const questions  = formDetail.data.items || []
  const title      = formDetail.data.info.title

  // Count answers per question for multiple choice
  const stats = {}
  questions.forEach(item => {
    if (item.questionItem?.question?.choiceQuestion) {
      const qId = item.questionItem.question.questionId
      stats[qId] = { question: item.title, counts: {} }

      responses.forEach(r => {
        const ans = r.answers?.[qId]?.textAnswers?.answers?.[0]?.value
        if (ans) {
          stats[qId].counts[ans] = (stats[qId].counts[ans] || 0) + 1
        }
      })
    }
  })

  return { title, totalResponses: responses.length, stats }
}