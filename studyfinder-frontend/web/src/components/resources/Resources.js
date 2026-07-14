import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../../api';

const Resources = () => {
  const { groupId } = useParams();
  const navigate = useNavigate();
  const [resources, setResources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [file, setFile] = useState(null);

  useEffect(() => {
    fetchResources();
  }, [groupId]);

  const fetchResources = async () => {
    try {
      const response = await api.get(`/resources/group/${groupId}`);
      setResources(response.data || []);
    } catch (error) {
      console.error('Error fetching resources:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      alert('Please select a file');
      return;
    }
    setUploading(true);
    const formData = new FormData();
    formData.append('title', title);
    formData.append('description', description);
    formData.append('file', file);
    
    try {
      await api.post(`/resources/group/${groupId}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      await fetchResources();
      setTitle('');
      setDescription('');
      setFile(null);
      alert('Resource uploaded successfully!');
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to upload');
    } finally {
      setUploading(false);
    }
  };

  const deleteResource = async (resourceId) => {
    if (!confirm('Delete this resource?')) return;
    try {
      await api.delete(`/resources/${resourceId}`);
      await fetchResources();
      alert('Resource deleted');
    } catch (error) {
      alert('Failed to delete resource');
    }
  };

  if (loading) {
    return <div className="loading">Loading resources...</div>;
  }

  return (
    <div>
      <button onClick={() => navigate(-1)} className="back-btn">← Back</button>
      <div className="section-header">
        <h2>📁 Resources</h2>
      </div>

      <form className="upload-form" onSubmit={handleUpload}>
        <input
          type="text"
          placeholder="Title *"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <input
          type="text"
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <input
          type="file"
          onChange={(e) => setFile(e.target.files[0])}
          required
        />
        <button type="submit" disabled={uploading}>
          {uploading ? 'Uploading...' : 'Upload Resource'}
        </button>
      </form>

      {resources.length === 0 ? (
        <div className="empty-state">
          <p>No resources yet. Upload your first one!</p>
        </div>
      ) : (
        <div className="resources-grid">
          {resources.map((resource) => (
            <div key={resource.resource_id} className="resource-card">
              <div className="resource-header">
                <span className="file-icon">📄</span>
                <div>
                  <h4>{resource.title}</h4>
                  <p className="meta">{resource.file_name}</p>
                </div>
              </div>
              {resource.description && <p className="desc">{resource.description}</p>}
              <div className="resource-footer">
                <span>{resource.downloads_count} downloads</span>
                <span>{new Date(resource.created_at).toLocaleDateString()}</span>
                <button className="download-btn">⬇️ Download</button>
                {resource.uploaded_by === localStorage.getItem('user_id') && (
                  <button className="delete-btn" onClick={() => deleteResource(resource.resource_id)}>🗑️</button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Resources;