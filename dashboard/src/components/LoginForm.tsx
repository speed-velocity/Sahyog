import { useState } from 'react';
import { API_BASE_URL } from '../api/config';
import { StatusBadge } from './StatusBadge';

export function LoginForm({ onLoginSuccess }: { onLoginSuccess: () => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const formData = new URLSearchParams();
      formData.set('username', username);
      formData.set('password', password);

      const response = await fetch(`${API_BASE_URL}/auth/token`, {
        method: 'POST',
        body: formData,
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      if (response.ok) {
        const data = await response.json();
        const token = data.access_token;

        if (typeof sessionStorage !== 'undefined') {
          sessionStorage.setItem('sahyog_token', token);
        }
        onLoginSuccess();
      } else {
        const errData = await response.json().catch(() => ({}));
        setError(errData.detail || 'Login failed. Please check your credentials.');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-form">
      <h2>Caregiver Login</h2>

      {error && (
        <div className="login-form__error">
          <StatusBadge label={error} tone="danger" />
        </div>
      )}

      <form onSubmit={handleSubmit} className="login-form__form">
        <div className="login-form__group">
          <label htmlFor="username">Username</label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            disabled={loading}
            aria-label="Username"
          />
        </div>

        <div className="login-form__group">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            disabled={loading}
            aria-label="Password"
          />
        </div>

        <div className="login-form__actions">
          <button type="submit" disabled={loading} className="btn btn--primary">
            {loading ? 'Logging in...' : 'Sign In'}
          </button>
        </div>
      </form>
    </div>
  );
}
