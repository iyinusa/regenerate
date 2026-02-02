import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './VideoGenerationModal.css';

interface VideoGenerationModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentary: {
    title?: string;
    segments?: any[];
  };
  onGenerate: (settings: VideoSettings) => void;
}

export interface VideoSettings {
  exportFormat: '720p' | '1080p' | '4k';
  aspectRatio: '9:16' | '16:9';
  firstSegmentOnly?: boolean;
}

const VideoGenerationModal: React.FC<VideoGenerationModalProps> = ({
  isOpen,
  onClose,
  // documentary,
  onGenerate
}) => {
  const [exportFormat, setExportFormat] = useState<'720p' | '1080p' | '4k'>('720p');
  const [aspectRatio, setAspectRatio] = useState<'9:16' | '16:9'>('16:9');
  const [firstSegmentOnly, setFirstSegmentOnly] = useState(false);

  const handleGenerate = () => {
    onGenerate({ exportFormat, aspectRatio, firstSegmentOnly });
  };

  const getResolutionDetails = (format: string) => {
    switch (format) {
      case '720p':
        return { resolution: '1280×720', bitrate: '~5 Mbps', size: '~150 MB' };
      case '1080p':
        return { resolution: '1920×1080', bitrate: '~8 Mbps', size: '~250 MB' };
      case '4k':
        return { resolution: '3840×2160', bitrate: '~45 Mbps', size: '~1.5 GB' };
      default:
        return { resolution: '', bitrate: '', size: '' };
    }
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="modal-backdrop" onClick={onClose}>
        <motion.div
          className="video-generation-modal glass-morphism"
          onClick={(e) => e.stopPropagation()}
          initial={{ opacity: 0, scale: 0.9, y: 50 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 50 }}
          transition={{ type: "spring", duration: 0.5 }}
        >
          {/* Modal Header */}
          <div className="modal-header">
            <div className="header-content">
              <div className="header-icon">
                <motion.div
                  animate={{
                    rotate: [0, 360],
                    scale: [1, 1.2, 1]
                  }}
                  transition={{
                    duration: 3,
                    repeat: Infinity,
                    ease: "linear"
                  }}
                >
                  🎬
                </motion.div>
              </div>
              <p className="modal-subtitle">Configure your video export settings</p>
            </div>
            <button className="close-btn" onClick={onClose} aria-label="Close">
              <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Settings Section */}
          <div className="settings-section">
            {/* Export Format */}
            <div className="setting-group">
              <h4 className="setting-title">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor">
                  <rect x="2" y="3" width="20" height="14" rx="2" strokeWidth={2} />
                  <path d="M8 21h8M12 17v4" strokeWidth={2} strokeLinecap="round" />
                </svg>
                Export Format
              </h4>
              <div className="format-options">
                {(['720p', '1080p', '4k'] as const).map((format) => (
                  <motion.button
                    key={format}
                    className={`format-option ${exportFormat === format ? 'active' : ''}`}
                    onClick={() => setExportFormat(format)}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <div className="format-badge">{format}</div>
                    <div className="format-details">
                      <span>{getResolutionDetails(format).resolution}</span>
                    </div>
                    {exportFormat === format && (
                      <motion.div
                        className="checkmark"
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ type: "spring" }}
                      >
                        ✓
                      </motion.div>
                    )}
                  </motion.button>
                ))}
              </div>
            </div>

            {/* Aspect Ratio */}
            <div className="setting-group">
              <h4 className="setting-title">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor">
                  <rect x="3" y="3" width="18" height="18" rx="2" strokeWidth={2} />
                  <path d="M9 3v18M15 3v18M3 9h18M3 15h18" strokeWidth={2} strokeLinecap="round" />
                </svg>
                Aspect Ratio
              </h4>
              <div className="aspect-ratio-options">
                <motion.button
                  className={`aspect-option ${aspectRatio === '16:9' ? 'active' : ''}`}
                  onClick={() => setAspectRatio('16:9')}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <div className="aspect-preview landscape">
                    <div className="preview-box"></div>
                  </div>
                  <div className="aspect-label">
                    <strong>16:9</strong>
                    <span>Landscape (YouTube, Desktop)</span>
                  </div>
                  {aspectRatio === '16:9' && (
                    <motion.div
                      className="checkmark"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: "spring" }}
                    >
                      ✓
                    </motion.div>
                  )}
                </motion.button>

                <motion.button
                  className={`aspect-option ${aspectRatio === '9:16' ? 'active' : ''}`}
                  onClick={() => setAspectRatio('9:16')}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  <div className="aspect-preview portrait">
                    <div className="preview-box"></div>
                  </div>
                  <div className="aspect-label">
                    <strong>9:16</strong>
                    <span>Portrait (TikTok, Instagram)</span>
                  </div>
                  {aspectRatio === '9:16' && (
                    <motion.div
                      className="checkmark"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: "spring" }}
                    >
                      ✓
                    </motion.div>
                  )}
                </motion.button>
              </div>
            </div>

            {/* Generation Options */}
            <div className="setting-group">
              <h4 className="setting-title">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor">
                  <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" strokeWidth={2} strokeLinecap="round" />
                </svg>
                Generation Mode
              </h4>
              <div className="generation-options">
                <motion.button
                  className={`generation-option ${!firstSegmentOnly ? 'active' : ''}`}
                  onClick={() => setFirstSegmentOnly(false)}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div className="option-icon">🎬</div>
                  <div className="option-details">
                    <strong>Full Documentary</strong>
                    <span>Generate all segments (longer processing)</span>
                  </div>
                  {!firstSegmentOnly && (
                    <motion.div
                      className="checkmark"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: "spring" }}
                    >
                      ✓
                    </motion.div>
                  )}
                </motion.button>

                <motion.button
                  className={`generation-option ${firstSegmentOnly ? 'active' : ''}`}
                  onClick={() => setFirstSegmentOnly(true)}
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div className="option-icon">⚡</div>
                  <div className="option-details">
                    <strong>First Segment Preview</strong>
                    <span>Quick generation for preview (8 seconds)</span>
                  </div>
                  {firstSegmentOnly && (
                    <motion.div
                      className="checkmark"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: "spring" }}
                    >
                      ✓
                    </motion.div>
                  )}
                </motion.button>
              </div>
            </div>
          </div>

          {/* Modal Footer */}
          <div className="modal-footer">
            <button className="secondary-btn" onClick={onClose}>
              Cancel
            </button>
            <motion.button
              className="primary-btn btn-generate"
              onClick={handleGenerate}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                <path d="M8 5v14l11-7z" />
              </svg>
              Generate Documentary
              <div className="btn-glow"></div>
            </motion.button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default VideoGenerationModal;
