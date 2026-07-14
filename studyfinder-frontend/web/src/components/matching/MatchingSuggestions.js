import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../api';

const MatchingSuggestions = () => {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchSuggestions();
  }, []);

  const fetchSuggestions = async () => {
    try {
      const response = await api.get('/matching/suggestions');
      setSuggestions(response.data || []);
    } catch (error) {
      console.error('Error fetching suggestions:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">Finding suggestions...</div>;
  }

  return (
    <div>
      <div className="section-header">
        <h2>🎯 Smart Suggestions</h2>
        <span className="suggestion-count">{suggestions.length} recommendations</span>
      </div>

      {suggestions.length === 0 ? (
        <div className="empty-state">
          <p>No suggestions yet. Enroll in courses to get personalized recommendations!</p>
        </div>
      ) : (
        <div className="suggestions-grid">
          {suggestions.map((group) => (
            <div 
              key={group.group_id} 
              className="suggestion-card"
              onClick={() => navigate(`/groups/${group.group_id}`)}
            >
              <div className="score-badge">{group.match_score}% match</div>
              <h3>{group.group_name}</h3>
              <p className="desc">{group.description || 'No description'}</p>
              <div className="suggestion-meta">
                <span>👥 {group.member_count} members</span>
                <span>{group.course_code || 'No course'}</span>
              </div>
              <div className="reasons">
                {group.reasons?.map((reason, i) => (
                  <span key={i} className="reason-tag">{reason}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default MatchingSuggestions;