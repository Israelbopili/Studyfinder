import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../api';

const Sessions = () => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      // Get user's groups first
      const groupsRes = await api.get('/groups/');
      const myGroups = groupsRes.data.filter(g => g.is_member);
      
      // Fetch sessions for each group
      const sessionsData = await Promise.all(
        myGroups.map(async (group) => {
          try {
            const res = await api.get(`/sessions/group/${group.group_id}`);
            return res.data.map(s => ({ ...s, group_name: group.group_name }));
          } catch { return []; }
        })
      );
      const allSessions = sessionsData.flat();
      setSessions(allSessions);
    } catch (error) {
      console.error('Error fetching sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  const cancelSession = async (sessionId) => {
    if (!confirm('Cancel this session?')) return;
    try {
      await api.delete(`/sessions/${sessionId}`);
      await fetchSessions();
      alert('Session cancelled');
    } catch (error) {
      alert('Failed to cancel session');
    }
  };

  if (loading) {
    return <div className="loading">Loading sessions...</div>;
  }

  return (
    <div>
      <div className="section-header">
        <h2>📅 Study Sessions</h2>
        <button onClick={() => navigate('/groups')}>Schedule from Group</button>
      </div>

      {sessions.length === 0 ? (
        <div className="empty-state">
          <p>No sessions scheduled. Join a group and schedule one!</p>
        </div>
      ) : (
        <div className="sessions-grid">
          {sessions.map((session) => (
            <div key={session.session_id} className="session-card">
              <h3>{session.title}</h3>
              <p className="group-name">📖 {session.group_name}</p>
              <p className="location">📍 {session.location || session.meeting_link || 'No location'}</p>
              <p className="datetime">🕐 {new Date(session.start_time).toLocaleString()}</p>
              <p className="status">Status: {session.status}</p>
              {session.created_by === localStorage.getItem('user_id') && (
                <button className="cancel-btn" onClick={() => cancelSession(session.session_id)}>
                  Cancel
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Sessions;