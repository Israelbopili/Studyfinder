import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../api';
import CreateGroup from './CreateGroup';

const Groups = () => {
  const [groups, setGroups] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(true);
  const [joining, setJoining] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchGroups();
  }, []);

  const fetchGroups = async () => {
    try {
      const response = await api.get('/groups/');
      setGroups(response.data || []);
    } catch (error) {
      console.error('Error fetching groups:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleJoin = async (groupId, e) => {
    e.stopPropagation();
    setJoining(groupId);
    try {
      await api.post(`/groups/${groupId}/join`);
      await fetchGroups();
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to join group');
    } finally {
      setJoining(null);
    }
  };

  const togglePriority = async (groupId, e) => {
    e.stopPropagation();
    try {
      const response = await api.put(`/groups/${groupId}/priority`);
      setGroups(groups.map(g => 
        g.group_id === groupId 
          ? { ...g, is_priority: response.data.is_priority }
          : g
      ));
    } catch (error) {
      alert('Failed to toggle priority');
    }
  };

  const handleGroupClick = (groupId) => {
    navigate(`/groups/${groupId}`);
  };

  if (loading) {
    return <div className="loading">Loading groups...</div>;
  }

  return (
    <div>
      <div className="section-header">
        <h2>Study Groups</h2>
        <button onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? 'Cancel' : '+ Create Group'}
        </button>
      </div>

      {showCreate && <CreateGroup onClose={() => setShowCreate(false)} onGroupCreated={fetchGroups} />}

      {groups.length === 0 ? (
        <div className="empty-state">
          <p>No groups available. Create your first study group!</p>
        </div>
      ) : (
        <div className="groups-grid">
          {/* Priority groups first */}
          {groups.filter(g => g.is_priority).map((group) => (
            <GroupCard 
              key={group.group_id}
              group={group}
              onJoin={handleJoin}
              onPriority={togglePriority}
              onClick={handleGroupClick}
              joining={joining}
            />
          ))}
          {groups.filter(g => !g.is_priority).map((group) => (
            <GroupCard 
              key={group.group_id}
              group={group}
              onJoin={handleJoin}
              onPriority={togglePriority}
              onClick={handleGroupClick}
              joining={joining}
            />
          ))}
        </div>
      )}
    </div>
  );
};

const GroupCard = ({ group, onJoin, onPriority, onClick, joining }) => {
  const isPrivate = group.privacy_status === 'private';
  const isPending = group.is_pending || false;
  const isMember = group.is_member || false;

  return (
    <div 
      className={`group-card clickable ${group.is_priority ? 'priority-group' : ''}`}
      onClick={() => onClick(group.group_id)}
    >
      <div className="group-header-row">
        <h4>{group.group_name}</h4>
        {group.unread_count > 0 && (
          <span className="unread-badge">{group.unread_count}</span>
        )}
      </div>
      <p className="group-desc">{group.description || 'No description'}</p>
      <div className="group-actions">
        <span className="meta">{group.member_count} members</span>
        <span className={`badge ${isPrivate ? 'private' : 'public'}`}>
          {isPrivate ? '🔒 Private' : '🌐 Public'}
        </span>
        {isMember ? (
          <>
            <button 
              className={`priority-btn ${group.is_priority ? 'active' : ''}`}
              onClick={(e) => onPriority(group.group_id, e)}
              title={group.is_priority ? 'Priority group' : 'Set as priority'}
            >
              ⭐
            </button>
            <span className="joined-badge">✅ Joined</span>
          </>
        ) : isPending ? (
          <span className="pending-badge">⏳ Pending Approval</span>
        ) : isPrivate ? (
          <button 
            onClick={(e) => onJoin(group.group_id, e)}
            disabled={joining === group.group_id}
            className="join-btn private"
          >
            {joining === group.group_id ? 'Requesting...' : 'Request to Join'}
          </button>
        ) : (
          <button 
            onClick={(e) => onJoin(group.group_id, e)}
            disabled={joining === group.group_id}
            className="join-btn"
          >
            {joining === group.group_id ? 'Joining...' : 'Join'}
          </button>
        )}
      </div>
    </div>
  );
};

export default Groups;