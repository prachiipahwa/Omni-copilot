import { Client } from '@notionhq/client'
import dotenv from 'dotenv'
dotenv.config()

const notion = new Client({ auth: process.env.NOTION_TOKEN })

// Search across all pages and databases
export async function searchNotion(query) {
  if (!process.env.NOTION_TOKEN) {
    return 'Notion is not connected. Please add NOTION_TOKEN to your .env file.'
  }

  try {
    const response = await notion.search({
      query: query,
      filter: { value: 'page', property: 'object' },
      page_size: 5
    })

    const results = response.results

    if (!results || results.length === 0) {
      return `No Notion pages found matching "${query}".`
    }

    // For each result, get the page title and content
    const pages = await Promise.all(
      results.map(async (page) => {
        // Get title
        const title = page.properties?.title?.title?.[0]?.plain_text
          || page.properties?.Name?.title?.[0]?.plain_text
          || 'Untitled'

        // Get page content (blocks)
        const blocks = await notion.blocks.children.list({
          block_id: page.id,
          page_size: 10   // first 10 blocks only
        })

        // Extract text from blocks
        const content = blocks.results
          .map(block => {
            const type = block.type
            const richText = block[type]?.rich_text
            if (!richText) return null
            return richText.map(t => t.plain_text).join('')
          })
          .filter(Boolean)
          .join('\n')

        const url = page.url

        return `Page: ${title}\nURL: ${url}\nContent preview:\n${content || 'No text content found'}`
      })
    )

    return pages.join('\n\n---\n\n')

  } catch (err) {
    console.error('Notion error:', err.message)
    return 'Failed to fetch from Notion: ' + err.message
  }
}

// Get a specific page by title (exact or close match)
export async function getNotionPage(title) {
  if (!process.env.NOTION_TOKEN) {
    return 'Notion is not connected.'
  }

  try {
    const response = await notion.search({
      query: title,
      filter: { value: 'page', property: 'object' },
      page_size: 1
    })

    if (!response.results.length) {
      return `No page found with title "${title}" in Notion.`
    }

    const page = response.results[0]
    const pageTitle = page.properties?.title?.title?.[0]?.plain_text
      || page.properties?.Name?.title?.[0]?.plain_text
      || 'Untitled'

    // Get full content
    const blocks = await notion.blocks.children.list({
      block_id: page.id,
      page_size: 50   // more blocks for full read
    })

    const content = blocks.results
      .map(block => {
        const type = block.type
        const richText = block[type]?.rich_text
        if (!richText) return null
        return richText.map(t => t.plain_text).join('')
      })
      .filter(Boolean)
      .join('\n')

    return `Page: ${pageTitle}\nURL: ${page.url}\n\nFull content:\n${content || 'Page is empty.'}`

  } catch (err) {
    console.error('Notion error:', err.message)
    return 'Failed to read Notion page: ' + err.message
  }
}