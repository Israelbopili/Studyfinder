import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../../api';

const Register = () => {
  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    student_number: '',
    program: '',
    year_of_study: 1,
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess('');

    // Validate password
    if (formData.password.length < 4) {
      setError('Password must be at least 4 characters');
      setLoading(false);
      return;
    }

    try {
      // ─── Step 1: Send OTP (no account created yet) ────────────────────
      const response = await api.post('/auth/send-otp', {
        email: formData.email,
        first_name: formData.first_name,
        last_name: formData.last_name
      });
      
      setSuccess('OTP sent to your email! Please check your inbox.');
      
      // ─── Save registration data for later ──────────────────────────────
      localStorage.setItem('pending_registration', JSON.stringify(formData));
      
      // ─── Redirect to OTP verification page ─────────────────────────────
      setTimeout(() => {
        navigate(`/verify-otp?email=${encodeURIComponent(formData.email)}`);
      }, 2000);
      
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to send OTP');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1>📚 Studyfinder</h1>
        <h2>Create Account</h2>
        {error && <div className="error">{error}</div>}
        {success && <div className="success">{success}</div>}
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            name="first_name"
            placeholder="First Name *"
            value={formData.first_name}
            onChange={handleChange}
            required
          />
          <input
            type="text"
            name="last_name"
            placeholder="Last Name *"
            value={formData.last_name}
            onChange={handleChange}
            required
          />
          <input
            type="email"
            name="email"
            placeholder="Email *"
            value={formData.email}
            onChange={handleChange}
            required
          />
          <input
            type="text"
            name="student_number"
            placeholder="Student Number *"
            value={formData.student_number}
            onChange={handleChange}
            required
          />
          <input
            type="text"
            name="program"
            placeholder="Program (e.g., ICT)"
            value={formData.program}
            onChange={handleChange}
          />
          <input
            type="number"
            name="year_of_study"
            placeholder="Year of Study"
            value={formData.year_of_study}
            onChange={handleChange}
            min="1"
            max="10"
          />
          <input
            type="password"
            name="password"
            placeholder="Password (min 4 chars) *"
            value={formData.password}
            onChange={handleChange}
            required
          />
          <button type="submit" disabled={loading}>
            {loading ? 'Sending OTP...' : 'Register'}
          </button>
        </form>
        <p>
          Already have an account? <Link to="/login">Login</Link>
        </p>
      </div>
    </div>
  );
};

export default Register;