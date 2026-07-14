import React, { useState, useEffect } from 'react';
import api from '../../api';

const Profile = () => {
  const [user, setUser] = useState(null);
  const [courses, setCourses] = useState([]);
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const [userRes, coursesRes] = await Promise.all([
        api.get('/auth/me'),
        api.get('/students/my-courses')
      ]);
      setUser(userRes.data);
      setFormData(userRes.data);
      setCourses(coursesRes.data || []);
    } catch (error) {
      console.error('Error fetching profile:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    try {
      const response = await api.put('/students/profile', formData);
      setUser(response.data);
      setEditing(false);
      alert('Profile updated successfully!');
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to update profile');
    }
  };

  if (loading) {
    return <div className="loading">Loading profile...</div>;
  }

  return (
    <div className="profile-container">
      <div className="profile-header">
        <div className="profile-avatar">👤</div>
        <h2>{user?.first_name} {user?.last_name}</h2>
        <p className="email">{user?.email}</p>
        <button className="edit-btn" onClick={() => setEditing(!editing)}>
          {editing ? 'Cancel' : '✏️ Edit Profile'}
        </button>
      </div>

      {editing ? (
        <form className="profile-form" onSubmit={handleUpdate}>
          <div className="form-group">
            <label>First Name</label>
            <input
              type="text"
              value={formData.first_name || ''}
              onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label>Last Name</label>
            <input
              type="text"
              value={formData.last_name || ''}
              onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label>Program</label>
            <input
              type="text"
              value={formData.program || ''}
              onChange={(e) => setFormData({ ...formData, program: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label>Year of Study</label>
            <input
              type="number"
              value={formData.year_of_study || ''}
              onChange={(e) => setFormData({ ...formData, year_of_study: parseInt(e.target.value) })}
              min="1"
              max="10"
            />
          </div>
          <div className="form-group">
            <label>Bio</label>
            <textarea
              value={formData.bio || ''}
              onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
            />
          </div>
          <button type="submit">Save Changes</button>
        </form>
      ) : (
        <div className="profile-details">
          <div className="detail-item">
            <span className="label">Program</span>
            <span className="value">{user?.program || 'Not set'}</span>
          </div>
          <div className="detail-item">
            <span className="label">Year of Study</span>
            <span className="value">{user?.year_of_study || 'Not set'}</span>
          </div>
          <div className="detail-item">
            <span className="label">Student Number</span>
            <span className="value">{user?.student_number}</span>
          </div>
          <div className="detail-item">
            <span className="label">Email Verified</span>
            <span className="value">{user?.email_verified ? '✅ Yes' : '❌ No'}</span>
          </div>
        </div>
      )}

      <div className="profile-courses">
        <h3>📚 My Courses</h3>
        {courses.length === 0 ? (
          <p>No courses enrolled yet.</p>
        ) : (
          <div className="courses-list">
            {courses.map((course) => (
              <div key={course.course_id} className="course-item">
                <span className="code">{course.course_code}</span>
                <span className="name">{course.course_name}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Profile;