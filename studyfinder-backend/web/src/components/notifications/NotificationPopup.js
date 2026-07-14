import React, { useState, useEffect } from 'react';
import './NotificationPopup.css';

const NotificationPopup = ({ message, onClose, priority }) => {
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose();
    }, 5000);
    return () => clearTimeout(timer);
  }, [onClose]);

  if (!message) return null;

  return (
    <div className={`notification-popup ${priority ? 'priority' : ''}`}>
      <div className="notification-content">
        <span className="notification-icon">💬</span>
        <div className="notification-text">
          <strong>{message.sender_name || 'Unknown'}</strong>
          <p>{message.content || 'New message'}</p>
          <small>{new Date(message.sent_at).toLocaleTimeString()}</small>
        </div>
        <button onClick={onClose} className="notification-close">×</button>
      </div>
    </div>
  );
};

export default NotificationPopup;