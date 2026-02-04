import React, { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './DocumentaryPlayer.css';
import VideoGenerationModal, { VideoSettings } from './VideoGenerationModal';
import DocumentaryEditModal from './DocumentaryEditModal';
import { useAuth } from '@/hooks/useAuth';
import { apiClient } from '@/lib/api.ts';

interface DocumentaryPlayerProps {
  documentary: {
    intro_url?: string;
    full_video?: string;
    title?: string;
    tagline?: string;
    segments?: any[];
  };
  canEdit?: boolean;
  onGenerateVideo?: () => void;
  onRegenerateVideo?: () => void;
  historyId?: string; // Add historyId prop for video generation
  onRequestAuth?: (action: string, callback: () => void) => void;
}

interface VideoGenerationStatus {
  jobId: string;
  status: 'processing' | 'completed' | 'failed';
  progress: number;
  message: string;
  error?: string;
}

interface ErrorMessage {
  id: string;
  message: string;
  timestamp: number;
}

const DocumentaryPlayer: React.FC<DocumentaryPlayerProps> = ({
  documentary,
  canEdit = true,
  onGenerateVideo,
  onRegenerateVideo,
  historyId,
  onRequestAuth
}) => {
  const { isAuthenticated } = useAuth();
  const [isHovered, setIsHovered] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [showOverlay, setShowOverlay] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [showGenerationModal, setShowGenerationModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editedDocumentary, setEditedDocumentary] = useState(documentary);
  
  // Video generation status tracking
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationStatus, setGenerationStatus] = useState<VideoGenerationStatus | null>(null);
  const [errorMessages, setErrorMessages] = useState<ErrorMessage[]>([]);
  
  const videoRef = useRef<HTMLVideoElement>(null);
  const firstFrameLoadedRef = useRef(false);
  const wsRef = useRef<WebSocket | null>(null);
  const errorTimeoutRefs = useRef<Map<string, number>>(new Map());

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

  // Add error message with auto-dismiss
  const addErrorMessage = useCallback((message: string) => {
    const id = `error_${Date.now()}`;
    const newError: ErrorMessage = {
      id,
      message,
      timestamp: Date.now()
    };
    
    setErrorMessages(prev => [...prev, newError]);
    
    // Auto-dismiss after 10 seconds
    const timeoutId = setTimeout(() => {
      removeErrorMessage(id);
    }, 10000) as unknown as number;
    
    errorTimeoutRefs.current.set(id, timeoutId);
  }, []);

  // Remove error message
  const removeErrorMessage = useCallback((id: string) => {
    setErrorMessages(prev => prev.filter(error => error.id !== id));
    
    // Clear timeout if exists
    const timeoutId = errorTimeoutRefs.current.get(id);
    if (timeoutId) {
      clearTimeout(timeoutId);
      errorTimeoutRefs.current.delete(id);
    }
  }, []);

  // Connect to WebSocket for video generation updates
  const connectVideoGenerationWebSocket = useCallback((jobId: string) => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    try {
      const ws = new WebSocket(apiClient.getWebSocketUrl(jobId));
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('Video generation WebSocket connected');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleVideoGenerationUpdate(data);
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      ws.onclose = () => {
        console.log('Video generation WebSocket disconnected');
      };

      ws.onerror = (error) => {
        console.error('Video generation WebSocket error:', error);
        addErrorMessage('Connection error during video generation');
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      addErrorMessage('Failed to establish real-time connection');
    }
  }, [addErrorMessage]);

  // Handle video generation status updates
  const handleVideoGenerationUpdate = useCallback((data: any) => {
    console.log('Video generation update:', data);

    if (data.event === 'task_started' || data.event === 'task_progress') {
      if (data.task?.task_type === 'generate_video') {
        setGenerationStatus({
          jobId: data.job_id,
          status: 'processing',
          progress: data.task.progress || 0,
          message: data.task.message || 'Generating video...'
        });
      }
    } else if (data.event === 'task_completed') {
      if (data.task?.task_type === 'generate_video') {
        setGenerationStatus({
          jobId: data.job_id,
          status: 'completed',
          progress: 100,
          message: 'Video generation completed!'
        });
        
        // Stop generating state after a short delay
        setTimeout(() => {
          setIsGenerating(false);
          setGenerationStatus(null);
          
          // Call the appropriate callback based on whether this was a regeneration
          if (isFullVideo && onRegenerateVideo) {
            onRegenerateVideo();
          } else if (onGenerateVideo) {
            onGenerateVideo();
          }
        }, 2000);
      }
    } else if (data.event === 'task_failed') {
      if (data.task?.task_type === 'generate_video') {
        const errorMsg = data.task?.error || 'Video generation failed';
        setGenerationStatus({
          jobId: data.job_id,
          status: 'failed',
          progress: 0,
          message: 'Generation failed',
          error: errorMsg
        });
        
        addErrorMessage(errorMsg);
        
        // Stop generating state
        setTimeout(() => {
          setIsGenerating(false);
          setGenerationStatus(null);
        }, 3000);
      }
    }
  }, [addErrorMessage, onGenerateVideo]);

  // Cleanup WebSocket and timeouts on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      
      // Clear all error timeouts
      errorTimeoutRefs.current.forEach(timeoutId => {
        clearTimeout(timeoutId);
      });
      errorTimeoutRefs.current.clear();
    };
  }, []);

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
    if (!isAuthenticated) {
      if (onRequestAuth) {
        onRequestAuth('generate video', () => {
             setShowEditModal(true);
        });
      }
      return;
    }
    // Open the edit modal first to allow modifications
    setShowEditModal(true);
  };

  const handleEditSave = async (updatedDoc: any) => {
    console.log('Documentary updated:', updatedDoc);
    
    if (!historyId) {
      addErrorMessage('No history ID available for saving documentary');
      return;
    }

    try {
      // Save documentary to database
      console.log('Saving documentary to database...', updatedDoc);
      const endpoint = `/api/v1/profile/documentary/${historyId}`;
      const result = await apiClient.put(endpoint, updatedDoc);
      
      console.log('Documentary saved successfully:', result);
      
      // Update local state
      setEditedDocumentary(updatedDoc);
      setShowEditModal(false);
      
      // After saving, open the generation settings modal
      setShowGenerationModal(true);
    } catch (error) {
      console.error('Failed to save documentary:', error);
      const errorMsg = error instanceof Error ? error.message : 'Failed to save documentary';
      addErrorMessage(errorMsg);
    }
  };

  const handleGenerate = async (settings: VideoSettings) => {
    if (!historyId) {
      addErrorMessage('No history ID available for video generation');
      return;
    }

    console.log('Generating video with settings:', settings);
    console.log('Documentary data:', editedDocumentary);
    
    // Close the generation modal
    setShowGenerationModal(false);
    
    try {
      // Start generating state
      setIsGenerating(true);
      setGenerationStatus({
        jobId: 'starting',
        status: 'processing',
        progress: 0,
        message: 'Starting video generation...'
      });

      // Call backend API to generate video
      const result = await apiClient.generateVideo(historyId, {
        export_format: settings.exportFormat,
        aspect_ratio: settings.aspectRatio,
        first_segment_only: settings.firstSegmentOnly || false
      });
      
      if (result.job_id) {
        console.log('Video generation started:', result);
        
        // Connect to WebSocket for real-time updates
        connectVideoGenerationWebSocket(result.job_id);
        
        setGenerationStatus({
          jobId: result.job_id,
          status: 'processing',
          progress: 5,
          message: result.message || 'Video generation in progress...'
        });
      } else {
        throw new Error('Failed to get job ID from video generation request');
      }
    } catch (error) {
      console.error('Failed to start video generation:', error);
      const errorMsg = error instanceof Error ? error.message : 'Failed to start video generation';
      addErrorMessage(errorMsg);
      
      // Reset generating state
      setIsGenerating(false);
      setGenerationStatus(null);
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
      <DocumentaryEditModal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        documentary={editedDocumentary}
        onSave={handleEditSave}
      />

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

            {/* Video Generation Blur Overlay */}
            <AnimatePresence>
              {isGenerating && (
                <motion.div
                  className="video-generation-overlay"
                  initial={{ opacity: 0, backdropFilter: 'blur(0px)' }}
                  animate={{ opacity: 1, backdropFilter: 'blur(10px)' }}
                  exit={{ opacity: 0, backdropFilter: 'blur(0px)' }}
                  transition={{ duration: 0.5 }}
                >
                  <div className="generation-status">
                    <motion.div
                      className="generation-icon"
                      animate={{ 
                        rotate: [0, 360],
                        scale: [1, 1.1, 1]
                      }}
                      transition={{
                        duration: 2,
                        repeat: Infinity,
                        ease: "linear"
                      }}
                    >
                      🎬
                    </motion.div>
                    
                    <div className="generation-info">
                      <h3 className="generation-title">Generating Your Documentary</h3>
                      <p className="generation-message">
                        {generationStatus?.message || 'Creating cinematic experience...'}
                      </p>
                      
                      {/* Progress Bar */}
                      <div className="generation-progress">
                        <div className="progress-track">
                          <motion.div
                            className="progress-fill"
                            initial={{ width: '0%' }}
                            animate={{ width: `${generationStatus?.progress || 0}%` }}
                            transition={{ duration: 0.5, ease: 'easeOut' }}
                          />
                        </div>
                        <span className="progress-text">
                          {generationStatus?.progress || 0}%
                        </span>
                      </div>
                      
                      {/* Animated Dots */}
                      <div className="generation-dots">
                        {[...Array(3)].map((_, i) => (
                          <motion.div
                            key={i}
                            className="dot"
                            animate={{
                              scale: [1, 1.5, 1],
                              opacity: [0.3, 1, 0.3]
                            }}
                            transition={{
                              duration: 1.5,
                              repeat: Infinity,
                              delay: i * 0.2
                            }}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Error Messages */}
            <AnimatePresence>
              {errorMessages.map((error) => (
                <motion.div
                  key={error.id}
                  className="video-error-message"
                  initial={{ opacity: 0, y: -30, scale: 0.9 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -30, scale: 0.9 }}
                  transition={{ duration: 0.3, ease: "easeOut" }}
                >
                  <div className="error-content">
                    <span className="error-icon">⚠️</span>
                    <span className="error-text">{error.message}</span>
                    <button
                      className="error-close-btn"
                      onClick={() => removeErrorMessage(error.id)}
                      aria-label="Close error message"
                    >
                      ✕
                    </button>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

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
                          {isPlaying ? '❚❚' : '▶'}
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
                        {historyId && canEdit && (
                          <motion.button
                            className="generate-btn"
                            onClick={handleGenerateAction}
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                          >
                            <span className="btn-icon">🎬</span>
                            {isFullVideo ? 'Regenerate Documentary' : 'Generate Full Documentary'}
                          </motion.button>
                        )}
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
            {/* Video Generation Blur Overlay for empty state */}
            <AnimatePresence>
              {isGenerating && (
                <motion.div
                  className="video-generation-overlay"
                  initial={{ opacity: 0, backdropFilter: 'blur(0px)' }}
                  animate={{ opacity: 1, backdropFilter: 'blur(10px)' }}
                  exit={{ opacity: 0, backdropFilter: 'blur(0px)' }}
                  transition={{ duration: 0.5 }}
                >
                  <div className="generation-status">
                    <motion.div
                      className="generation-icon"
                      animate={{ 
                        rotate: [0, 360],
                        scale: [1, 1.1, 1]
                      }}
                      transition={{
                        duration: 2,
                        repeat: Infinity,
                        ease: "linear"
                      }}
                    >
                      🎬
                    </motion.div>
                    
                    <div className="generation-info">
                      <h3 className="generation-title">Generating Your Documentary</h3>
                      <p className="generation-message">
                        {generationStatus?.message || 'Creating cinematic experience...'}
                      </p>
                      
                      {/* Progress Bar */}
                      <div className="generation-progress">
                        <div className="progress-track">
                          <motion.div
                            className="progress-fill"
                            initial={{ width: '0%' }}
                            animate={{ width: `${generationStatus?.progress || 0}%` }}
                            transition={{ duration: 0.5, ease: 'easeOut' }}
                          />
                        </div>
                        <span className="progress-text">
                          {generationStatus?.progress || 0}%
                        </span>
                      </div>
                      
                      {/* Animated Dots */}
                      <div className="generation-dots">
                        {[...Array(3)].map((_, i) => (
                          <motion.div
                            key={i}
                            className="dot"
                            animate={{
                              scale: [1, 1.5, 1],
                              opacity: [0.3, 1, 0.3]
                            }}
                            transition={{
                              duration: 1.5,
                              repeat: Infinity,
                              delay: i * 0.2
                            }}
                          />
                        ))}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Error Messages for empty state */}
            <AnimatePresence>
              {errorMessages.map((error) => (
                <motion.div
                  key={error.id}
                  className="video-error-message"
                  initial={{ opacity: 0, y: -30, scale: 0.9 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -30, scale: 0.9 }}
                  transition={{ duration: 0.3, ease: "easeOut" }}
                >
                  <div className="error-content">
                    <span className="error-icon">⚠️</span>
                    <span className="error-text">{error.message}</span>
                    <button
                      className="error-close-btn"
                      onClick={() => removeErrorMessage(error.id)}
                      aria-label="Close error message"
                    >
                      ✕
                    </button>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

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
              
              {canEdit && (
                <motion.button
                  className="generate-video-btn"
                  onClick={() => setShowGenerationModal(true)}
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
              )}
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
