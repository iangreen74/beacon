/**
 * Main dashboard component for mood pulse visualization.
 * Displays sentiment trends, team overview, and real-time updates.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const API_BASE = window.__DASHBOARD_CONFIG__?.apiBaseUrl || '/api/v1';
const REFRESH_INTERVAL = window.__DASHBOARD_CONFIG__?.refreshInterval || 30;
const SENTIMENT_COLORS = window.__DASHBOARD_CONFIG__?.sentimentColors || {
  positive: '#10b981',
  neutral: '#6b7280',
  negative: '#ef4444'
};

const Dashboard = ({ teamId = null }) => {
  const [pulses, setPulses] = useState([]);
  const [trends, setTrends] = useState(null);
  const [teams, setTeams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      
      // Fetch pulses
      const pulsesUrl = teamId ? `${API_BASE}/pulses/?team_id=${teamId}` : `${API_BASE}/pulses/`;
      const pulsesRes = await fetch(pulsesUrl, { credentials: 'include' });
      const pulsesData = await pulsesRes.json();
      setPulses(pulsesData);

      // Fetch trends
      const trendsUrl = teamId ? `${API_BASE}/analytics/trends?team_id=${teamId}` : `${API_BASE}/analytics/trends`;
      const trendsRes = await fetch(trendsUrl, { credentials: 'include' });
      const trendsData = await trendsRes.json();
      setTrends(trendsData);

      // Fetch teams if not team-specific
      if (!teamId) {
        const teamsRes = await fetch(`${API_BASE}/teams/`, { credentials: 'include' });
        const teamsData = await teamsRes.json();
        setTeams(teamsData);
      }

      setError(null);
    } catch (err) {
      setError('Failed to load dashboard data');
      console.error('Dashboard error:', err);
    } finally {
      setLoading(false);
    }
  }, [teamId]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, REFRESH_INTERVAL * 1000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const sentimentData = pulses.reduce((acc, pulse) => {
    const date = new Date(pulse.submitted_at).toLocaleDateString();
    if (!acc[date]) acc[date] = { date, positive: 0, neutral: 0, negative: 0 };
    acc[date][pulse.sentiment] = (acc[date][pulse.sentiment] || 0) + 1;
    return acc;
  }, {});

  const chartData = Object.values(sentimentData).slice(-14);

  if (loading && pulses.length === 0) {
    return <div className="flex justify-center items-center h-64">Loading dashboard...</div>;
  }

  if (error) {
    return <div className="bg-red-50 p-4 rounded text-red-800">{error}</div>;
  }

  return (
    <div className="dashboard p-6 space-y-6">
      <header className="border-b pb-4">
        <h1 className="text-3xl font-bold">Team Mood Dashboard</h1>
        {teamId && <p className="text-gray-600">Team View</p>}
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard title="Total Pulses" value={pulses.length} color="blue" />
        <StatCard title="Avg Sentiment" value={trends?.average_sentiment || 'N/A'} color="green" />
        <StatCard title="Trend" value={trends?.trend_direction || 'stable'} color="purple" />
      </div>

      <div className="bg-white p-6 rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Sentiment Trends (Last 14 Days)</h2>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="positive" stroke={SENTIMENT_COLORS.positive} />
            <Line type="monotone" dataKey="neutral" stroke={SENTIMENT_COLORS.neutral} />
            <Line type="monotone" dataKey="negative" stroke={SENTIMENT_COLORS.negative} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <PulseHistory pulses={pulses.slice(0, 10)} />
    </div>
  );
};

const StatCard = ({ title, value, color }) => (
  <div className={`bg-${color}-50 p-4 rounded-lg`}>
    <h3 className="text-sm text-gray-600">{title}</h3>
    <p className="text-2xl font-bold mt-1">{value}</p>
  </div>
);

const PulseHistory = ({ pulses }) => (
  <div className="bg-white p-6 rounded-lg shadow">
    <h2 className="text-xl font-semibold mb-4">Recent Pulses</h2>
    <div className="space-y-2">
      {pulses.map(pulse => (
        <div key={pulse.id} className="border-l-4 border-gray-300 pl-4 py-2">
          <span className={`font-semibold text-${pulse.sentiment === 'positive' ? 'green' : pulse.sentiment === 'negative' ? 'red' : 'gray'}-600`}>
            {pulse.sentiment}
          </span>
          <span className="text-gray-500 ml-4 text-sm">{new Date(pulse.submitted_at).toLocaleString()}</span>
        </div>
      ))}
    </div>
  </div>
);

export default Dashboard;
