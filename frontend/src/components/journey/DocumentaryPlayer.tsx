import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './DocumentaryPlayer.css';
import VideoGenerationModal, { VideoSettings } from './VideoGenerationModal';

interface DocumentaryPlayerProps {
  documentary: {
    intro_url?: string;
    full_video?: string;
    title?: string;
    tagline?: string;
    segments?: any[];
  };
  onGenerateVideo?: () => void;
  onRegenerateVideo?: () => void;
  onEditDocumentary?: () => void;
}

const DocumentaryPlayer: React.FC<DocumentaryPlayerProps> = ({
  documentary,
  onGenerateVideo,
  onRegenerateVideo,
  onEditDocumentary
}) => {
  const [isHovered, setIsHovered] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [showOverlay, setShowOverlay] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [showGenerationModal, setShowGenerationModal] = useState(false);
  const [editedDocumentary, setEditedDocumentary] = useState(documentary);
  const videoRef = useRef<HTMLVideoElement>(null);
  const firstFrameLoadedRef = useRef(false);

  // Update edited documentary when documentary prop changes
  useEffect(() => {
    setEditedDocumentary(documentary);
  }, [documentary]);

  // Format time in MM:SS format
  const formatTime = (seconds: number): string => {
    if (!isFinite(seconds) || isNaN(seconds)) return '00:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Determine which video to use (priority: full_video > intro_url)
  const videoUrl = documentary?.full_video || documentary?.intro_url;
  const isFullVideo = !!documentary?.full_video;
  const hasVideo = !!videoUrl;

  // Debug logging
  console.log('DocumentaryPlayer Debug:', {
    documentary,
    videoUrl,
    isFullVideo,
    hasVideo
  });

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);
    const handleLoadStart = () => {
      setIsLoading(true);
      setHasError(false);
      console.log('Video loading started:', videoUrl);
    };
    const handleCanPlay = () => {
      setIsLoading(false);
      console.log('Video can play:', videoUrl);
    };
    const handleError = (e: Event) => {
      setIsLoading(false);
      setHasError(true);
      console.error('Video error:', e, videoUrl);
    };
    const handleLoadedData = () => {
      console.log('Video loaded successfully:', videoUrl);
    };
    const handleTimeUpdate = () => {
      setCurrentTime(video.currentTime);
    };
    const handleDurationChange = () => {
      setDuration(video.duration);
    };

    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);
    video.addEventListener('loadstart', handleLoadStart);
    video.addEventListener('canplay', handleCanPlay);
    video.addEventListener('error', handleError);
    video.addEventListener('loadeddata', handleLoadedData);
    video.addEventListener('timeupdate', handleTimeUpdate);
    video.addEventListener('durationchange', handleDurationChange);

    return () => {
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
      video.removeEventListener('loadstart', handleLoadStart);
      video.removeEventListener('canplay', handleCanPlay);
      video.removeEventListener('error', handleError);
      video.removeEventListener('loadeddata', handleLoadedData);
      video.removeEventListener('timeupdate', handleTimeUpdate);
      video.removeEventListener('durationchange', handleDurationChange);
    };
  }, [videoUrl]);

  // Load first frame for preview
  useEffect(() => {
    const video = videoRef.current;
    if (!video || !videoUrl) return;

    // Reset the flag when video URL changes
    firstFrameLoadedRef.current = false;

    console.log('Setting up first frame preview for:', videoUrl);

    // Force video to load immediately
    video.load();

    const handleFirstFrame = async () => {
      // Only run this once per video load
      if (firstFrameLoadedRef.current) return;
      
      console.log('First frame event fired. Current time:', video.currentTime, 'Ready state:', video.readyState);
      
      if (video.readyState >= 2) {
        firstFrameLoadedRef.current = true;
        
        try {
          // We must mute to be allowed to play without user interaction
          video.muted = true;
          // Play briefly to trigger the rendering pipeline
          await video.play();
          video.pause();
          // Reset to beginning (0.85s to avoid potential black frame at exactly 0)
          video.currentTime = 0.85;
          // Unmute so user hears sound when they manually play
          video.muted = false;
          console.log('Played and paused (muted) to show first frame');
        } catch (error) {
          console.log('Frame preview error:', error);
          firstFrameLoadedRef.current = false; // Allow retry if it failed
        }
      }
    };

    // Try multiple events to ensure we catch when the frame is ready
    video.addEventListener('loadeddata', handleFirstFrame);
    video.addEventListener('canplay', handleFirstFrame);

    return () => {
      video.removeEventListener('loadeddata', handleFirstFrame);
      video.removeEventListener('canplay', handleFirstFrame);
    };
  }, [videoUrl]);

  const handlePlayPause = () => {
    if (!videoRef.current) return;
    
    if (isPlaying) {
      videoRef.current.pause();
    } else {
      videoRef.current.play();
    }
  };

  const handleMouseEnter = () => {
    setIsHovered(true);
    setShowOverlay(true);
  };

  const handleMouseLeave = () => {
    setIsHovered(false);
    // Keep overlay visible for a short time after mouse leaves
    setTimeout(() => setShowOverlay(false), 2000);
  };

  const handleGenerateAction = () => {
    // Open the edit modal at parent level to allow users to configure the documentary
    if (onEditDocumentary) {
      onEditDocumentary();
    }
  };

  const handleGenerate = (settings: VideoSettings) => {
    console.log('Generating video with settings:', settings);
    console.log('Documentary data:', editedDocumentary);
    
    // Close the generation modal
    setShowGenerationModal(false);
    
    // TODO: Call backend API to generate video
    // For now, call the appropriate callback
    if (isFullVideo && onRegenerateVideo) {
      onRegenerateVideo();
    } else if (onGenerateVideo) {
      onGenerateVideo();
    }
  };

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!videoRef.current) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const percentage = clickX / rect.width;
    const newTime = percentage * duration;
    videoRef.current.currentTime = newTime;
  };

  const handleFullscreen = () => {
    if (!videoRef.current) return;
    if (videoRef.current.requestFullscreen) {
      videoRef.current.requestFullscreen();
    }
  };

  const progressPercentage = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <>
      {/* Generation Settings Modal */}
      <VideoGenerationModal
        isOpen={showGenerationModal}
        onClose={() => setShowGenerationModal(false)}
        documentary={editedDocumentary}
        onGenerate={handleGenerate}
      />

      <div 
        className="documentary-player"
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {hasVideo ? (
          <div className="video-container">
            <video
              ref={videoRef}
              className="documentary-video"
              src={videoUrl}
              crossOrigin="anonymous"
              preload="auto"
              controls={false}
              playsInline
            >
              Your browser does not support the video tag.
            </video>

            {/* Loading State */}
            {isLoading && (
              <div className="video-loading">
                <div className="loading-spinner"></div>
                <p>Loading video...</p>
              </div>
            )}

            {/* Error State */}
            {hasError && (
              <div className="video-error">
                <div className="error-icon">⚠️</div>
                <p>Failed to load video</p>
                <button 
                  className="retry-btn"
                  onClick={() => {
                    setHasError(false);
                    if (videoRef.current) {
                      videoRef.current.load();
                    }
                  }}
                >
                  Retry
                </button>
              </div>
            )}

            <AnimatePresence>
              {(showOverlay || isHovered) && !isLoading && !hasError && (
                <motion.div
                  className="video-overlay"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.3 }}
                >
                  <div className="overlay-content">
                    {/* Main Play/Pause Button */}
                    <button
                      className="play-pause-btn"
                      onClick={handlePlayPause}
                    >
                      <div className={`play-icon ${isPlaying ? 'pause' : 'play'}`}>
                        {isPlaying ? (
                          <div className="pause-bars">
                            <span></span>
                            <span></span>
                          </div>
                        ) : (
                          <div className="play-triangle"></div>
                        )}
                      </div>
                    </button>

                    {/* Control Bar */}
                    <div className="control-bar">
                      <div className="control-left">
                        <button
                          className="control-btn play-pause-small"
                          onClick={handlePlayPause}
                        >
                          {isPlaying ? '⏸️' : '▶️'}
                        </button>
                      </div>

                      <div className="control-center">
                        <div className="progress-container" onClick={handleProgressClick}>
                          <div className="progress-bar">
                            <div 
                              className="progress-fill" 
                              style={{ width: `${progressPercentage}%` }}
                            ></div>
                          </div>
                        </div>
                      </div>

                      <div className="control-right">
                        {/* Player Timer */}
                        <div className="time-display">
                          {formatTime(currentTime)} / {formatTime(duration)}
                        </div>
                        <button
                          className="control-btn fullscreen-btn"
                          onClick={handleFullscreen}
                          title="Fullscreen"
                        >
                          ⛶
                        </button>
                        <motion.button
                          className="generate-btn"
                          onClick={handleGenerateAction}
                          whileHover={{ scale: 1.05 }}
                          whileTap={{ scale: 0.95 }}
                        >
                          <span className="btn-icon">🎬</span>
                          {isFullVideo ? 'Regenerate Documentary' : 'Generate Full Documentary'}
                        </motion.button>
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        ) : (
          // Empty state when no video is available
          <div className="empty-player">
            <div className="empty-content">
              <motion.div
                className="empty-icon"
                animate={{ 
                  scale: [1, 1.1, 1],
                  rotate: [0, 5, -5, 0]
                }}
                transition={{ 
                  duration: 3,
                  repeat: Infinity,
                  ease: "easeInOut"
                }}
              >
                🎬
              </motion.div>
              
              <h3 className="empty-title">Documentary Awaits</h3>
              <p className="empty-subtitle">Create your cinematic story</p>
              
              <motion.button
                className="generate-video-btn"
                onClick={onGenerateVideo}
                whileHover={{ 
                  scale: 1.05,
                  boxShadow: "0 0 30px rgba(255, 255, 255, 0.3)"
                }}
                whileTap={{ scale: 0.95 }}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
              >
                <span className="btn-text">Generate Documentary Video</span>
                <div className="btn-glow"></div>
              </motion.button>
            </div>
            
            {/* Animated background elements */}
            <div className="empty-bg-elements">
              {[...Array(5)].map((_, i) => (
                <motion.div
                  key={i}
                  className="bg-particle"
                  animate={{
                    x: [0, 100, 0],
                    y: [0, -50, 0],
                    opacity: [0.1, 0.3, 0.1]
                  }}
                  transition={{
                    duration: 4 + i,
                    repeat: Infinity,
                    delay: i * 0.8
                  }}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default DocumentaryPlayer;
