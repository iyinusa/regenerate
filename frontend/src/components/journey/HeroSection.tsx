import React from 'react';
import { motion, useScroll, useTransform, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
import './HeroSection.css';
import DocumentaryPlayer from './DocumentaryPlayer';
import DocumentaryEditModal from './DocumentaryEditModal';
import PassportEditModal from './PassportEditModal';
import VideoGenerationModal, { VideoSettings } from './VideoGenerationModal';
import { apiClient } from '@/lib/api';

const DEFAULT_AVATAR = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23cccccc'%3E%3Cpath d='M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z'/%3E%3C/svg%3E";

interface HeroSectionProps {
  profile: any;
  documentary: any;
  journey: any;
  introVideo?: string | null;
  fullVideo?: string | null;
  sectionIndex: number;
  historyId?: string;
  canEdit?: boolean;
  onDocumentaryUpdate?: (updatedDocumentary: any) => void;
  onProfileUpdate?: (updatedProfile: any) => void;
  onGenerateVideo?: () => void;
  onRegenerateVideo?: () => void;
  onRequestEdit?: (action: string, callback: () => void) => void;
}

const HeroSection: React.FC<HeroSectionProps> = ({
  profile,
  documentary,
  journey,
  introVideo,
  fullVideo,
  sectionIndex,
  historyId,
  canEdit = true,
  onDocumentaryUpdate,
  onProfileUpdate,
  onGenerateVideo,
  onRegenerateVideo,
  onRequestEdit
}) => {
  const [showEditModal, setShowEditModal] = useState(false);
  const [showPassportModal, setShowPassportModal] = useState(false);
  const [showPassportView, setShowPassportView] = useState(false);
  const [showGenerationModal, setShowGenerationModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editedDocumentary, setEditedDocumentary] = useState(documentary);
  const [isHoveringPassport, setIsHoveringPassport] = useState(false);

  // Local state for passport from structured_data
  const [localPassport, setLocalPassport] = useState<string | null>(null);

  // Extract passport from structured_data on mount or when profile changes
  React.useEffect(() => {
    // Passport is stored in structured_data at root level, not in profile
    const passportUrl = (profile as any)?._structured_data_passport || profile?.passport;
    setLocalPassport(passportUrl || null);
  }, [profile]);

  const handlePassportUpdate = async (url: string) => {
    if (!historyId) return;
    
    // Optimistic update
    setLocalPassport(url);

    try {
      await apiClient.updateProfilePassport(historyId, url);
      // Notify parent if callback provided
      if (onProfileUpdate) {
        // Update profile with new passport reference
        const updatedProfile = { ...profile, _structured_data_passport: url };
        onProfileUpdate(updatedProfile);
      }
    } catch (err) {
      console.error("Failed to update passport:", err);
      // Revert on error
      const passportUrl = (profile as any)?._structured_data_passport || profile?.passport;
      setLocalPassport(passportUrl || null);
      setError("Failed to update passport photo");
    }
  };
  
  const handlePassportClick = () => {
    if (canEdit) {
      if (onRequestEdit) {
          onRequestEdit('update_passport', () => setShowPassportModal(true));
      } else {
          setShowPassportModal(true); 
      }
    } else {
      setShowPassportView(true);
    }
  };

  const handleSaveDocumentary = async (updatedDocumentary: any) => {
    if (!historyId) {
      console.error('No history ID available for saving documentary');
      setError('Unable to save: No history ID available');
      return;
    }

    console.log('Saving documentary with historyId:', historyId);
    console.log('Documentary data being sent:', updatedDocumentary);

    setLoading(true);
    setError(null);

    try {
      // Save documentary data to backend (similar to other sections)
      const endpoint = `/api/v1/profile/documentary/${historyId}`;
      const result = await apiClient.put(endpoint, updatedDocumentary);
      
      console.log('Documentary save response:', result);

      // Update parent component with new documentary data
      if (onDocumentaryUpdate) {
        onDocumentaryUpdate(updatedDocumentary);
      }

      // Store the edited documentary and close edit modal
      setEditedDocumentary(updatedDocumentary);
      setShowEditModal(false);
      
      // Show video generation modal
      setShowGenerationModal(true);
      
      console.log('Documentary saved successfully');
    } catch (err) {
      console.error('Failed to save documentary:', err);
      setError(err instanceof Error ? err.message : 'Failed to save documentary');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async (settings: VideoSettings) => {
    console.log('Generating video with settings:', settings);
    console.log('Documentary data:', editedDocumentary);
    
    // Close the generation modal
    setShowGenerationModal(false);
    
    if (!historyId) {
      console.error('No history ID available for video generation');
      return;
    }
    
    try {
      const hasFullVideo = !!documentary?.full_video;
      
      const result = await apiClient.generateVideo(historyId, {
        export_format: settings.exportFormat,
        aspect_ratio: settings.aspectRatio,
        first_segment_only: settings.firstSegmentOnly || false
      });
      
      if (result.job_id) {
        console.log('Video generation started:', result);
        
        // Call the appropriate callback based on video availability
        if (hasFullVideo && onRegenerateVideo) {
          onRegenerateVideo();
        } else if (onGenerateVideo) {
          onGenerateVideo();
        }
      }
    } catch (error) {
      console.error('Failed to start video generation:', error);
      // You could show an error notification here
    }
  };
  
  const { scrollY } = useScroll();
  
  // Parallax and fade effects on scroll
  const opacity = useTransform(scrollY, [0, 650], [1, 0.6]);
  const scale = useTransform(scrollY, [0, 650], [1, 0.8]);
  const y = useTransform(scrollY, [0, 650], [0, 50]);

  return (
    <section className="journey-section hero-section" data-section={sectionIndex}>
      <motion.div 
        className="section-container hero-container"
        style={{ opacity, scale, y }}
      >
        {/* Header Row */}
        <div className="hero-header">
          <motion.div 
            className="hero-header-left"
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, ease: "easeOut" }}
          >
            <div className="hero-identity-row">
              <div 
                className="hero-passport" 
                onClick={handlePassportClick}
                onMouseEnter={() => canEdit && setIsHoveringPassport(true)}
                onMouseLeave={() => setIsHoveringPassport(false)}
                style={{ cursor: 'pointer' }}
              >
                <img 
                  src={localPassport || DEFAULT_AVATAR} 
                  alt={profile?.name || "Profile"} 
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = DEFAULT_AVATAR;
                  }}
                />
                
                {/* Edit Overlay */}
                {canEdit && (
                  <AnimatePresence>
                    {isHoveringPassport && (
                      <motion.div 
                        className="passport-overlay"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                      >
                         <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                           <path d="M12 20h9"></path>
                           <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
                         </svg>
                      </motion.div>
                    )}
                  </AnimatePresence>
                )}
              </div>
              <div className="hero-text-content">
                <div className="hero-name gradient-text">
                  {profile?.name || 'Professional Journey'}
                </div>
                <p className="hero-title">
                  {journey?.summary?.headline || profile?.title || 'Innovator | Creator | Leader'}
                </p>
              </div>
            </div>
          </motion.div>

          <motion.div 
            className="hero-header-right"
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
            style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}
          >
             {documentary?.opening_hook && (
              <div className="hero-hook glass quote-style">
                <span className="quote-mark-left">"</span>
                {documentary.opening_hook}
                <span className="quote-mark-right">"</span>
              </div>
            )}
          </motion.div>
        </div>

        {/* Main Grid */}
        <div className="hero-grid">
          {/* Documentary Player */}
          <motion.div 
            className="hero-video-box glass"
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.6, ease: "easeOut" }}
          >
            <DocumentaryPlayer 
              documentary={documentary ? {
                ...documentary,
                intro_url: introVideo,
                full_video: fullVideo
              } : null}
              historyId={historyId}
              canEdit={canEdit}
              onRequestAuth={onRequestEdit}
              onDocumentaryComputed={() => {
                // Refresh the page to load the new documentary
                window.location.reload();
              }}
              onGenerateVideo={() => {
                if (onGenerateVideo) {
                    onGenerateVideo();
                } else {
                    console.log('Generate documentary video');
                }
              }}
              onRegenerateVideo={() => {
                if (onRegenerateVideo) {
                    onRegenerateVideo();
                } else {
                    console.log('Regenerate documentary video');
                }
              }}
            />
          </motion.div>

          {/* Narrative / Bio */}
          <motion.div
            className="hero-narrative-box glass"
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4, ease: "easeOut" }}
          >
            <div className="narrative-content">
              {journey?.summary?.narrative || profile?.bio || profile?.description || 'No narrative available yet.'}
            </div>
          </motion.div>
        </div>

        {/* Error display */}
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {/* Documentary Edit Modal - Now at main window level */}
        <DocumentaryEditModal
          isOpen={showEditModal}
          onClose={() => {
            setShowEditModal(false);
            setError(null);
          }}
          documentary={documentary}
          onSave={handleSaveDocumentary}
          loading={loading}
        />

        {/* Video Generation Modal */}
        <VideoGenerationModal
          isOpen={showGenerationModal}
          onClose={() => setShowGenerationModal(false)}
          documentary={editedDocumentary}
          onGenerate={handleGenerate}
        />

        {/* Passport Edit Modal */}
        <PassportEditModal
          isOpen={showPassportModal}
          onClose={() => setShowPassportModal(false)}
          currentPassport={localPassport}
          onSave={handlePassportUpdate}
        />

        {/* Passport View Modal (Animated Popup) */}
        <AnimatePresence>
          {showPassportView && (
            <div className="modal-overlay" onClick={() => setShowPassportView(false)}>
              <motion.div 
                className="passport-view-content glass"
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.5 }}
                onClick={(e) => e.stopPropagation()}
              >
                  <motion.img 
                    src={localPassport || DEFAULT_AVATAR}
                    alt="Passport View"
                    style={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover' }}
                    layoutId="passport-image" 
                  />
              </motion.div>
            </div>
          )}
        </AnimatePresence>

        {/* Scroll Indicator */}
        <motion.div 
          className="scroll-indicator"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 1, delay: 1 }}
        >
          <div className="scroll-icon">
            <div className="scroll-wheel"></div>
          </div>
          <p>SCROLL TO EXPLORE</p>
        </motion.div>
      </motion.div>
    </section>
  );
};

export default HeroSection;
