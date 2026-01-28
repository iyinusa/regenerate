import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './DocumentaryEditModal.css';

interface DocumentarySegment {
  id?: string;
  order?: number;
  title?: string;
  duration_seconds?: number;
  visual_description?: string;
  narration?: string;
  mood?: string;
  background_music_hint?: string;
  data_visualization?: {
    type?: string;
    data_points?: any[];
  };
}

interface DocumentaryEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentary: {
    title?: string;
    tagline?: string;
    segments?: DocumentarySegment[];
  };
  onSave: (updatedDocumentary: any) => void;
  loading?: boolean;
}

const DocumentaryEditModal: React.FC<DocumentaryEditModalProps> = ({
  isOpen,
  onClose,
  documentary,
  onSave,
  loading = false
}) => {
  const MAX_SEGMENTS = 16;
  const [segments, setSegments] = useState<DocumentarySegment[]>([]);
  const [expandedSegments, setExpandedSegments] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (documentary?.segments) {
      // Initialize with existing segments or create a default one
      const initialSegments = documentary.segments.length > 0 
        ? documentary.segments 
        : [{
            id: '1',
            order: 1,
            title: 'Untitled Segment',
            duration_seconds: 8,
            narration: '',
            mood: 'professional',
            visual_description: '',
            background_music_hint: '',
            data_visualization: undefined
          }];
      setSegments(initialSegments);
    }
  }, [documentary]);

  const handleNarrationChange = (index: number, value: string) => {
    const updatedSegments = [...segments];
    updatedSegments[index] = { ...updatedSegments[index], narration: value };
    setSegments(updatedSegments);
  };

  const handleAdvancedChange = (index: number, field: keyof DocumentarySegment, value: any) => {
    const updatedSegments = [...segments];
    updatedSegments[index] = { ...updatedSegments[index], [field]: value };
    setSegments(updatedSegments);
  };

  const toggleAdvanced = (index: number) => {
    const newExpanded = new Set(expandedSegments);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedSegments(newExpanded);
  };

  const addSegment = () => {
    if (segments.length < MAX_SEGMENTS) {
      const newSegment: DocumentarySegment = {
        id: String(segments.length + 1),
        order: segments.length + 1,
        title: `Segment ${segments.length + 1}`,
        duration_seconds: 8,
        narration: '',
        mood: 'professional',
        visual_description: '',
        background_music_hint: '',
        data_visualization: undefined
      };
      setSegments([...segments, newSegment]);
    }
  };

  const removeSegment = (index: number) => {
    if (segments.length > 1) {
      const updatedSegments = segments.filter((_, i) => i !== index);
      // Re-order segments
      updatedSegments.forEach((seg, idx) => {
        seg.order = idx + 1;
        seg.id = String(idx + 1);
      });
      setSegments(updatedSegments);
      
      // Clean up expanded state
      const newExpanded = new Set<number>();
      expandedSegments.forEach(idx => {
        if (idx < index) newExpanded.add(idx);
        if (idx > index) newExpanded.add(idx - 1);
      });
      setExpandedSegments(newExpanded);
    }
  };

  const handleSave = () => {
    const updatedDocumentary = {
      ...documentary,
      segments
    };
    onSave(updatedDocumentary);
  };

  const calculateTotalDuration = () => {
    return segments.reduce((total, seg) => total + (seg.duration_seconds || 8), 0);
  };

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div className="modal-backdrop" onClick={onClose}>
        <motion.div
          className="documentary-edit-modal"
          onClick={(e) => e.stopPropagation()}
          initial={{ opacity: 0, scale: 0.9, y: 50 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9, y: 50 }}
          transition={{ type: "spring", duration: 0.5 }}
        >
          {/* Modal Header */}
          <div className="modal-header">
            <div className="header-content">
              <h3 className="modal-title gradient-text">{documentary?.title || 'Documentary Editor'}</h3>
              {documentary?.tagline && (
                <p className="modal-tagline">{documentary.tagline}</p>
              )}
            </div>
            <button className="close-btn" onClick={onClose} aria-label="Close">
              <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Segments Info Bar */}
          <div className="segments-info-bar">
            <div className="info-item">
              <span className="info-label">Segments:</span>
              <span className="info-value">{segments.length} / {MAX_SEGMENTS}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Total Duration:</span>
              <span className="info-value">{calculateTotalDuration()}s / 141s</span>
            </div>
            {calculateTotalDuration() > 141 && (
              <div className="info-warning">
                ⚠️ Exceeds Veo limit (141s)
              </div>
            )}
          </div>

          {/* Scrollable Content */}
          <div className="modal-content">
            {segments.map((segment, index) => (
              <motion.div
                key={segment.id || index}
                className="segment-editor glass-card"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
              >
                {/* Segment Header */}
                <div className="segment-header">
                  <div className="segment-number">{String(index + 1).padStart(2, '0')}</div>
                  <div className="segment-title-display">
                    <h3>{segment.title || `Segment ${index + 1}`}</h3>
                    {/* <span className="duration-badge">{segment.duration_seconds || 8}s</span> */}
                  </div>
                  <div className="segment-actions">
                    <button
                      className="icon-btn advanced-btn"
                      onClick={() => toggleAdvanced(index)}
                      title="Advanced settings (Pro)"
                      aria-label="Toggle advanced settings"
                    >
                      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor">
                        <circle cx="12" cy="12" r="3" strokeWidth={2} />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                          d="M12 1v6m0 6v6M5.64 5.64l4.24 4.24m4.24 4.24l4.24 4.24M1 12h6m6 0h6M5.64 18.36l4.24-4.24m4.24-4.24l4.24-4.24" />
                      </svg>
                      {expandedSegments.has(index) && <span className="pro-badge">PRO</span>}
                    </button>
                    {segments.length > 1 && (
                      <button
                        className="icon-btn delete-btn"
                        onClick={() => removeSegment(index)}
                        title="Delete segment"
                        aria-label="Delete segment"
                      >
                        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    )}
                  </div>
                </div>

                {/* Narration Editor */}
                <div className="narration-editor">
                  <label className="editor-label">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                      <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" />
                      <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" />
                    </svg>
                    Narration
                  </label>
                  <textarea
                    className="narration-textarea"
                    value={segment.narration || ''}
                    onChange={(e) => handleNarrationChange(index, e.target.value)}
                    placeholder="Enter voiceover narration for this segment..."
                    rows={4}
                  />
                  <div className="char-count">
                    {(segment.narration || '').length} characters
                  </div>
                </div>

                {/* Advanced Settings */}
                <AnimatePresence>
                  {expandedSegments.has(index) && (
                    <motion.div
                      className="advanced-settings"
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.3 }}
                    >
                      <div className="advanced-header">
                        <span>⚡ Advanced Settings</span>
                        <span className="pro-indicator">PRO</span>
                      </div>

                      <div className="advanced-grid">
                        {/* Mood */}
                        <div className="form-group">
                          <label className="form-label">Mood</label>
                          <select
                            className="form-select"
                            value={segment.mood || 'professional'}
                            onChange={(e) => handleAdvancedChange(index, 'mood', e.target.value)}
                          >
                            <option value="inspirational">Inspirational</option>
                            <option value="professional">Professional</option>
                            <option value="dynamic">Dynamic</option>
                            <option value="reflective">Reflective</option>
                            <option value="triumphant">Triumphant</option>
                          </select>
                        </div>

                        {/* Visual Description */}
                        <div className="form-group full-width">
                          <label className="form-label">Visual Description</label>
                          <textarea
                            className="form-textarea"
                            value={segment.visual_description || ''}
                            onChange={(e) => handleAdvancedChange(index, 'visual_description', e.target.value)}
                            placeholder="Describe what viewers should see..."
                            rows={3}
                          />
                        </div>

                        {/* Background Music Hint */}
                        <div className="form-group full-width">
                          <label className="form-label">Background Music Hint</label>
                          <input
                            type="text"
                            className="form-input"
                            value={segment.background_music_hint || ''}
                            onChange={(e) => handleAdvancedChange(index, 'background_music_hint', e.target.value)}
                            placeholder="e.g., Upbeat electronic, Soft piano..."
                          />
                        </div>

                        {/* Data Visualization */}
                        <div className="form-group full-width">
                          <label className="form-label">Data Visualization Type</label>
                          <select
                            className="form-select"
                            value={segment.data_visualization?.type || ''}
                            onChange={(e) => handleAdvancedChange(index, 'data_visualization', {
                              ...segment.data_visualization,
                              type: e.target.value,
                              data_points: segment.data_visualization?.data_points || []
                            })}
                          >
                            <option value="">None</option>
                            <option value="Timeline Reveal">Timeline Reveal</option>
                            <option value="Metrics Display">Metrics Display</option>
                            <option value="Growth Chart">Growth Chart</option>
                            <option value="Skill Evolution">Skill Evolution</option>
                            <option value="Achievement Showcase">Achievement Showcase</option>
                          </select>
                        </div>

                        {/* Data Points - Only show if data visualization type is selected */}
                        {segment.data_visualization?.type && (
                          <div className="form-group full-width">
                            <label className="form-label">Data Points (one per line)</label>
                            <textarea
                              className="form-textarea"
                              value={(segment.data_visualization?.data_points || []).join('\n')}
                              onChange={(e) => {
                                const dataPoints = e.target.value.split('\n').filter(point => point.trim() !== '');
                                handleAdvancedChange(index, 'data_visualization', {
                                  ...segment.data_visualization,
                                  data_points: dataPoints
                                });
                              }}
                              placeholder={segment.data_visualization.type === 'Timeline Reveal' 
                                ? "2014: Foundation\n2017: Core Mastery\n2020: Leadership Role"
                                : "Key data points for visualization..."}
                              rows={4}
                            />
                            <div className="form-hint">
                              {segment.data_visualization.type === 'Timeline Reveal' 
                                ? "Format: Year: Achievement (e.g., '2014: Foundation')"
                                : "Enter data points for the visualization"}
                            </div>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))}

            {/* Add Segment Button */}
            {segments.length < MAX_SEGMENTS && (
              <motion.button
                className="add-segment-btn"
                onClick={addSegment}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Add Segment ({segments.length}/{MAX_SEGMENTS})
              </motion.button>
            )}
          </div>

          {/* Modal Footer */}
          <div className="modal-footer">
            <button className="secondary-btn" onClick={onClose}>
              Cancel
            </button>
            <button 
              className="primary-btn" 
              onClick={handleSave}
              disabled={calculateTotalDuration() > 141 || loading}
            >
              {loading ? (
                <>
                  <div className="btn-spinner"></div>
                  Saving...
                </>
              ) : (
                <>
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                      d="M5 13l4 4L19 7" />
                  </svg>
                  Save Changes
                </>
              )}
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};

export default DocumentaryEditModal;
