import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const api = {
  // Events
  getEvents: (userId, skip = 0, limit = 100) =>
    client.get(`/events/${userId}?skip=${skip}&limit=${limit}`),
  
  getLearningEvents: (userId, skip = 0, limit = 50) =>
    client.get(`/events/${userId}/learning?skip=${skip}&limit=${limit}`),
  
  createEvent: (userId, eventData) =>
    client.post(`/events/${userId}`, eventData),
  
  // Analytics
  getDailyAnalytics: (userId, date = null) => {
    const url = date 
      ? `/analytics/${userId}/daily?date=${date}`
      : `/analytics/${userId}/daily`
    return client.get(url)
  },
  
  getWeeklyAnalytics: (userId) =>
    client.get(`/analytics/${userId}/weekly`),
  
  getTopicAnalytics: (userId) =>
    client.get(`/analytics/${userId}/topics`),
  
  getUserSummary: (userId) =>
    client.get(`/analytics/${userId}/summary`),
  
  // RAG Query
  queryKnowledgeBase: (queryData) =>
    client.post('/query/', queryData),

  // ML
  mlStatus: () =>
    client.get('/ml/status'),

  mlClassify: (payload) =>
    client.post('/ml/classify', payload),

  mlFullPredict: (payload) =>
    client.post('/ml/predict', payload),
  
  // Flashcards
  generateFlashcards: (userId, date = null) =>
    client.post('/flashcards/generate', { user_id: userId, date }),
  
  getFlashcardsFromEvents: (userId) =>
    client.get(`/flashcards/${userId}/from-events`),

  getDueFlashcards: (userId) =>
    client.get(`/flashcards/${userId}/due`),
  
  getUserFlashcards: (userId, skip = 0, limit = 50) =>
    client.get(`/flashcards/${userId}?skip=${skip}&limit=${limit}`),
  
  reviewFlashcard: (flashcardId, difficulty) =>
    client.post(`/flashcards/${flashcardId}/review`, { difficulty }),
  
  // Health
  healthCheck: () =>
    client.get('/health', { baseURL: API_BASE_URL.replace('/api', '') }),
}

export default client
