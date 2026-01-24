import { motion, useScroll, useTransform } from 'framer-motion';
import { useState } from 'react';
import './HeroSection.css';
import DocumentaryPlayer from './DocumentaryPlayer';
import DocumentaryEditModal from './DocumentaryEditModal';
import VideoGenerationModal, { VideoSettings } from './VideoGenerationModal';

interface HeroSectionProps {
  profile: any;
  documentary: any;
  journey: any;
  introVideo?: string | null;
  fullVideo?: string | null;
  sectionIndex: number;
  historyId?: string;
  onDocumentaryUpdate?: (updatedDocumentary: any) => void;
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
  onDocumentaryUpdate,
  onGenerateVideo,
  onRegenerateVideo,
  onRequestEdit
}) => {
  const [showEditModal, setShowEditModal] = useState(false);
  const [showGenerationModal, setShowGenerationModal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editedDocumentary, setEditedDocumentary] = useState(documentary);
  
  const handleEditDocumentary = () => {
    if (onRequestEdit) {
      onRequestEdit('edit documentary', () => setShowEditModal(true));
    } else {
      setShowEditModal(true);
    }
  };

  const handleSaveDocumentary = async (updatedDocumentary: any) => {
    if (!historyId) {
      console.error('No history ID available for saving documentary');
      setError('Unable to save: No history ID available');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Save documentary data to backend (similar to other sections)
      const endpoint = `/api/v1/profile/documentary/${historyId}`;
      const response = await fetch(endpoint, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedDocumentary)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save documentary');
      }

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

  const handleGenerate = (settings: VideoSettings) => {
    console.log('Generating video with settings:', settings);
    console.log('Documentary data:', editedDocumentary);
    
    // Close the generation modal
    setShowGenerationModal(false);
    
    // TODO: Call backend API to generate video
    // For now, call the appropriate callback based on video availability
    const hasFullVideo = !!documentary?.full_video;
    
    if (hasFullVideo && onRegenerateVideo) {
      onRegenerateVideo();
    } else if (onGenerateVideo) {
      onGenerateVideo();
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
            <div className="hero-name gradient-text">
              {profile?.name || 'Professional Journey'}
            </div>
            <p className="hero-title">
              {journey?.summary?.headline || profile?.title || 'Innovator | Creator | Leader'}
            </p>
          </motion.div>

          <motion.div 
            className="hero-header-right"
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.2, ease: "easeOut" }}
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

          {/* Documentary Player */}
          <motion.div 
            className="hero-video-box glass"
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.6, ease: "easeOut" }}
          >
            <DocumentaryPlayer 
              documentary={{
                ...documentary,
                intro_url: introVideo,
                full_video: fullVideo
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
              onEditDocumentary={handleEditDocumentary}
            />
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
