import { google } from 'googleapis'
import { getAuthenticatedClient } from '../routes/auth.js'

export async function searchDrive(query) {
  const auth = getAuthenticatedClient()
  if (!auth) {
    return 'Google Drive is not connected. Please login first at http://localhost:3001/auth/google'
  }

  const drive = google.drive({ version: 'v3', auth })

  try {
    console.log('Drive searching for:', query)

    // Search both filename AND full text content
    const response = await drive.files.list({
      q: `(name contains '${query}' or fullText contains '${query}') and trashed = false`,
      fields: 'files(id, name, mimeType, modifiedTime, webViewLink)',
      pageSize: 5,
      orderBy: 'modifiedTime desc'
    })

    const files = response.data.files
    if (!files || files.length === 0) {
      return `No files found matching "${query}" in your Google Drive.`
    }

    return `Found ${files.length} file(s):\n` + files.map(f =>
      `- ${f.name} (modified: ${new Date(f.modifiedTime).toLocaleDateString()}) — ${f.webViewLink}`
    ).join('\n')

  } catch (err) {
    console.error('Drive error:', err.message)
    return 'Failed to search Drive: ' + err.message
  }
}