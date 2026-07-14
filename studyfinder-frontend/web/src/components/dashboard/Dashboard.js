import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../api';

const Dashboard = () => {
  const [user, setUser] = useState(null);
  const [myGroups, setMyGroups] = useState([]);
  const [upcomingSessions, setUpcomingSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [userRes, groupsRes] = await Promise.all([
          api.get('/auth/me'),
          api.get('/groups/'),
        ]);
        setUser(userRes.data);
        const joined = groupsRes.data.filter(g => g.is_member);
        setMyGroups(joined);
        
        // Fetch sessions for joined groups
        const sessionsData = await Promise.all(
          joined.map(async (group) => {
            try {
              const res = await api.get(`/sessions/group/${group.group_id}`);
              return res.data.map(s => ({ ...s, group_name: group.group_name }));
            } catch { return []; }
          })
        );
        const allSessions = sessionsData.flat();
        const now = new Date();
        const upcoming = allSessions
          .filter(s => new Date(s.start_time) > now && s.status !== 'cancelled')
          .sort((a, b) => new Date(a.start_time) - new Date(b.start_time))
          .slice(0, 5);
        setUpcomingSessions(upcoming);
      } catch (error) {
        console.error('Error fetching data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <div>
      <div className="welcome">
        <h2>Welcome, {user?.first_name} {user?.last_name}! 👋</h2>
        <p>Email: {user?.email}</p>
        <p>Program: {user?.program || 'Not set'} • Year {user?.year_of_study || 'N/A'}</p>
      </div>

      <div className="dashboard-grid">
        {/* Upcoming Sessions */}
        <div className="section">
          <div className="section-header">
            <h3>📅 Upcoming Sessions</h3>
            <button onClick={() => navigate('/sessions')}>View All</button>
          </div>
          {upcomingSessions.length === 0 ? (
            <div className="empty-state">
              <p>No upcoming sessions. Schedule one from a group.</p>
            </div>
          ) : (
            upcomingSessions.map((session) => (
              <div key={session.session_id} className="session-card">
                <h4>{session.group_name}</h4>
                <p>📍 {session.location || session.meeting_link || 'No location'}</p>
                <p className="meta">🕐 {new Date(session.start_time).toLocaleString()}</p>
              </div>
            ))
          )}
        </div>

        {/* My Groups */}
        <div className="section">
          <div className="section-header">
            <h3>👥 My Study Groups</h3>
            <button onClick={() => navigate('/groups')}>View All</button>
          </div>
          {myGroups.length === 0 ? (
            <div className="empty-state">
              <p>You haven't joined any groups yet.</p>
              <button onClick={() => navigate('/groups')}>Find Groups</button>
            </div>
          ) : (
            myGroups.map((group) => (
              <div 
                key={group.group_id} 
                className={`group-card ${group.is_priority ? 'priority' : ''}`}
                onClick={() => navigate(`/groups/${group.group_id}`)}
              >
                <h4>{group.group_name}</h4>
                <p className="meta">{group.member_count} members</p>
                {group.unread_count > 0 && (
                  <span className="unread-badge">{group.unread_count} new</span>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;