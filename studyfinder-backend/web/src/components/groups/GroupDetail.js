import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../../api';
import NotificationPopup from '../notifications/NotificationPopup';

const GroupDetail = () => {
  const { groupId } = useParams();
  const navigate = useNavigate();
  const [group, setGroup] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [activeTab, setActiveTab] = useState('chat');
  const [notification, setNotification] = useState(null);
  const [pendingRequests, setPendingRequests] = useState([]);
  const [ws, setWs] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    fetchGroupData();
    connectWebSocket();
    return () => { if (ws) ws.close(); };
  }, [groupId]);

  const fetchGroupData = async () => {
    try {
      const [groupRes, messagesRes] = await Promise.all([
        api.get(`/groups/${groupId}`),
        api.get(`/chat/${groupId}/history`).catch(() => ({ data: [] }))
      ]);
      setGroup(groupRes.data);
      setMessages(messagesRes.data || []);
      
      // Mark as read
      await api.post(`/chat/${groupId}/read`);
      
      // Get pending requests if admin
      if (groupRes.data.is_admin) {
        try {
          const pendingRes = await api.get(`/groups/${groupId}/pending-requests`);
          setPendingRequests(pendingRes.data || []);
        } catch {}
      }
    } catch (error) {
      console.error('Error fetching group:', error);
      if (error.response?.status === 403) {
        alert(error.response?.data?.detail || 'You do not have access to this group');
        navigate('/groups');
      }
    } finally {
      setLoading(false);
    }
  };

  const connectWebSocket = () => {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    const wsUrl = `ws://localhost:8000/api/v1/chat/${groupId}?token=${token}`;
    const socket = new WebSocket(wsUrl);
    
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'message') {
        setMessages(prev => [...prev, data]);
        scrollToBottom();
        if (data.sender_id !== group?.creator_id) {
          setNotification({
            sender_name: data.sender_name,
            content: data.content,
            sent_at: data.sent_at
          });
          setTimeout(() => setNotification(null), 5000);
        }
      }
    };

    socket.onclose = () => {
      console.log('WebSocket disconnected, reconnecting...');
      setTimeout(connectWebSocket, 3000);
    };

    setWs(socket);
  };

  const scrollToBottom = () => {
    setTimeout(() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
  };

  const sendMessage = async () => {
    if (!newMessage.trim()) return;
    setSending(true);
    try {
      await api.post('/chat/messages', {
        group_id: groupId,
        content: newMessage.trim(),
        message_type: 'text'
      });
      setNewMessage('');
    } catch (error) {
      alert('Failed to send message');
    } finally {
      setSending(false);
    }
  };

  const togglePriority = async () => {
    try {
      const response = await api.put(`/groups/${groupId}/priority`);
      setGroup({ ...group, is_priority: response.data.is_priority });
    } catch (error) {
      alert('Failed to toggle priority');
    }
  };

  const approveMember = async (studentId) => {
    try {
      await api.post(`/groups/${groupId}/approve/${studentId}`);
      setPendingRequests(pendingRequests.filter(r => r.student_id !== studentId));
      fetchGroupData();
      alert('Member approved successfully!');
    } catch (error) {
      alert('Failed to approve member');
    }
  };

  const rejectMember = async (studentId) => {
    try {
      await api.post(`/groups/${groupId}/reject/${studentId}`);
      setPendingRequests(pendingRequests.filter(r => r.student_id !== studentId));
      alert('Request rejected');
    } catch (error) {
      alert('Failed to reject request');
    }
  };

  const leaveGroup = async () => {
    if (!confirm('Are you sure you want to leave this group?')) return;
    try {
      await api.post(`/groups/${groupId}/leave`);
      navigate('/groups');
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to leave group');
    }
  };

  if (loading) {
    return <div className="loading">Loading group...</div>;
  }

  if (!group) {
    return <div className="loading">Group not found</div>;
  }

  return (
    <div className="group-detail">
      {notification && (
        <NotificationPopup 
          message={notification}
          onClose={() => setNotification(null)}
          priority={group.is_priority}
        />
      )}

      <div className="group-header">
        <button onClick={() => navigate('/groups')} className="back-btn">← Back to Groups</button>
        <div className="group-header-info">
          <div className="group-title-row">
            <h2>{group.group_name}</h2>
            {group.is_member && (
              <button 
                className={`priority-btn ${group.is_priority ? 'active' : ''}`}
                onClick={togglePriority}
                title={group.is_priority ? 'Priority group' : 'Set as priority'}
              >
                ⭐
              </button>
            )}
            {group.unread_count > 0 && (
              <span className="unread-badge">{group.unread_count} new</span>
            )}
          </div>
          <p className="group-meta">
            {group.member_count} members · 
            {group.privacy_status === 'private' ? ' 🔒 Private' : ' 🌐 Public'}
            {group.is_priority && <span className="priority-label"> · ⭐ Priority</span>}
          </p>
          {group.description && <p className="group-desc">{group.description}</p>}
        </div>
      </div>

      <div className="group-tabs">
        <button 
          className={activeTab === 'chat' ? 'tab-active' : 'tab'}
          onClick={() => setActiveTab('chat')}
        >
          💬 Chat {group.unread_count > 0 && <span className="tab-badge">{group.unread_count}</span>}
        </button>
        <button 
          className={activeTab === 'members' ? 'tab-active' : 'tab'}
          onClick={() => setActiveTab('members')}
        >
          👥 Members ({group.member_count})
        </button>
        {group.is_admin && (
          <button 
            className={activeTab === 'requests' ? 'tab-active' : 'tab'}
            onClick={() => setActiveTab('requests')}
          >
            📋 Requests {pendingRequests.length > 0 && <span className="tab-badge">{pendingRequests.length}</span>}
          </button>
        )}
        {group.is_member && (
          <button className="leave-btn" onClick={leaveGroup}>
            Leave Group
          </button>
        )}
      </div>

      {/* Chat Tab */}
      {activeTab === 'chat' && (
        <div className="chat-section">
          {!group.is_member ? (
            <div className="join-prompt">
              <p>
                {group.privacy_status === 'private' 
                  ? 'This is a private group. Request to join from group admin.' 
                  : 'You need to join this group to participate.'}
              </p>
              {!group.is_pending && (
                <button onClick={() => window.location.reload()}>Request to Join</button>
              )}
            </div>
          ) : (
            <>
              <div className="messages-container">
                {messages.length === 0 ? (
                  <p className="no-messages">No messages yet. Start the conversation!</p>
                ) : (
                  messages.map((msg) => (
                    <div key={msg.message_id} className="message">
                      <strong>{msg.sender_name || 'Unknown'}:</strong>
                      <span>{msg.content}</span>
                      <small>{new Date(msg.sent_at).toLocaleTimeString()}</small>
                    </div>
                  ))
                )}
                <div ref={messagesEndRef} />
              </div>
              <div className="message-input">
                <input
                  type="text"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  placeholder="Type a message..."
                  onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                />
                <button onClick={sendMessage} disabled={sending}>
                  {sending ? 'Sending...' : 'Send'}
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Members Tab */}
      {activeTab === 'members' && (
        <div className="members-section">
          <h3>Members ({group.member_count})</h3>
          <div className="members-list">
            {group.members?.map((member) => (
              <div key={member.student_id} className="member-item">
                <span className="member-name">
                  {member.first_name} {member.last_name}
                </span>
                <span className="member-role">{member.role}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pending Requests Tab (Admin only) */}
      {activeTab === 'requests' && group.is_admin && (
        <div className="requests-section">
          <h3>Pending Join Requests</h3>
          {pendingRequests.length === 0 ? (
            <p className="no-requests">No pending requests.</p>
          ) : (
            pendingRequests.map((req) => (
              <div key={req.student_id} className="request-item">
                <span>{req.first_name} {req.last_name}</span>
                <span className="request-email">{req.email}</span>
                <span className="request-date">{new Date(req.requested_at).toLocaleDateString()}</span>
                <div className="request-actions">
                  <button className="approve-btn" onClick={() => approveMember(req.student_id)}>✅ Approve</button>
                  <button className="reject-btn" onClick={() => rejectMember(req.student_id)}>❌ Reject</button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default GroupDetail;