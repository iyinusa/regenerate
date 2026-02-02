import { useEffect, useState, useRef } from 'react';
import { useSearchParams, useParams } from 'react-router-dom';
import { apiClient } from '@/lib/api.ts';
import { useAuth } from '@/hooks/useAuth';
import JourneyBackground from '@/components/JourneyBackground';
import ImmersiveAudio from '@/components/ImmersiveAudio';
import HeroSection from '@/components/journey/HeroSection';
import TimelineSection from '@/components/journey/TimelineSection';
import ExperienceSection from '@/components/journey/ExperienceSection';
import EducationSection from '@/components/journey/EducationSection';
import CertificationsSection from '@/components/journey/CertificationsSection';
import SkillsSection from '@/components/journey/SkillsSection';
import ProjectsSection from '@/components/journey/ProjectsSection';
import DocumentarySection from '@/components/journey/DocumentarySection';
import AuthModal from '@/components/AuthModal';
import ProfileModal from '@/components/profile/ProfileModal';
import './Journey.css';
import ThemeToggle from '@/components/ThemeToggle';

interface ProfileData {
  name?: string;
  title?: string;
  location?: string;
  bio?: string;
  experiences?: any[];
  education?: any[];
  skills?: string[];
  projects?: any[];
  achievements?: any[];
  certifications?: any[];
  email?: string;
  website?: string;
  linkedin?: string;
  github?: string;
  social_links?: Record<string, string>;
}

interface JourneyData {
  summary?: any;
  milestones?: any[];
  career_chapters?: any[];
  skills_evolution?: any[];
  impact_metrics?: any;
}

interface TimelineData {
  events?: any[];
  eras?: any[];
}

interface DocumentaryData {
  title?: string;
  tagline?: string;
  duration_estimate?: string;
  segments?: any[];
  opening_hook?: string;
  closing_statement?: string;
}

interface PrivacySettings {
  hidden_sections?: Record<string, boolean>;
}

const Journey: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { guestId, username } = useParams(); // Added username
  const { isAuthenticated, guestId: currentUserGuestId } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [journey, setJourney] = useState<JourneyData | null>(null);
  const [timeline, setTimeline] = useState<TimelineData | null>(null);
  const [documentary, setDocumentary] = useState<DocumentaryData | null>(null);
  const [introVideo, setIntroVideo] = useState<string | null>(null);
  const [fullVideo, setFullVideo] = useState<string | null>(null);
  const [historyId, setHistoryId] = useState<string | null>(null);
  const [privacySettings, setPrivacySettings] = useState<PrivacySettings | null>(null);
  const [activeSection, setActiveSection] = useState(0);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [authMessage, setAuthMessage] = useState('');
  
  const containerRef = useRef<HTMLDivElement>(null);
  const pollTimeoutRef = useRef<number | null>(null);

  // Check if user owns this journey (for editing permissions)
  // We compare the URL guestId with the authenticated user's guestId
  // Public view (username present) disables editing
  const isPublicView = !!username;
  const canEdit = !isPublicView && isAuthenticated && !!guestId && !!currentUserGuestId && guestId === currentUserGuestId;

  // Helper function to check if a section should be visible
  const isSectionVisible = (sectionId: string) => {
    if (!isPublicView || !privacySettings?.hidden_sections) return true;
    return !privacySettings.hidden_sections[sectionId];
  };

  // Calculate visible sections for navigation
  const getVisibleSections = () => {
    // If not public view (owner mode), show sections even if empty so they can be edited
    // If public view, only show populated sections
    const shouldShow = (hasData: boolean) => hasData || !isPublicView;

    const sections = [
      { id: 'hero', index: 0, visible: true }, // Hero is always visible
      { id: 'chronicles', index: 1, visible: isSectionVisible('chronicles') && shouldShow(!!(timeline?.events?.length)) },
      { id: 'experience', index: 2, visible: isSectionVisible('experience') && shouldShow(!!(profile?.experiences?.length)) },
      { id: 'education', index: 3, visible: isSectionVisible('education') && shouldShow(!!(profile?.education?.length)) },
      { id: 'skills', index: 4, visible: isSectionVisible('skills') && shouldShow(!!(profile?.skills?.length)) },
      { id: 'projects', index: 5, visible: isSectionVisible('projects') && shouldShow(!!(profile?.projects?.length)) },
      { id: 'certifications', index: 6, visible: isSectionVisible('certifications') && shouldShow(!!(profile?.certifications?.length)) },
      { id: 'documentary', index: 7, visible: !!documentary }
    ];
    return sections.filter(section => section.visible);
  };

  useEffect(() => {
    // Determine if we're loading by jobId (traditional), guestId (new format), or username (public)
    const jobId = searchParams.get('jobId');
    
    if (!jobId && !guestId && !username) {
      setError('No profile provided');
      setLoading(false);
      return;
    }

    const fetchProfileData = async () => {
      try {
        let response;
        
        if (username) {
            // Public profile fetch
            response = await apiClient.request(`/api/v1/privacy/public/${username}`);
            
            setProfile(response.profile || null);
            setJourney(response.journey || null);
            setTimeline(response.timeline || null);
            setDocumentary(response.documentary || null);
            setIntroVideo(response.intro_video || null);
            setFullVideo(response.full_video || null);
            setPrivacySettings({ hidden_sections: response.hidden_sections || {} });
            setLoading(false);
            return;
        }

        if (guestId) {
          // New format: /journey/{guest_id}
          const historyIdParam = searchParams.get('history_id');
          response = await apiClient.getJourneyByGuestId(guestId, historyIdParam);
          
          // Data structure from guest_id endpoint is different
          setProfile(response.profile || null);
          setJourney(response.journey || null);
          setTimeline(response.timeline || null);
          setDocumentary(response.documentary || null);
          setIntroVideo(response.intro_video || null);
          setFullVideo(response.full_video || null);
          setHistoryId(response.history_id || null); // Capture history ID for editing
          setLoading(false);
        } else if (jobId) {
          // Traditional format: /journey?jobId={job_id}
          response = await apiClient.getProfileStatus(jobId);
          
          if (response.status === 'failed') {
            setError(response.error || 'Failed to load profile');
            setLoading(false);
            return;
          }

          if (response.status === 'completed') {
            setProfile(response.data || null);
            setJourney(response.journey || null);
            setTimeline(response.timeline || null);
            setDocumentary(response.documentary || null);
            setIntroVideo(response.intro_video || null);
            setFullVideo(response.full_video || null);
            setLoading(false);
          } else {
            // Still processing, poll again
            pollTimeoutRef.current = setTimeout(fetchProfileData, 2000) as any;
          }
        }
      } catch (err: any) {
        console.error('Failed to fetch profile:', err);
        
        // Handle specific error cases
        if (err.message && err.message.includes('404')) {
          setError('Profile session not found. This may be due to a server restart.');
        } else {
          setError('Failed to load profile data');
        }
        
        setLoading(false);
        // Don't continue polling on error
        return;
      }
    };

    fetchProfileData();

    return () => {
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current);
      }
    };
  }, [searchParams, guestId]);

  const handleAuthRequired = (action?: string) => {
    setAuthMessage(`Please sign in to ${action?.toLowerCase()}`);
    setShowAuthModal(true);
  };

  const handleEdit = (action: string, callback: () => void) => {
    if (!isAuthenticated) {
      handleAuthRequired(action);
      return;
    }
    
    if (!canEdit) {
      setAuthMessage('You can only edit your own journey');
      setShowAuthModal(true);
      return;
    }
    
    callback();
  };

  // Intersection observer for scroll animations
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            const sectionIndex = parseInt(entry.target.getAttribute('data-section') || '0');
            setActiveSection(sectionIndex);
          }
        });
      },
      { threshold: 0.3 }
    );

    const sections = containerRef.current?.querySelectorAll('.journey-section');
    sections?.forEach((section) => observer.observe(section));

    return () => observer.disconnect();
  }, [loading]);

  if (loading) {
    return (
      <main className="journey-page loading">
        <JourneyBackground />

        <div className="shimmer-container">
          {/* Hero skeleton */}
          <div className="shimmer-section shimmer-hero" data-section="0">
            <div className="shimmer-avatar" />
            <div className="shimmer-hero-lines">
              <div className="shimmer-line short" />
              <div className="shimmer-line medium" />
              <div className="shimmer-line long" />
            </div>
          </div>

          {/* Two-column grid that mimics timeline + profile sections */}
          <div className="shimmer-grid">
            <div className="shimmer-section shimmer-chronicles" data-section="1">
              <div className="shimmer-title" />
              <div className="shimmer-timeline">
                <div className="shimmer-event" />
                <div className="shimmer-event short" />
                <div className="shimmer-event long" />
                <div className="shimmer-event" />
              </div>
            </div>

            <div className="shimmer-section shimmer-cards" data-section="2">
              <div className="shimmer-card">
                <div className="shimmer-line medium" />
                <div className="shimmer-line short" />
                <div className="shimmer-line long" />
              </div>
              <div className="shimmer-card">
                <div className="shimmer-line medium" />
                <div className="shimmer-line short" />
                <div className="shimmer-line long" />
              </div>
              <div className="shimmer-card">
                <div className="shimmer-line medium" />
                <div className="shimmer-line short" />
                <div className="shimmer-line long" />
              </div>
            </div>
          </div>

          {/* Wide sections to represent skills/projects/education */}
          <div className="shimmer-section shimmer-wide" data-section="3">
            <div className="shimmer-title" />
            <div className="shimmer-row">
              <div className="shimmer-block" />
              <div className="shimmer-block small" />
              <div className="shimmer-block" />
            </div>
          </div>

          {/* Documentary skeleton */}
          <div className="shimmer-section shimmer-documentary" data-section="7">
            <div className="shimmer-title" />
            <div className="shimmer-line long" />
          </div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="journey-page error">
        <div className="error-container">
          <h1>Unable to Load Journey</h1>
          <p>{error}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="journey-page" ref={containerRef}>
      {/* Theme Toggle at top center */}
      <ThemeToggle />

      {/* Auth Modal */}
      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        initialMode="login"
      />

      {/* Auth message overlay */}
      {authMessage && (
        <div className="auth-message-overlay">
          <div className="auth-message">
            <p>{authMessage}</p>
            <button className="submit-button" onClick={() => setAuthMessage('')}>Got it</button>
          </div>
        </div>
      )}
      <JourneyBackground activeSection={activeSection} />
      <ImmersiveAudio profile={profile} />

      {/* Profile Menu Button */}
      {isAuthenticated && (
        <button 
          className="profile-menu-btn"
          onClick={() => setShowProfileModal(true)}
          onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'}
          onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(20, 20, 25, 0.6)'}
          aria-label="Open Settings"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>
      )}

      <ProfileModal isOpen={showProfileModal} onClose={() => setShowProfileModal(false)} />

      <div className="journey-content">
        {/* Hero Section */}
        <HeroSection 
          profile={profile} 
          documentary={documentary}
          journey={journey}
          introVideo={introVideo}
          fullVideo={fullVideo}
          sectionIndex={0}
          historyId={historyId || undefined}
          // canEdit={canEdit}
          onDocumentaryUpdate={setDocumentary}
          onGenerateVideo={() => {
            handleEdit('generate video', async () => {
              if (!historyId) {
                console.error('No history ID available for video generation');
                return;
              }
              
              try {
                console.log('Generating documentary video...');
                const result = await apiClient.generateVideo(historyId, {
                  export_format: '1080p',
                  aspect_ratio: '16:9',
                  first_segment_only: true
                });
                
                if (result.job_id) {
                  console.log('Video generation started:', result);
                  // You could show a toast notification here or update UI
                  // The WebSocket connection should handle progress updates
                }
              } catch (error) {
                console.error('Failed to start video generation:', error);
              }
            });
          }}
          onRegenerateVideo={() => {
            handleEdit('regenerate video', async () => {
              if (!historyId) {
                console.error('No history ID available for video regeneration');
                return;
              }
              
              try {
                console.log('Regenerating documentary video...');
                const result = await apiClient.generateVideo(historyId, {
                  export_format: '720p',
                  aspect_ratio: '16:9',
                  first_segment_only: false
                });
                
                if (result.job_id) {
                  console.log('Video regeneration started:', result);
                }
              } catch (error) {
                console.error('Failed to start video regeneration:', error);
              }
            });
          }}
          onRequestEdit={handleEdit}
        />

        {/* Timeline Section */}
        {((timeline?.events && timeline.events.length > 0) || !isPublicView) && isSectionVisible('chronicles') && (
          <TimelineSection 
            timeline={timeline}
            journey={journey}
            sectionIndex={1}
            historyId={isPublicView ? undefined : (historyId || undefined)}
            onRequestEdit={handleEdit}
          />
        )}

        {/* Experience Section */}
        {((profile?.experiences && profile.experiences.length > 0) || !isPublicView) && isSectionVisible('experience') && (
          <ExperienceSection 
            experiences={profile?.experiences || []}
            journey={journey}
            sectionIndex={2}
            historyId={isPublicView ? undefined : (historyId || undefined)}
            onRequestEdit={handleEdit}
          />
        )}

        {/* Skills Section */}
        {((profile?.skills && profile.skills.length > 0) || !isPublicView) && isSectionVisible('skills') && (
          <SkillsSection 
            skills={profile?.skills || []}
            journey={journey}
            profile={profile || {}}
            sectionIndex={3}
          />
        )}

        {/* Projects Section */}
        {((profile?.projects && profile.projects.length > 0) || !isPublicView) && isSectionVisible('projects') && (
          <ProjectsSection 
            projects={profile?.projects || []}
            achievements={profile?.achievements || []}
            sectionIndex={4}
            historyId={isPublicView ? undefined : (historyId || undefined)}
            onRequestEdit={handleEdit}
          />
        )}

        {/* Education Section */}
        {((profile?.education && profile.education.length > 0) || !isPublicView) && isSectionVisible('education') && (
          <EducationSection
            education={profile?.education || []}
            journey={journey}
            sectionIndex={5}
            historyId={isPublicView ? undefined : (historyId || undefined)}
            onRequestEdit={handleEdit}
          />
        )}

        {/* Certification Section */}
        {((profile?.certifications && profile.certifications.length > 0) || !isPublicView) && isSectionVisible('certifications') && (
          <CertificationsSection 
            certifications={profile?.certifications || []}
            journey={journey}
            sectionIndex={6}
            historyId={isPublicView ? undefined : (historyId || undefined)}
            onRequestEdit={handleEdit}
          />
        )}

        {/* Documentary Section */}
        {documentary && (
          <DocumentarySection 
            documentary={documentary}
            profile={profile}
            sectionIndex={7}
          />
        )}
      </div>

      {/* Section Navigation */}
      <nav className="section-navigation">
        <div className="nav-dots">
          {getVisibleSections().map((section) => (
            <button
              key={section.index}
              className={`nav-dot ${activeSection === section.index ? 'active' : ''}`}
              onClick={() => {
                const sectionElement = document.querySelector(`[data-section="${section.index}"]`);
                sectionElement?.scrollIntoView({ behavior: 'smooth' });
              }}
              aria-label={`Go to ${section.id} section`}
            />
          ))}
        </div>
      </nav>
    </main>
  );
};

export default Journey;
