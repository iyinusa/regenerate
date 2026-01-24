import React, { useState, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { apiClient } from '@/lib/api';

const ProfileTab: React.FC = () => {
  const { user, refreshAuthStatus } = useAuth();
  
  const [profileForm, setProfileForm] = useState({
    full_name: '',
    email: ''
  });
  
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  
  const [isProfileLoading, setIsProfileLoading] = useState(false);
  const [isPasswordLoading, setIsPasswordLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
  const [githubUrl, setGithubUrl] = useState('');
  const [linkedinUrl, setLinkedinUrl] = useState('');
  
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  useEffect(() => {
    if (user) {
      setProfileForm({
        full_name: user.full_name || '',
        email: user.email || ''
      });
    }
  }, [user]);

  useEffect(() => {
    // Determine Auth URLs (mostly for display/action, similar to Login modal)
    // Actually we will call API to get the auth URL when button is clicked
    // But for simplicity in this tab we might just redirect directly on click
    const loadAuthUrls = async () => {
        try {
            const gh = await apiClient.githubOAuth();
            if (gh && gh.redirect_url) setGithubUrl(gh.redirect_url);
            
            const li = await apiClient.linkedinOAuth();
            if (li && li.redirect_url) setLinkedinUrl(li.redirect_url);
        } catch (e) {
            console.error("Failed to load OAuth URLs", e);
        }
    };
    loadAuthUrls();
  }, []);

  const handleProfileUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsProfileLoading(true);
    setMessage(null);
    try {
      await apiClient.updateProfile({
        full_name: profileForm.full_name,
        email: profileForm.email
      });
      await refreshAuthStatus();
      setMessage({ type: 'success', text: 'Profile updated successfully' });
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || 'Failed to update profile' });
    } finally {
      setIsProfileLoading(false);
    }
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setMessage({ type: 'error', text: 'New passwords do not match' });
      return;
    }
    
    setIsPasswordLoading(true);
    setMessage(null);
    try {
      await apiClient.changePassword({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password
      });
      setPasswordForm({ current_password: '', new_password: '', confirm_password: '' });
      setMessage({ type: 'success', text: 'Password changed successfully' });
    } catch (error: any) {
      setMessage({ type: 'error', text: error.message || 'Failed to change password' });
    } finally {
      setIsPasswordLoading(false);
    }
  };

  const handleConnect = (url: string) => {
    if (!url) return;
    window.location.href = url;
  };

  if (!user) return <div>Please log in to view profile.</div>;

  return (
    <div className="profile-tab-content">
      {message && (
        <div style={{ 
          padding: '12px', 
          borderRadius: '8px', 
          marginBottom: '20px', 
          background: message.type === 'success' ? 'rgba(76, 175, 80, 0.1)' : 'rgba(255, 77, 77, 0.1)',
          color: message.type === 'success' ? '#81c784' : '#ff8a80',
          border: `1px solid ${message.type === 'success' ? 'rgba(76, 175, 80, 0.3)' : 'rgba(255, 77, 77, 0.3)'}`
        }}>
          {message.text}
        </div>
      )}

      {/* Profile Details */}
      <div className="profile-section">
        <div className="profile-section-title">Personal Details</div>
        <form onSubmit={handleProfileUpdate}>
          <div className="form-group">
            <label className="form-label">Full Name</label>
            <input 
              type="text" 
              className="form-input" 
              value={profileForm.full_name}
              onChange={(e) => setProfileForm({...profileForm, full_name: e.target.value})}
              placeholder="Enter your full name"
            />
          </div>
          <div className="form-group">
            <label className="form-label">Email</label>
            <input 
              type="email" 
              className="form-input" 
              value={profileForm.email}
              onChange={(e) => setProfileForm({...profileForm, email: e.target.value})}
              placeholder="Enter your email"
              disabled // Usually email change requires verification, let's keep it disabled or editable if backend supports
            />
            {/* Note: Backend supports email update but we might want to be careful. Leaving it enabled as per requirement 'edit profile details (Full Name, Email)' */}
          </div>
          <div className="form-actions">
            <button type="submit" className="btn-primary" disabled={isProfileLoading}>
              {isProfileLoading ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>

      {/* Linked Accounts */}
      <div className="profile-section">
        <div className="profile-section-title">Linked Accounts</div>
        
        {/* GitHub */}
        <div className={`connection-item ${user.github_connected ? 'connected' : ''}`}>
          <div className="connection-info">
            <div className="connection-icon">
              <i className="fab fa-github"></i> {/* Assuming FontAwesome or similar is available, or use SVG */}
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
              </svg>
            </div>
            <div className="connection-details">
              <h4>GitHub</h4>
              <p>{user.github_connected ? `Connected as ${user.github_username}` : 'Connect to import repositories'}</p>
            </div>
          </div>
          <div className="connection-status">
            {user.github_connected ? (
              <span className="status-badge connected">Connected</span>
            ) : (
              <button className="btn-connect" onClick={() => handleConnect(githubUrl)}>Connect</button>
            )}
          </div>
        </div>

        {/* LinkedIn */}
        <div className={`connection-item ${user.linkedin_connected ? 'connected' : ''}`}>
          <div className="connection-info">
            <div className="connection-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/>
              </svg>
            </div>
            <div className="connection-details">
              <h4>LinkedIn</h4>
              <p>{user.linkedin_connected ? 'Account connected' : 'Connect to import professional profile'}</p>
            </div>
          </div>
          <div className="connection-status">
            {user.linkedin_connected ? (
              <span className="status-badge connected">Connected</span>
            ) : (
              <button className="btn-connect" onClick={() => handleConnect(linkedinUrl)}>Connect</button>
            )}
          </div>
        </div>
      </div>

      {/* Security */}
      <div className="profile-section">
        <div className="profile-section-title">Security</div>
        <form onSubmit={handlePasswordChange}>
          <div className="form-group">
            <label className="form-label">Current Password</label>
            <input 
              type={showCurrentPassword ? "text" : "password"} 
              className="form-input" 
              value={passwordForm.current_password}
              onChange={(e) => setPasswordForm({...passwordForm, current_password: e.target.value})}
              placeholder="••••••••"
            />
            <button 
              type="button" 
              className="password-toggle-btn"
              onClick={() => setShowCurrentPassword(!showCurrentPassword)}
              aria-label={showCurrentPassword ? "Hide password" : "Show password"}
            >
              {showCurrentPassword ? (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                  <line x1="1" y1="1" x2="23" y2="23"></line>
                </svg>
              ) : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                  <circle cx="12" cy="12" r="3"></circle>
                </svg>
              )}
            </button>
          </div>
          <div className="form-group">
            <label className="form-label">New Password</label>
            <input 
              type={showNewPassword ? "text" : "password"} 
              className="form-input" 
              value={passwordForm.new_password}
              onChange={(e) => setPasswordForm({...passwordForm, new_password: e.target.value})}
              placeholder="••••••••"
            />
            <button 
              type="button" 
              className="password-toggle-btn"
              onClick={() => setShowNewPassword(!showNewPassword)}
              aria-label={showNewPassword ? "Hide password" : "Show password"}
            >
              {showNewPassword ? (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                  <line x1="1" y1="1" x2="23" y2="23"></line>
                </svg>
              ) : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                  <circle cx="12" cy="12" r="3"></circle>
                </svg>
              )}
            </button>
          </div>
          <div className="form-group">
            <label className="form-label">Confirm New Password</label>
            <input 
              type={showConfirmPassword ? "text" : "password"} 
              className="form-input" 
              value={passwordForm.confirm_password}
              onChange={(e) => setPasswordForm({...passwordForm, confirm_password: e.target.value})}
              placeholder="••••••••"
            />
            <button 
              type="button" 
              className="password-toggle-btn"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              aria-label={showConfirmPassword ? "Hide password" : "Show password"}
            >
              {showConfirmPassword ? (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                  <line x1="1" y1="1" x2="23" y2="23"></line>
                </svg>
              ) : (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                  <circle cx="12" cy="12" r="3"></circle>
                </svg>
              )}
            </button>
          </div>
          <div className="form-actions">
            <button type="submit" className="btn-primary" disabled={isPasswordLoading}>
              {isPasswordLoading ? 'Updating...' : 'Change Password'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default ProfileTab;
