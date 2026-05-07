import { marked } from 'marked'
import markedKatex from 'marked-katex-extension'
import DOMPurify from 'dompurify'
import katex from 'katex'

// Configure marked once globally.
marked.setOptions({
  gfm: true,
  breaks: true
})

marked.use(markedKatex({
  throwOnError: false,
  output: 'html',
  katex
}))

/**
 * Render Markdown into sanitized HTML for safe display.
 * @param {string} source Raw Markdown content.
 * @returns {string} Sanitized HTML string ready for v-html.
 */
export function renderMarkdown(source) {
  if (!source) {
    return ''
  }
  const placeholders = []
    const placeholderPrefix = '@@MATH_BLOCK_'
    const placeholderSuffix = '_@@'
  const preprocessed = source.replace(/\$\$([\s\S]+?)\$\$/g, (_, expression) => {
    const token = `${placeholderPrefix}${placeholders.length}${placeholderSuffix}`
    try {
      const rendered = katex.renderToString(expression.trim(), {
        throwOnError: false,
        displayMode: true
      })
      placeholders.push({ token, html: DOMPurify.sanitize(rendered) })
    } catch (error) {
      console.error('KaTeX render error:', error)
      placeholders.push({ token, html: DOMPurify.sanitize(expression) })
    }
    return token
  })
  try {
    const rawHtml = marked.parse(preprocessed)
    let sanitized = DOMPurify.sanitize(rawHtml)
    placeholders.forEach(({ token, html }) => {
      sanitized = sanitized.split(token).join(html)
    })
    return sanitized
  } catch (error) {
    console.error('Markdown render error:', error)
    return DOMPurify.sanitize(source)
  }
}
