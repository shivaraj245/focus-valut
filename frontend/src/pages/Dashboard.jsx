import { useState, useEffect } from 'react'
import { api } from '../api/client'
import { BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const COLORS = ['#667eea', '#764ba2', '#f093fb', '#4facfe', '#43e97b']

function Dashboard() {
  const [userId] = useState(1)
  const [summary, setSummary] = useState(null)
  const [dailyStats, setDailyStats] = useState(null)
  const [weeklyStats, setWeeklyStats] = useState(null)
  const [topicStats, setTopicStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)
      const [summaryRes, dailyRes, weeklyRes, topicRes] = await Promise.all([
        api.getUserSummary(userId),
        api.getDailyAnalytics(userId),
        api.getWeeklyAnalytics(userId),
        api.getTopicAnalytics(userId),
      ])

      setSummary(summaryRes.data)
      setDailyStats(dailyRes.data)
      setWeeklyStats(weeklyRes.data)
      setTopicStats(topicRes.data)
    } catch (error) {
      console.error('Error loading dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-xl text-gray-600">Loading dashboard...</div>
      </div>
    )
  }

  const weeklyChartData = weeklyStats ? Object.entries(weeklyStats.daily_stats).map(([date, stats]) => ({
    date: new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    learning: Math.round(stats.learning_time / 60),
    total: Math.round(stats.total_time / 60),
  })) : []

  const activityPieData = dailyStats ? Object.entries(dailyStats.activity_breakdown).map(([name, value]) => ({
    name: name.charAt(0).toUpperCase() + name.slice(1),
    value: Math.round(value / 60),
  })) : []

  const topTopics = topicStats ? topicStats.topics.slice(0, 5) : []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-gray-900">Learning Dashboard</h1>
        <button
          onClick={loadData}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition"
        >
          Refresh
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-600">Total Events</div>
          <div className="text-3xl font-bold text-indigo-600 mt-2">{summary?.total_events || 0}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-600">Learning Events</div>
          <div className="text-3xl font-bold text-purple-600 mt-2">{summary?.learning_events || 0}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-600">Total Time</div>
          <div className="text-3xl font-bold text-blue-600 mt-2">{summary?.total_time_hours || 0}h</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <div className="text-sm font-medium text-gray-600">Learning %</div>
          <div className="text-3xl font-bold text-green-600 mt-2">{summary?.learning_percentage || 0}%</div>
        </div>
      </div>

      {/* Today's Stats */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Today's Activity</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <div className="text-sm text-gray-600">Pages Visited</div>
            <div className="text-2xl font-bold text-gray-900">{dailyStats?.total_events || 0}</div>
          </div>
          <div>
            <div className="text-sm text-gray-600">Learning Time</div>
            <div className="text-2xl font-bold text-indigo-600">{dailyStats?.learning_time_minutes || 0} min</div>
          </div>
          <div>
            <div className="text-sm text-gray-600">Learning %</div>
            <div className="text-2xl font-bold text-purple-600">{dailyStats?.learning_percentage || 0}%</div>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Weekly Trend */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Weekly Learning Trend</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={weeklyChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis label={{ value: 'Minutes', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              <Bar dataKey="learning" fill="#667eea" name="Learning" />
              <Bar dataKey="total" fill="#cbd5e0" name="Total" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Activity Breakdown */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Today's Activity Breakdown</h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={activityPieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {activityPieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top Topics */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Top Learning Topics</h2>
        <div className="space-y-4">
          {topTopics.map((topic, index) => (
            <div key={index} className="flex items-center justify-between">
              <div className="flex-1">
                <div className="font-medium text-gray-900">{topic.name}</div>
                <div className="text-sm text-gray-600">{topic.count} pages • {Math.round(topic.total_time / 60)} min</div>
              </div>
              <div className="w-48 bg-gray-200 rounded-full h-2">
                <div
                  className="bg-indigo-600 h-2 rounded-full"
                  style={{ width: `${Math.min((topic.total_time / (summary?.learning_time_hours * 3600 || 1)) * 100, 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Dashboard
