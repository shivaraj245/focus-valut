import { useState, useEffect } from 'react'
import { api } from '../api/client'

function Flashcards() {
  const [userId] = useState(1)
  const [flashcards, setFlashcards] = useState([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [showAnswer, setShowAnswer] = useState(false)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    loadFlashcards()
  }, [])

  const loadFlashcards = async () => {
    try {
      setLoading(true)
      const response = await api.getDueFlashcards(userId)
      setFlashcards(response.data)
      setCurrentIndex(0)
      setShowAnswer(false)
    } catch (error) {
      console.error('Error loading flashcards:', error)
    } finally {
      setLoading(false)
    }
  }

  const generateFlashcards = async () => {
    try {
      setGenerating(true)
      await api.generateFlashcards(userId)
      await loadFlashcards()
    } catch (error) {
      console.error('Error generating flashcards:', error)
    } finally {
      setGenerating(false)
    }
  }

  const handleReview = async (difficulty) => {
    const flashcard = flashcards[currentIndex]
    
    try {
      await api.reviewFlashcard(flashcard.id, difficulty)
      
      if (currentIndex < flashcards.length - 1) {
        setCurrentIndex(currentIndex + 1)
        setShowAnswer(false)
      } else {
        await loadFlashcards()
      }
    } catch (error) {
      console.error('Error reviewing flashcard:', error)
    }
  }

  const currentCard = flashcards[currentIndex]

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-xl text-gray-600">Loading flashcards...</div>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900">Flashcards</h1>
        <p className="mt-2 text-gray-600">
          Review your learning with AI-generated flashcards
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <div className="text-2xl font-bold text-indigo-600">{flashcards.length}</div>
          <div className="text-sm text-gray-600">Due Today</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <div className="text-2xl font-bold text-purple-600">{currentIndex + 1}</div>
          <div className="text-sm text-gray-600">Current Card</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 text-center">
          <div className="text-2xl font-bold text-green-600">
            {flashcards.length - currentIndex}
          </div>
          <div className="text-sm text-gray-600">Remaining</div>
        </div>
      </div>

      {/* Flashcard */}
      {currentCard ? (
        <div className="bg-white rounded-lg shadow-lg p-8">
          <div className="min-h-[300px] flex flex-col justify-center">
            <div className="mb-6">
              <div className="text-sm font-medium text-gray-500 mb-2">Question</div>
              <div className="text-xl text-gray-900">{currentCard.question}</div>
            </div>

            {showAnswer && (
              <div className="mt-6 pt-6 border-t border-gray-200">
                <div className="text-sm font-medium text-gray-500 mb-2">Answer</div>
                <div className="text-lg text-gray-700">{currentCard.answer}</div>
                
                {currentCard.source_url && (
                  <a
                    href={currentCard.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-4 inline-block text-sm text-indigo-600 hover:text-indigo-800"
                  >
                    View Source →
                  </a>
                )}
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="mt-8 flex justify-center space-x-4">
            {!showAnswer ? (
              <button
                onClick={() => setShowAnswer(true)}
                className="px-8 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition"
              >
                Show Answer
              </button>
            ) : (
              <>
                <button
                  onClick={() => handleReview('hard')}
                  className="px-6 py-3 bg-red-100 text-red-700 font-medium rounded-lg hover:bg-red-200 transition"
                >
                  Hard (1 day)
                </button>
                <button
                  onClick={() => handleReview('medium')}
                  className="px-6 py-3 bg-yellow-100 text-yellow-700 font-medium rounded-lg hover:bg-yellow-200 transition"
                >
                  Medium (3 days)
                </button>
                <button
                  onClick={() => handleReview('easy')}
                  className="px-6 py-3 bg-green-100 text-green-700 font-medium rounded-lg hover:bg-green-200 transition"
                >
                  Easy (7 days)
                </button>
              </>
            )}
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="text-6xl mb-4">🎉</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">All Done!</h2>
          <p className="text-gray-600 mb-6">
            No flashcards due right now. Generate new ones from your recent learning.
          </p>
          <button
            onClick={generateFlashcards}
            disabled={generating}
            className="px-6 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:bg-gray-400 transition"
          >
            {generating ? 'Generating...' : 'Generate Flashcards'}
          </button>
        </div>
      )}

      {/* Generate Button */}
      {flashcards.length > 0 && (
        <div className="text-center">
          <button
            onClick={generateFlashcards}
            disabled={generating}
            className="px-6 py-2 bg-white text-indigo-600 border border-indigo-600 font-medium rounded-lg hover:bg-indigo-50 disabled:bg-gray-100 disabled:text-gray-400 disabled:border-gray-300 transition"
          >
            {generating ? 'Generating...' : 'Generate More Flashcards'}
          </button>
        </div>
      )}
    </div>
  )
}

export default Flashcards
