import { useEffect, useState, useRef } from 'react';
import { useSearchParams, useParams } from 'react-router-dom';
import { apiClient } from '@/lib/api.ts';
import JourneyBackground from '@/components/JourneyBackground';
import ImmersiveAudio from '@/components/ImmersiveAudio';
import HeroSection from '@/components/journey/HeroSection';
import TimelineSection from '@/components/journey/TimelineSection';
import ExperienceSection from '@/components/journey/ExperienceSection';
import SkillsSection from '@/components/journey/SkillsSection';
import ProjectsSection from '@/components/journey/ProjectsSection';
import DocumentarySection from '@/components/journey/DocumentarySection';
import './Journey.css';

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

const Journey: React.FC = () => {
  const [searchParams] = useSearchParams();
  const { guestId } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [journey, setJourney] = useState<JourneyData | null>(null);
  const [timeline, setTimeline] = useState<TimelineData | null>(null);
  const [documentary, setDocumentary] = useState<DocumentaryData | null>(null);
  const [activeSection, setActiveSection] = useState(0);
  
  const containerRef = useRef<HTMLDivElement>(null);
  const pollTimeoutRef = useRef<number | null>(null);

  useEffect(() => {
    // Determine if we're loading by jobId (traditional) or guestId (new format)
    const jobId = searchParams.get('jobId');
    
    if (!jobId && !guestId) {
      setError('No job ID or guest ID provided');
      setLoading(false);
      return;
    }

    const fetchProfileData = async () => {
      try {
        let response;
        
        if (guestId) {
          // New format: /journey/{guest_id}
          response = await apiClient.getJourneyByGuestId(guestId);
          
          // Data structure from guest_id endpoint is different
          setProfile(response.profile || null);
          setJourney(response.journey || null);
          setTimeline(response.timeline || null);
          setDocumentary(response.documentary || null);
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
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Loading your immersive journey...</p>
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
      <JourneyBackground activeSection={activeSection} />
      <ImmersiveAudio profile={profile} />
      
      <div className="journey-content">
        {/* Hero Section */}
        <HeroSection 
          profile={profile} 
          documentary={documentary}
          journey={journey}
          sectionIndex={0}
        />

        {/* Timeline Section */}
        {timeline && (
          <TimelineSection 
            timeline={timeline}
            journey={journey}
            sectionIndex={1}
          />
        )}

        {/* Experience Section */}
        {profile?.experiences && profile.experiences.length > 0 && (
          <ExperienceSection 
            experiences={profile.experiences}
            journey={journey}
            sectionIndex={2}
          />
        )}

        {/* Skills Section */}
        {profile?.skills && profile.skills.length > 0 && (
          <SkillsSection 
            skills={profile.skills}
            journey={journey}
            sectionIndex={3}
          />
        )}

        {/* Projects Section */}
        {profile?.projects && profile.projects.length > 0 && (
          <ProjectsSection 
            projects={profile.projects}
            achievements={profile.achievements}
            sectionIndex={4}
          />
        )}

        {/* Documentary Section */}
        {documentary && (
          <DocumentarySection 
            documentary={documentary}
            profile={profile}
            sectionIndex={5}
          />
        )}
      </div>

      {/* Section Navigation */}
      <nav className="section-navigation">
        <div className="nav-dots">
          {[0, 1, 2, 3, 4, 5].map((index) => (
            <button
              key={index}
              className={`nav-dot ${activeSection === index ? 'active' : ''}`}
              onClick={() => {
                const section = document.querySelector(`[data-section="${index}"]`);
                section?.scrollIntoView({ behavior: 'smooth' });
              }}
              aria-label={`Go to section ${index + 1}`}
            />
          ))}
        </div>
      </nav>
    </main>
  );
};

export default Journey;
