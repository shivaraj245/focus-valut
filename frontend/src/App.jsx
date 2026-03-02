import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Events from './pages/Events'
import Query from './pages/Query'
import Flashcards from './pages/Flashcards'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center">
                <span className="text-2xl font-bold">🧠 FocusVault</span>
              </div>
              <div className="flex space-x-4">
                <Link to="/" className="px-3 py-2 rounded-md text-sm font-medium hover:bg-indigo-700">
                  Dashboard
                </Link>
                <Link to="/events" className="px-3 py-2 rounded-md text-sm font-medium hover:bg-indigo-700">
                  Events
                </Link>
                <Link to="/query" className="px-3 py-2 rounded-md text-sm font-medium hover:bg-indigo-700">
                  Ask AI
                </Link>
                <Link to="/flashcards" className="px-3 py-2 rounded-md text-sm font-medium hover:bg-indigo-700">
                  Flashcards
                </Link>
              </div>
            </div>
          </div>
        </nav>

        <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/events" element={<Events />} />
            <Route path="/query" element={<Query />} />
            <Route path="/flashcards" element={<Flashcards />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

export default App
