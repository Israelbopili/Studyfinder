import React, { useState, useEffect } from 'react';
import api from '../../api';

const CreateGroup = ({ onClose, onGroupCreated }) => {
  const [formData, setFormData] = useState({
    group_name: '',
    description: '',
    privacy_status: 'public',
    max_members: 50,
  });
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get('/courses/').then(res => setCourses(res.data || [])).catch(() => {});
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (formData.group_name.length < 3) {
      alert('Group name must be at least 3 characters');
      return;
    }
    setLoading(true);
    try {
      const response = await api.post('/groups/', formData);
      onGroupCreated();
      onClose();
      window.location.href = `/groups/${response.data.group_id}`;
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to create group');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="create-form" onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Group Name *"
        value={formData.group_name}
        onChange={(e) => setFormData({ ...formData, group_name: e.target.value })}
        required
      />
      <textarea
        placeholder="Description"
        value={formData.description}
        onChange={(e) => setFormData({ ...formData, description: e.target.value })}
      />
      <select
        value={formData.privacy_status}
        onChange={(e) => setFormData({ ...formData, privacy_status: e.target.value })}
      >
        <option value="public">🌐 Public</option>
        <option value="private">🔒 Private (Admin approval required)</option>
      </select>
      <input
        type="number"
        placeholder="Max Members"
        value={formData.max_members}
        onChange={(e) => setFormData({ ...formData, max_members: parseInt(e.target.value) })}
        min="2"
        max="200"
      />
      <button type="submit" disabled={loading}>
        {loading ? 'Creating...' : 'Create Group'}
      </button>
    </form>
  );
};

export default CreateGroup;