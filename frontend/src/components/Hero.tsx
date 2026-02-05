import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { gsap } from 'gsap';
import { TextPlugin } from 'gsap/TextPlugin';
import { apiClient } from '@/lib/api.ts';
import { useAuth } from '@/hooks/useAuth';
import AuthModal from './AuthModal';
import './Hero.css';

gsap.registerPlugin(TextPlugin);

// Source type for profile generation
type SourceType = 'url' | 'resume';

interface HeroProps {
  onGenerate: (data: { url: string; jobId?: string; status?: string }) => void;
}

const Hero: React.FC<HeroProps> = ({ onGenerate }) => {
  const heroRef = useRef<HTMLElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const subtitleRef = useRef<HTMLParagraphElement>(null);
  const ctaRef = useRef<HTMLDivElement>(null);
  const urlInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const navigate = useNavigate();
  const { user, isAuthenticated, guestId, loading: authLoading, logout } = useAuth();

  const [isLoading, setIsLoading] = useState(false);
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authModalMode, setAuthModalMode] = useState<'login' | 'register'>('login');
  const [suggestRegister, setSuggestRegister] = useState(false);
  const [oauthInfo, setOauthInfo] = useState<{ provider?: 'github' | 'linkedin'; username?: string }>({});
  const [oauthStatus, setOauthStatus] = useState<{
    github: { connected: boolean; username?: string };
    linkedin: { connected: boolean; expired?: boolean };
  }>({
    github: { connected: false },
    linkedin: { connected: false }
  });
  
  // New state for source type toggle
  const [sourceType, setSourceType] = useState<SourceType>('url');
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState<string>('');

  useEffect(() => {
    // Test API connection
    apiClient.healthCheck()
      .then(() => console.log('API connection established'))
      .catch((err) => console.warn('API connection failed:', err));

    // Load OAuth status when auth is ready
    if (!authLoading && (isAuthenticated || guestId)) {
      loadOAuthStatus();
    }

    // Check URL params for OAuth callbacks
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('github_connected') === 'true') {
      const username = urlParams.get('username');
      setOauthStatus(prev => ({
        ...prev,
        github: { connected: true, username: username || undefined }
      }));
      setOauthInfo({ provider: 'github', username: username || undefined });
      
      if (urlParams.get('suggest_register') === 'true' && !isAuthenticated) {
        setSuggestRegister(true);
        setAuthModalMode('register');
        setShowAuthModal(true);
      }
      
      // Clean URL
      window.history.replaceState({}, '', window.location.pathname);
    }
    if (urlParams.get('linkedin_connected') === 'true') {
      setOauthStatus(prev => ({
        ...prev,
        linkedin: { connected: true }
      }));
      setOauthInfo({ provider: 'linkedin' });
      
      if (urlParams.get('suggest_register') === 'true' && !isAuthenticated) {
        setSuggestRegister(true);
        setAuthModalMode('register');
        setShowAuthModal(true);
      }
      
      // Clean URL
      window.history.replaceState({}, '', window.location.pathname);
    }
    if (urlParams.get('error')) {
      setError(`OAuth Error: ${urlParams.get('error')}`);
      window.history.replaceState({}, '', window.location.pathname);
    }

    // GSAP animations on mount
    const tl = gsap.timeline();
    
    // Set initial state first to ensure elements are visible if animation fails
    gsap.set(".hero-content > *", { opacity: 1, y: 0 });
    gsap.set(".feature-card", { opacity: 1, y: 0 });
    
    // entrance animation
    tl.fromTo(".hero-content > *", 
      { y: 100, opacity: 0 },
      { 
        y: 0,
        opacity: 1,
        duration: 1.2,
        stagger: 0.2,
        ease: "power4.out"
      }
    )
    .fromTo(".feature-card", 
      { opacity: 0, y: 50 },
      {
        opacity: 1,
        y: 0,
        stagger: 0.1,
        duration: 1,
        ease: "power3.out"
      }, "-=0.5");

  }, [authLoading, isAuthenticated, guestId]);

  const loadOAuthStatus = async () => {
    try {
      const status = await apiClient.getOAuthStatus(isAuthenticated ? undefined : guestId);
      if (status.user_found) {
        setOauthStatus({
          github: status.github,
          linkedin: status.linkedin
        });
      }
    } catch (err: any) {
      console.warn('OAuth status check failed:', err);
    }
  };

  async function handleGenerate() {
    // Validate based on source type
    if (sourceType === 'url' && !url.trim()) {
      setError('Please enter a profile URL');
      return;
    }
    if (sourceType === 'resume' && !resumeFile) {
      setError('Please select a resume PDF to upload');
      return;
    }
    
    setIsLoading(true);
    setError('');
    setUploadProgress('');
    
    try {
      let response;
      
      if (sourceType === 'resume' && resumeFile) {
        // Step 1: Upload the resume PDF
        setUploadProgress('Uploading resume...');
        const uploadResult = await apiClient.uploadResume(resumeFile);
        
        // Step 2: Start profile generation with resume URL
        setUploadProgress('Analysing resume...');
        response = await apiClient.generateProfile({
          source_type: 'resume',
          resume_file_url: uploadResult.url,
          include_github: false
        });
        
        onGenerate({
          url: uploadResult.url,
          jobId: response.job_id,
          status: response.status
        });
      } else {
        // URL-based profile generation
        response = await apiClient.generateProfile({
          source_type: 'url',
          url: url.trim(),
          include_github: false
        });
        
        onGenerate({
          url: url.trim(),
          jobId: response.job_id,
          status: response.status
        });
      }
      
    } catch (err: any) {
      console.error('Profile generation failed:', err);
      setError(err.message || 'Failed to start profile generation. Please try again.');
    } finally {
      setIsLoading(false);
      setUploadProgress('');
    }
  }
  
  function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file type
      if (file.type !== 'application/pdf') {
        setError('Please upload a PDF file');
        return;
      }
      // Validate file size (max 10MB)
      if (file.size > 10 * 1024 * 1024) {
        setError('File size exceeds 10MB limit');
        return;
      }
      setResumeFile(file);
      setError('');
    }
  }
  
  function handleFileDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0];
    if (file) {
      if (file.type !== 'application/pdf') {
        setError('Please upload a PDF file');
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        setError('File size exceeds 10MB limit');
        return;
      }
      setResumeFile(file);
      setError('');
    }
  }
  
  function handleDragOver(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
  }
  
  function clearResumeFile() {
    setResumeFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  }

  async function handleGitHubOAuth() {
    try {
      const authUrl = await apiClient.githubOAuth(isAuthenticated ? undefined : guestId);
      window.location.href = authUrl.redirect_url;
    } catch (err) {
      console.error('GitHub OAuth failed:', err);
      setError('GitHub OAuth is unavailable.');
    }
  }

  async function handleLinkedInOAuth() {
    try {
      const authUrl = await apiClient.linkedinOAuth(isAuthenticated ? undefined : guestId);
      window.location.href = authUrl.redirect_url;
    } catch (err) {
      console.error('LinkedIn OAuth failed:', err);
      setError('LinkedIn OAuth is unavailable.');
    }
  }

  function handleKeyPress(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter') {
      handleGenerate();
    }
  }

  async function handleLogout() {
    try {
      await logout();
    } catch (err) {
      console.error('Logout failed:', err);
    }
  }

  function handleUsernameClick() {
    if (guestId) {
      navigate(`/journey/${guestId}`);
    } else if (user?.username) {
      navigate(`/journey/${user.username}`);
    }
  }

  return (
    <section className="hero" ref={heroRef}>
      <div className="hero-container">
        {/* Auth Modal */}
        <AuthModal
          isOpen={showAuthModal}
          onClose={() => setShowAuthModal(false)}
          initialMode={authModalMode}
          suggestRegister={suggestRegister}
          oauthInfo={oauthInfo}
        />

        {/* User Authentication UI */}
        <div className="auth-section">
          {isAuthenticated ? (
            <div className="user-menu">
              <div className="user-info">
                <span 
                  className="user-name" 
                  onClick={handleUsernameClick}
                  style={{ cursor: 'pointer' }}
                  title="View your journey"
                >
                  {user?.full_name || user?.username || 'User'}
                </span>
                {(user?.github_connected || user?.linkedin_connected) && (
                  <div className="connected-badges">
                    {user.github_connected && (
                      <span className="badge github">GitHub</span>
                    )}
                    {user.linkedin_connected && (
                      <span className="badge linkedin">LinkedIn</span>
                    )}
                  </div>
                )}
                <button 
                  className="sign-out-btn"
                  onClick={handleLogout}
                  title="Sign out"
                >
                  Sign Out
                </button>
              </div>
            </div>
          ) : (
            <div className="auth-buttons">
              <button 
                className="auth-btn login-btn"
                onClick={() => {
                  setAuthModalMode('login');
                  setSuggestRegister(false);
                  setOauthInfo({});
                  setShowAuthModal(true);
                }}
              >
                Sign In
              </button>
            </div>
          )}
        </div>

        {/* Decorative Background Elements */}
        <div className="glow-orb top-left floating-decoration"></div>
        <div className="glow-orb bottom-right floating-decoration" style={{ animationDelay: '-1.25s' }}></div>

        <div className="hero-content">
          <div className="header-reveal">
            <div className="terminal-badge">
              <span className="dot red"></span>
              <span className="dot yellow"></span>
              <span className="dot green"></span>
              <span className="terminal-text">AI_ENGINE::ACTIVE</span>
            </div>
          </div>

          {/* Logo */}
          <img src="/favicon.png" alt="Logo" className="hero-logo" />

          <h1 ref={titleRef} className="mhero-title">
            REGENERATE <br />
            <span className="gradient-text">YOUR JOURNEY</span>
          </h1>
          
          <p ref={subtitleRef} className="mhero-subtitle">
            Traditional resumes are fading. We are using the <span className="highlight">Smartest AI</span> to distill your entire professional footprint into an immersive cinematic experience. Your work deserves to be celebrated.
          </p>

          <div ref={ctaRef} className="cta-section">
            {/* Source Type Toggle */}
            <div className="source-toggle">
              <button
                className={`toggle-btn ${sourceType === 'url' ? 'active' : ''}`}
                onClick={() => { setSourceType('url'); setError(''); }}
                disabled={isLoading}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M3.9 12c0-1.71 1.39-3.1 3.1-3.1h4V7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h4v-1.9H7c-1.71 0-3.1-1.39-3.1-3.1zM8 13h8v-2H8v2zm9-6h-4v1.9h4c1.71 0 3.1 1.39 3.1 3.1s-1.39 3.1-3.1 3.1h-4V17h4c2.76 0 5-2.24 5-5s-2.24-5-5-5z"/>
                </svg>
                Link
              </button>
              <button
                className={`toggle-btn ${sourceType === 'resume' ? 'active' : ''}`}
                onClick={() => { setSourceType('resume'); setError(''); }}
                disabled={isLoading}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11zM8 15.01V17h2.01L14.5 12.51l-2.01-2.01L8 15.01zm6.87-5.9l1.03 1.03c.12.12.12.32 0 .44l-.9.9-1.47-1.47.9-.9c.12-.12.32-.12.44 0z"/>
                </svg>
                Resume
              </button>
            </div>
            
            {/* URL Input - shown when source type is 'url' */}
            {sourceType === 'url' && (
              <div className="input-wrapper glass-morphism">
                <div className="cli-prefix">
                  <span className="prompt-user">source</span><span className="prompt-symbol">➜</span>
                </div>
                <input
                  ref={urlInputRef}
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  onKeyPress={handleKeyPress}
                  type="url"
                  placeholder="Paste LinkedIn, Portfolio, or GitHub URL"
                  className="cli-input"
                  disabled={isLoading}
                  spellCheck="false"
                />
                <button
                  onClick={handleGenerate}
                  disabled={isLoading || !url.trim()}
                  className="refactor-run-button"
                >
                  {isLoading ? (
                    <div className="loader"></div>
                  ) : (
                    <span>REGEN NOW →</span>
                  )}
                </button>
              </div>
            )}
            
            {/* Resume Upload - shown when source type is 'resume' */}
            {sourceType === 'resume' && (
              <div className="resume-upload-wrapper glass-morphism">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,application/pdf"
                  onChange={handleFileChange}
                  style={{ display: 'none' }}
                  disabled={isLoading}
                />
                
                {!resumeFile ? (
                  <div 
                    className="resume-dropzone"
                    onClick={() => fileInputRef.current?.click()}
                    onDrop={handleFileDrop}
                    onDragOver={handleDragOver}
                  >
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor" className="upload-icon">
                      <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zM6 20V4h7v5h5v11H6zm5-6v4h2v-4h3l-4-4-4 4h3z"/>
                    </svg>
                    <span className="dropzone-text">
                      Drop your resume PDF here or <span className="browse-link">browse</span>
                    </span>
                    <span className="dropzone-hint">PDF only, max 10MB</span>
                  </div>
                ) : (
                  <div className="resume-selected">
                    <div className="file-info">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" className="pdf-icon">
                        <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11z"/>
                      </svg>
                      <span className="file-name">{resumeFile.name}</span>
                      <span className="file-size">({(resumeFile.size / 1024 / 1024).toFixed(2)} MB)</span>
                      <button 
                        className="remove-file-btn"
                        onClick={clearResumeFile}
                        disabled={isLoading}
                        title="Remove file"
                      >
                        ✕
                      </button>
                    </div>
                    <button
                      onClick={handleGenerate}
                      disabled={isLoading}
                      className="refactor-run-button"
                    >
                      {isLoading ? (
                        <>
                          <div className="loader"></div>
                          {uploadProgress && <span className="upload-status">{uploadProgress}</span>}
                        </>
                      ) : (
                        <span>REGEN NOW →</span>
                      )}
                    </button>
                  </div>
                )}
              </div>
            )}
            
            {error && (
              <div className="system-error">
                <span className="error-icon">!</span>
                <span className="error-text">ERROR: {error}</span>
              </div>
            )}

            <div className="secondary-actions">
              <span className="divider-text">CONNECT</span>
              <div className="oauth-buttons">
                <button
                  className={`oauth-btn linkedin-btn ${oauthStatus.linkedin.connected ? 'connected' : ''}`}
                  onClick={handleLinkedInOAuth}
                  disabled={oauthStatus.linkedin.connected && !oauthStatus.linkedin.expired}
                >
                  <svg height="20" width="20" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                  </svg>
                  <span>
                    {oauthStatus.linkedin.connected
                      ? (oauthStatus.linkedin.expired ? 'Reconnect LinkedIn' : 'LinkedIn Connected')
                      : 'LinkedIn Access'}
                  </span>
                  {oauthStatus.linkedin.connected && !oauthStatus.linkedin.expired && (
                    <svg className="check-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="3">
                      <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                  )}
                </button>
                <button 
                  className={`oauth-btn github-btn ${oauthStatus.github.connected ? 'connected' : ''}`}
                  onClick={handleGitHubOAuth}
                  disabled={oauthStatus.github.connected}
                >
                  <svg height="20" width="20" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path>
                  </svg>
                  <span>
                    {oauthStatus.github.connected 
                      ? `Connected: ${oauthStatus.github.username || 'GitHub'}` 
                      : 'GitHub Access'}
                  </span>
                  {oauthStatus.github.connected && (
                    <svg className="check-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="3">
                      <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                  )}
                </button>
              </div>
              <span className="divider-text">for in-depth analysis</span>
            </div>
          </div>

          <div className="features-grid">
            <div className="feature-card">
              <div className="card-icon">// SCAN</div>
              <h3>AI SMART INGESTION</h3>
              <p>Deep scan of your professional digital twin. LinkedIn, GitHub, and Portfolios synchronised.</p>
            </div>
            <div className="feature-card">
              <div className="card-icon">// ANALYZE</div>
              <h3>AI-DRIVEN SYNTHESIS</h3>
              <p>Our Smart AI identifies patterns in your work history that standard resumes miss.</p>
            </div>
            <div className="feature-card">
              <div className="card-icon">// REGEN</div>
              <h3>CINEMATIC JOURNEY</h3>
              <p>Constructs an immersive, shareable narrative that tells your story better than just a resume.</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;
