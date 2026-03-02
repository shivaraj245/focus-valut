import { useState } from 'react'
import { api } from '../api/client'

function Query() {
  const [userId] = useState(1)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!question.trim()) return

    try {
      setLoading(true)
      setError(null)
      
      const response = await api.queryKnowledgeBase({
        question: question.trim(),
        user_id: userId,
        top_k: 5,
      })

      setAnswer(response.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to query knowledge base')
    } finally {
      setLoading(false)
    }
  }

  const exampleQuestions = [
    "What is dynamic programming?",
    "How do I implement a binary search tree?",
    "Explain the difference between React hooks",
    "What are the SOLID principles?",
  ]

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900">Ask Your Knowledge Base</h1>
        <p className="mt-2 text-gray-600">
          Query your personal learning history using AI-powered RAG
        </p>
      </div>

      {/* Query Form */}
      <div className="bg-white rounded-lg shadow p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="question" className="block text-sm font-medium text-gray-700 mb-2">
              Your Question
            </label>
            <textarea
              id="question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask anything about what you've learned..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
              rows={4}
            />
          </div>

          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="w-full px-6 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition"
          >
            {loading ? 'Searching...' : 'Ask Question'}
          </button>
        </form>

        {/* Example Questions */}
        <div className="mt-6">
          <div className="text-sm font-medium text-gray-700 mb-2">Example questions:</div>
          <div className="flex flex-wrap gap-2">
            {exampleQuestions.map((q, index) => (
              <button
                key={index}
                onClick={() => setQuestion(q)}
                className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {/* Answer */}
      {answer && (
        <div className="bg-white rounded-lg shadow p-6 space-y-6">
          <div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">Answer</h2>
            <div className="prose max-w-none">
              <p className="text-gray-700 whitespace-pre-wrap">{answer.answer}</p>
            </div>
            <div className="mt-4 flex items-center text-sm text-gray-500">
              <span className="font-medium">Confidence:</span>
              <div className="ml-2 flex-1 max-w-xs bg-gray-200 rounded-full h-2">
                <div
                  className="bg-green-500 h-2 rounded-full"
                  style={{ width: `${answer.confidence * 100}%` }}
                />
              </div>
              <span className="ml-2">{Math.round(answer.confidence * 100)}%</span>
            </div>
          </div>

          {/* Sources */}
          {answer.contexts && answer.contexts.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-3">Sources</h3>
              <div className="space-y-3">
                {answer.contexts.map((context, index) => (
                  <div key={index} className="border border-gray-200 rounded-lg p-4 hover:border-indigo-300 transition">
                    <div className="flex items-start justify-between mb-2">
                      <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-indigo-100 text-indigo-800">
                        {context.topic_name}
                      </span>
                      <span className="text-xs text-gray-500">
                        Score: {Math.round(context.score * 100)}%
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 mb-2">{context.text}</p>
                    <a
                      href={context.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-indigo-600 hover:text-indigo-800 truncate block"
                    >
                      {context.url}
                    </a>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default Query
