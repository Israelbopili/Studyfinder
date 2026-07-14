import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../../api';
import './NotificationBell.css';

const NotificationBell = () => {
  const [unreadCount, setUnreadCount] = useState(0);
  const [showDropdown, setShowDropdown] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchUnreadCount = async () => {
    try {
      const response = await api.get('/chat/unread');
      const total = response.data.reduce((sum, g) => sum + g.unread_count, 0);
      setUnreadCount(total);
      setNotifications(response.data);
    } catch (error) {
      console.error('Error fetching unread count:', error);
    }
  };

  const handleBellClick = () => {
    setShowDropdown(!showDropdown);
    if (!showDropdown) {
      fetchUnreadCount();
    }
  };

  const handleNotificationClick = (groupId) => {
    setShowDropdown(false);
    navigate(`/groups/${groupId}`);
  };

  const markAllAsRead = async () => {
    try {
      for (const notif of notifications) {
        await api.post(`/chat/${notif.group_id}/read`);
      }
      setUnreadCount(0);
      setNotifications([]);
      fetchUnreadCount();
    } catch (error) {
      console.error('Error marking all as read:', error);
    }
  };

  return (
    <div className="notification-bell-container">
      <button className="notification-bell" onClick={handleBellClick}>
        🔔
        {unreadCount > 0 && (
          <span className="notification-badge">{unreadCount}</span>
        )}
      </button>

      {showDropdown && (
        <div className="notification-dropdown">
          <div className="notification-header">
            <span>Notifications</span>
            {unreadCount > 0 && (
              <button className="mark-all-read" onClick={markAllAsRead}>
                Mark all read
              </button>
            )}
          </div>
          <div className="notification-list">
            {notifications.length === 0 ? (
              <div className="notification-empty">No new notifications</div>
            ) : (
              notifications.map((notif) => (
                <div
                  key={notif.group_id}
                  className={`notification-item ${notif.is_priority ? 'priority' : ''}`}
                  onClick={() => handleNotificationClick(notif.group_id)}
                >
                  <span className="notification-icon">
                    {notif.is_priority ? '⭐' : '💬'}
                  </span>
                  <div className="notification-content">
                    <span className="notification-text">
                      {notif.unread_count} new message{notif.unread_count > 1 ? 's' : ''}
                    </span>
                    <span className="notification-group">Group</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationBell;