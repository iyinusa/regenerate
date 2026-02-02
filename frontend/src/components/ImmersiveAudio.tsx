import React, { useState, useEffect, useRef } from 'react';

// Define the industry map based on keywords
const INDUSTRY_KEYWORDS: Record<string, string[]> = {
  technology: ['developer', 'engineer', 'software', 'tech', 'data', 'it', 'web', 'cyber', 'code', 'stack', 'cloud', 'ai', 'machine learning'],
  finance: ['finance', 'bank', 'economics', 'accountant', 'audit', 'tax', 'investment', 'capital', 'fund', 'asset'],
  creative: ['designer', 'artist', 'creative', 'writer', 'director', 'ui', 'ux', 'art', 'media', 'film', 'photo'],
  business: ['manager', 'business', 'sales', 'marketing', 'exec', 'founder', 'ceo', 'consultant', 'strategy', 'operations'],
  game: ['game', 'unity', 'unreal', '3d', 'animation', 'vfx', 'gameplay', 'level design'],
};

interface ImmersiveAudioProps {
  profile: any;
}

const ImmersiveAudio: React.FC<ImmersiveAudioProps> = ({ profile }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [audioLoaded, setAudioLoaded] = useState(false);
  const [audioError, setAudioError] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [audioSrc, setAudioSrc] = useState<string>('');
  
  // Determine industry on mount or profile change
  useEffect(() => {
    if (!profile) return;

    const text = [
      profile.name || '',
      profile.title || '',
      profile.bio || '',
      ...(profile.skills || []),
      ...(profile.experiences?.filter((e: any) => e).map((e: any) => (e.title || '') + ' ' + (e.description || '')) || [])
    ].join(' ').toLowerCase();

    let foundIndustry = 'others';
    let maxCount = 0;

    Object.entries(INDUSTRY_KEYWORDS).forEach(([key, keywords]) => {
      let count = 0;
      keywords.forEach(word => {
        if (text.includes(word)) count++;
      });
      // Weight matches? Simple count for now
      if (count > maxCount) {
        maxCount = count;
        foundIndustry = key;
      }
    });

    // If no specific keywords found but we have profile, default to others or one based on title
    const newAudioSrc = `/immersive/${foundIndustry}.wav`;
    setAudioSrc(newAudioSrc);
    setAudioLoaded(false);
    setAudioError(false);
    console.log(`[ImmersiveAudio] Selected industry: ${foundIndustry}, Audio src: ${newAudioSrc}`);
    
  }, [profile]);

  // Handle audio loading and error events
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleLoadedData = () => {
      console.log(`[ImmersiveAudio] Audio loaded successfully: ${audioSrc}`);
      setAudioLoaded(true);
      setAudioError(false);
    };

    const handleError = (e: Event) => {
      console.error(`[ImmersiveAudio] Audio loading failed: ${audioSrc}`, e);
      setAudioError(true);
      setAudioLoaded(false);
      setIsPlaying(false);
    };

    audio.addEventListener('loadeddata', handleLoadedData);
    audio.addEventListener('error', handleError);

    return () => {
      audio.removeEventListener('loadeddata', handleLoadedData);
      audio.removeEventListener('error', handleError);
    };
  }, [audioSrc]);

  // Handle play/pause functionality
  useEffect(() => {
    if (audioRef.current) {
      // Set initial volume low to be subtle
      audioRef.current.volume = 0.3; 
      
      if (isPlaying && audioLoaded) {
        const playPromise = audioRef.current.play();
        if (playPromise !== undefined) {
          playPromise
            .then(() => {
              console.log(`[ImmersiveAudio] Playing: ${audioSrc}`);
            })
            .catch(error => {
              console.log("Audio autoplay prevented or failed:", error);
              setIsPlaying(false); // Reset state if failed
            });
        }
      } else if (audioRef.current) {
        audioRef.current.pause();
      }
    }
  }, [isPlaying, audioSrc, audioLoaded]);

  // Toggle play/pause
  const handleToggle = () => {
    if (audioError) {
      console.log('[ImmersiveAudio] Cannot play audio due to loading error');
      return;
    }
    if (!audioLoaded) {
      console.log('[ImmersiveAudio] Audio not yet loaded');
      return;
    }
    setIsPlaying(!isPlaying);
  };

  return (
    <div style={{
      position: 'fixed',
      top: '20px',
      right: '20px',
      zIndex: 1000,
    }}>
      <button 
        onClick={handleToggle}
        disabled={!audioLoaded && !audioError}
        title={
          audioError ? "Audio unavailable" :
          !audioLoaded ? "Loading audio..." :
          isPlaying ? "Mute Cinematic Sound" : "Enable Cinematic Sound"
        }
        style={{
          width: '44px',
          height: '44px',
          borderRadius: '50%',
          backgroundColor: audioError ? 'rgba(128, 0, 0, 0.6)' : 'rgba(0, 0, 0, 0.6)',
          border: audioError ? '1px solid #ff4444' : '1px solid var(--accent-blue)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          cursor: (!audioLoaded && !audioError) ? 'wait' : audioError ? 'not-allowed' : 'pointer',
          backdropFilter: 'blur(5px)',
          boxShadow: isPlaying ? '0 0 15px rgba(31, 74, 174, 0.6)' : 'none',
          transition: 'all 0.3s ease',
          color: audioError ? '#ff4444' : isPlaying ? 'var(--accent-blue)' : '#aaaaaa',
          opacity: (!audioLoaded && !audioError) ? 0.6 : 1,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.backgroundColor = 'rgba(31, 74, 174, 0.2)';
          e.currentTarget.style.color = '#ffffff';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.backgroundColor = 'rgba(0, 0, 0, 0.6)';
          e.currentTarget.style.color = isPlaying ? 'var(--accent-blue)' : '#aaaaaa';
        }}
      >
        {!audioLoaded && !audioError ? (
          // Loading spinner
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" opacity="0.3"/>
            <path d="M12 2a10 10 0 0 1 10 10" strokeDasharray="31.416" strokeDashoffset="31.416">
              <animate attributeName="stroke-dashoffset" dur="1s" values="31.416;0" repeatCount="indefinite"/>
            </path>
          </svg>
        ) : audioError ? (
          // Error icon
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
        ) : isPlaying ? (
           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/></svg>
        ) : (
           <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><line x1="23" y1="9" x2="17" y2="15"></line><line x1="17" y1="9" x2="23" y2="15"></line></svg>
        )}
      </button>
      {/* Audio element with preload */}
      <audio 
        ref={audioRef} 
        src={audioSrc} 
        loop 
        preload="auto"
        crossOrigin="anonymous"
      />
    </div>
  );
};

export default ImmersiveAudio;
