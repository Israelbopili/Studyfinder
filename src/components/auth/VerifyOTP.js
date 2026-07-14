import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import api from '../../api';

const VerifyOTP = () => {
  const [otp, setOtp] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [attempts, setAttempts] = useState(3);
  const [timer, setTimer] = useState(0);
  const [registrationData, setRegistrationData] = useState(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // Get registration data from localStorage (saved during registration)
    const savedData = localStorage.getItem('pending_registration');
    if (savedData) {
      try {
        const parsed = JSON.parse(savedData);
        setRegistrationData(parsed);
        setEmail(parsed.email);
      } catch (e) {
        console.error('Invalid registration data');
      }
    }

    // Or get email from URL
    const params = new URLSearchParams(location.search);
    const emailParam = params.get('email');
    if (emailParam) {
      setEmail(emailParam);
    }
  }, [location]);

  // Countdown timer for resend
  useEffect(() => {
    if (timer > 0) {
      const interval = setInterval(() => {
        setTimer(prev => prev - 1);
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [timer]);

  const handleVerify = async (e) => {
    e.preventDefault();
    if (!otp || otp.length !== 6) {
      setError('Please enter a valid 6-digit OTP code');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      // ─── Step 1: Verify OTP ──────────────────────────────────────────
      await api.post('/auth/verify-otp', {
        email,
        otp_code: otp
      });

      // ─── Step 2: Create Account (after OTP verified) ────────────────
      if (registrationData) {
        const registerResponse = await api.post('/auth/register', registrationData);
        setSuccess('Email verified and account created successfully!');
      } else {
        setSuccess('Email verified successfully! Please login.');
      }

      setAttempts(3);
      localStorage.removeItem('pending_registration');
      
      // Redirect to login after 2 seconds
      setTimeout(() => {
        navigate('/login');
      }, 2000);

    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Verification failed';
      setError(errorMsg);
      
      if (errorMsg.includes('attempts remaining')) {
        const match = errorMsg.match(/(\d+) attempts? remaining/);
        if (match) {
          setAttempts(parseInt(match[1]));
        }
      }
      if (errorMsg.includes('expired')) {
        setTimer(60);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleResendOTP = async () => {
    setLoading(true);
    setError('');
    setSuccess('');
    try {
      await api.post('/auth/resend-otp', { email });
      setSuccess('New OTP sent to your email!');
      setTimer(60);
      setAttempts(3);
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to resend OTP');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1>📚 Studyfinder</h1>
        <h2>Verify Your Email</h2>
        <p style={{ color: '#666', marginBottom: '20px' }}>
          Enter the 6-digit code sent to <strong>{email}</strong>
        </p>

        {error && <div className="error">{error}</div>}
        {success && <div className="success">{success}</div>}

        <form onSubmit={handleVerify}>
          <div style={{ textAlign: 'center', marginBottom: '20px' }}>
            <input
              type="text"
              placeholder="Enter 6-digit OTP"
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
              maxLength="6"
              style={{
                width: '100%',
                padding: '16px',
                fontSize: '24px',
                textAlign: 'center',
                letterSpacing: '12px',
                border: '2px solid #ddd',
                borderRadius: '8px',
                fontFamily: 'monospace',
                fontWeight: 'bold'
              }}
              autoFocus
              required
            />
            <div style={{ marginTop: '8px', fontSize: '14px', color: '#888' }}>
              {attempts > 0 ? `${attempts} attempts remaining` : 'No attempts left'}
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || attempts === 0}
            style={{
              width: '100%',
              padding: '12px',
              background: '#1A3A6B',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '16px',
              fontWeight: 'bold',
              cursor: loading || attempts === 0 ? 'not-allowed' : 'pointer',
              opacity: loading || attempts === 0 ? 0.6 : 1
            }}
          >
            {loading ? 'Verifying...' : 'Verify & Create Account'}
          </button>
        </form>

        <div style={{ marginTop: '20px', textAlign: 'center' }}>
          <button
            onClick={handleResendOTP}
            disabled={loading || timer > 0}
            style={{
              background: 'none',
              border: 'none',
              color: '#1A3A6B',
              cursor: loading || timer > 0 ? 'not-allowed' : 'pointer',
              opacity: loading || timer > 0 ? 0.6 : 1,
              fontSize: '14px',
              textDecoration: 'underline'
            }}
          >
            {timer > 0 ? `Resend available in ${timer}s` : 'Resend OTP'}
          </button>
        </div>

        <div style={{ marginTop: '15px', textAlign: 'center' }}>
          <Link to="/login" style={{ color: '#1A3A6B', fontSize: '14px' }}>
            Back to Login
          </Link>
        </div>
      </div>
    </div>
  );
};

export default VerifyOTP;