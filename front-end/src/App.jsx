import { useState } from 'react'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

async function readResponse(response) {
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(body.error || 'The request could not be completed.')
  }
  return body
}

function App() {
  const [file, setFile] = useState(null)
  const [uploadedFile, setUploadedFile] = useState(null)
  const [isUploading, setIsUploading] = useState(false)
  const [question, setQuestion] = useState('')
  const [isAsking, setIsAsking] = useState(false)
  const [answer, setAnswer] = useState('')
  const [hasAnswerResponse, setHasAnswerResponse] = useState(false)
  const [error, setError] = useState('')

  async function handleUpload(event) {
    event.preventDefault()
    if (!file || isUploading) return

    setError('')
    setIsUploading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(`${API_BASE_URL}/upload_file`, {
        method: 'POST',
        body: formData,
      })
      const data = await readResponse(response)
      setUploadedFile({
        name: data.filename || file.name,
        chunks: data.chunks,
      })
      setFile(null)
    } catch (requestError) {
      setError(requestError.message || 'Unable to upload the file. Please try again.')
    } finally {
      setIsUploading(false)
    }
  }

  async function handleAsk(event) {
    event.preventDefault()
    const trimmedQuestion = question.trim()
    if (!trimmedQuestion || isAsking) return

    setError('')
    setAnswer('')
    setIsAsking(true)
    setHasAnswerResponse(false)

    try {
      const response = await fetch(`${API_BASE_URL}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: trimmedQuestion }),
      })
      const data = await readResponse(response)
      setAnswer(typeof data.answer === 'string' ? data.answer : '')
      setHasAnswerResponse(true)
    } catch (requestError) {
      setError(requestError.message || 'Unable to get an answer. Please try again.')
    } finally {
      setIsAsking(false)
    }
  }

  return (
    <main className="app-shell">
      <header className="page-header">
        <span className="eyebrow">DOCUMENT ASSISTANT</span>
        <h1>Ask your document</h1>
        <p>Upload a text file, then ask a question about its contents.</p>
      </header>

      <section className="workspace" aria-label="Document question and answer">
        {!uploadedFile ? (
          <form className="upload-card" onSubmit={handleUpload}>
            <div className="step-label"><span>1</span> Upload a document</div>
            <label className="file-picker">
              <span className="file-icon" aria-hidden="true">↑</span>
              <span className="file-picker-copy">
                <strong>{file ? file.name : 'Choose a .txt file'}</strong>
                <small>{file ? 'Ready to upload' : 'Only one text file can be uploaded'}</small>
              </span>
              <input
                type="file"
                accept=".txt,text/plain"
                onChange={(event) => {
                  const selectedFile = event.target.files?.[0] ?? null
                  if (selectedFile && !selectedFile.name.toLowerCase().endsWith('.txt')) {
                    setFile(null)
                    setError('Please choose a .txt file.')
                    event.target.value = ''
                    return
                  }
                  setFile(selectedFile)
                  setError('')
                }}
                disabled={isUploading}
              />
            </label>
            <button className="primary-button" type="submit" disabled={!file || isUploading}>
              {isUploading ? (
                <><span className="spinner" aria-hidden="true" /> Uploading file…</>
              ) : (
                'Upload file'
              )}
            </button>
            {isUploading && <p className="status-message" role="status">Uploading and indexing your document. This may take a moment.</p>}
          </form>
        ) : (
          <div className="chat-card">
            <div className="document-status">
              <span className="document-check" aria-hidden="true">✓</span>
              <div>
                <strong>Document ready</strong>
                <span>{uploadedFile.name}{Number.isInteger(uploadedFile.chunks) ? ` · ${uploadedFile.chunks} chunks` : ''}</span>
              </div>
            </div>

            <div className="step-label"><span>2</span> Ask a question</div>
            <form className="question-form" onSubmit={handleAsk}>
              <label className="visually-hidden" htmlFor="question">Your question</label>
              <input
                id="question"
                type="text"
                value={question}
                onChange={(event) => {
                  setQuestion(event.target.value)
                  setHasAnswerResponse(false)
                }}
                placeholder="Ask something about your document…"
                disabled={isAsking}
              />
              <button className="primary-button" type="submit" disabled={!question.trim() || isAsking}>
                {isAsking ? (
                  <><span className="spinner" aria-hidden="true" /> Searching…</>
                ) : (
                  'Ask'
                )}
              </button>
            </form>
            {isAsking && <p className="status-message" role="status">Generating an answer from your document…</p>}

            {answer && (
              <section className="answer-section" aria-live="polite">
                <h2>Answer</h2>
                <article className="answer"><p>{answer}</p></article>
              </section>
            )}
            {hasAnswerResponse && !isAsking && !error && !answer && (
              <p className="empty-response">No answer was returned. Try another question.</p>
            )}
          </div>
        )}
        {error && <p className="error-message" role="alert">{error}</p>}
      </section>
      <footer>Answers are based on the text in your uploaded document.</footer>
    </main>
  )
}

export default App
