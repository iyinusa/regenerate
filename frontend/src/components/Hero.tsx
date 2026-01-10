import { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { TextPlugin } from 'gsap/TextPlugin';
import { apiClient } from '@/lib/api.ts';
import './Hero.css';

gsap.registerPlugin(TextPlugin);

interface HeroProps {
  onGenerate: (data: { url: string; jobId?: string; status?: string }) => void;
}

const Hero: React.FC<HeroProps> = ({ onGenerate }) => {
  const heroRef = useRef<HTMLElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const subtitleRef = useRef<HTMLParagraphElement>(null);
  const ctaRef = useRef<HTMLDivElement>(null);
  const urlInputRef = useRef<HTMLInputElement>(null);

  const [isLoading, setIsLoading] = useState(false);
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    // Test API connection
    apiClient.healthCheck()
      .then(() => console.log('API connection established'))
      .catch((err) => console.warn('API connection failed:', err));

    // GSAP animations on mount
    const tl = gsap.timeline();
    
    // entrance animation
    tl.from(".hero-content > *", {
      y: 100,
      opacity: 0,
      duration: 1.2,
      stagger: 0.2,
      ease: "power4.out"
    })
    .from(".feature-card", {
      opacity: 0,
      y: 50,
      stagger: 0.1,
      duration: 1,
      ease: "power3.out"
    }, "-=0.8");

    // Floating animation for decorative elements
    gsap.to(".floating-decoration", {
      y: -30,
      x: 20,
      duration: 4,
      repeat: -1,
      yoyo: true,
      ease: "sine.inOut"
    });

    // Mouse move effect for title
    const handleMouseMove = (e: MouseEvent) => {
      const { clientX, clientY } = e;
      const xPos = (clientX / window.innerWidth - 0.5) * 20;
      const yPos = (clientY / window.innerHeight - 0.5) * 20;
      
      gsap.to(".hero-title", {
        x: xPos,
        y: yPos,
        duration: 1,
        ease: "power2.out"
      });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  async function handleGenerate() {
    if (!url.trim()) return;
    
    setIsLoading(true);
    setError('');
    
    try {
      // Call FastAPI backend to start profile generation
      const response = await apiClient.generateProfile({
        url: url.trim(),
        include_github: false
      });
      
      onGenerate({
        url: url.trim(),
        jobId: response.job_id,
        status: response.status
      });
      
    } catch (err) {
      console.error('Profile generation failed:', err);
      setError('Failed to start profile generation. Please check your URL.');
    } finally {
      setIsLoading(false);
    }
  }

  async function handleGitHubOAuth() {
    try {
      const authUrl = await apiClient.githubOAuth();
      window.location.href = authUrl.redirect_url;
    } catch (err) {
      console.error('GitHub OAuth failed:', err);
      setError('GitHub OAuth is unavailable.');
    }
  }

  function handleKeyPress(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter') {
      handleGenerate();
    }
  }

  return (
    <section className="hero" ref={heroRef}>
      <div className="hero-container">
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

          <h1 ref={titleRef} className="hero-title">
            REGENERATE <br />
            <span className="gradient-text">YOUR JOURNEY</span>
          </h1>
          
          <p ref={subtitleRef} className="hero-subtitle">
            Traditional resumes are fading. We use <span className="highlight">State-of-the-art AI</span> to distill your entire professional footprint into an immersive cinematic experience. Your work deserves more than bullet points.
          </p>

          <div ref={ctaRef} className="cta-section">
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
                placeholder="Paste LinkedIn, GitHub or Portfolio URL"
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
            
            {error && (
              <div className="system-error">
                <span className="error-icon">!</span>
                <span className="error-text">ERROR: {error}</span>
              </div>
            )}

            <div className="secondary-actions">
              <span className="divider-text">OR CONNECT SOURCE</span>
              <button className="github-btn" onClick={handleGitHubOAuth}>
                <svg height="20" width="20" viewBox="0 0 16 16" fill="currentColor">
                  <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path>
                </svg>
                <span>Authorize GitHub Access</span>
              </button>
              <span className="divider-text">for indepth analysis</span>
            </div>
          </div>

          <div className="features-grid">
            <div className="feature-card">
              <div className="card-icon">// SCAN</div>
              <h3>SMART INGESTION</h3>
              <p>Deep scan of your professional digital twin. LinkedIn, GitHub, and portfolios synchronized.</p>
            </div>
            <div className="feature-card">
              <div className="card-icon">// ANALYZE</div>
              <h3>AI-DRIVEN SYNTHESIS</h3>
              <p>Gemini 3 identifies patterns in your work history that standard resumes miss.</p>
            </div>
            <div className="feature-card">
              <div className="card-icon">// REGEN</div>
              <h3>CINEMATIC JOURNEY</h3>
              <p>Constructs an immersive, shareable narrative that tells your story better than you can.</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;
