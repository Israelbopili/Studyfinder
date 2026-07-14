import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import NotificationBell from '../notifications/NotificationBell';

const Navbar = () => {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login';
  };

  return (
    <nav className="navbar">
      <div className="nav-container">
        <div className="nav-brand">
          <Link to="/">📚 Studyfinder</Link>
        </div>
        <div className="nav-links">
          <Link to="/">Dashboard</Link>
          <Link to="/groups">Groups</Link>
          <Link to="/courses">Courses</Link>
          <Link to="/matching">Suggestions</Link>
          <NotificationBell />
          <button onClick={handleLogout} className="logout-btn">Logout</button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;