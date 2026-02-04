import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { apiClient } from '@/lib/api';
import './PassportEditModal.css';

interface PassportEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentPassport?: string | null;
  onSave: (url: string) => Promise<void>;
  loading?: boolean;
}

const PassportEditModal: React.FC<PassportEditModalProps> = ({
  isOpen,
  onClose,
  currentPassport,
  onSave,
  loading = false
}) => {
  const [activeTab, setActiveTab] = useState<'upload' | 'url'>('upload');
  const [urlInput, setUrlInput] = useState(currentPassport || '');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(currentPassport || null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  // Reset state when modal opens
  React.useEffect(() => {
    if (isOpen) {
      setUrlInput(currentPassport || '');
      setPreviewUrl(currentPassport || null);
      setSelectedFile(null);
      setError(null);
    }
  }, [isOpen, currentPassport]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (!file.type.startsWith('image/')) {
        setError('Please select an image file');
        return;
      }
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setError(null);
    }
  };

  const handleSave = async () => {
    setError(null);
    
    try {
      if (activeTab === 'upload') {
        if (!selectedFile) {
          // If no new file selected but we have a preview (existing), just close?
          // Or if they want to clear it?
          // For now assume if no file selected, verify if we want to save existing?
          // Actually if no file change, maybe nothing to do unless we removed it.
          if (!previewUrl) {
             // Removing passport?
             // Not supported yet by requirements
             onClose();
             return;
          }
          onClose(); // No change
          return;
        }

        setUploading(true);
        try {
          const result = await apiClient.uploadPassport(selectedFile);
          await onSave(result.url);
        } finally {
          setUploading(false);
        }
      } else {
        // URL mode
        if (!urlInput.trim()) {
           setError("Please enter a URL");
           return;
        }
        await onSave(urlInput);
      }
      onClose();
    } catch (err: any) {
      console.error('Failed to save passport:', err);
      setError(err.message || 'Failed to save passport');
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="modal-overlay" onClick={onClose}>
          <motion.div 
            className="passport-modal-content glass"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            onClick={(e) => e.stopPropagation()}
          >
            <button className="close-btn" onClick={onClose}>&times;</button>
            <h2 className="modal-title">Update Passport Photo</h2>

            <div className="passport-modal-tabs">
              <button 
                className={`passport-tab-button ${activeTab === 'upload' ? 'active' : ''}`}
                onClick={() => setActiveTab('upload')}
              >
                Upload Image
              </button>
              <button 
                className={`passport-tab-button ${activeTab === 'url' ? 'active' : ''}`}
                onClick={() => setActiveTab('url')}
              >
                Image URL
              </button>
            </div>

            <div className="passport-modal-body">
              {previewUrl && (
                <div className="passport-preview-container">
                  <div className="hero-passport" style={{width: '120px', height: '120px'}}>
                    <img src={previewUrl} alt="Preview" style={{width: '100%', height: '100%', objectFit: 'cover'}} />
                  </div>
                </div>
              )}

              {activeTab === 'upload' ? (
                <div className="passport-form-group">
                  <label className="passport-label">Select Image</label>
                  <input 
                    type="file" 
                    accept="image/*"
                    onChange={handleFileChange}
                    className="passport-file-input"
                  />
                  <p className="passport-help-text">JPG, PNG or GIF. Max 5MB.</p>
                </div>
              ) : (
                <div className="passport-form-group">
                  <label className="passport-label">Image URL</label>
                  <input 
                    type="text" 
                    value={urlInput}
                    onChange={(e) => {
                      setUrlInput(e.target.value);
                      setPreviewUrl(e.target.value);
                    }}
                    placeholder="https://example.com/photo.jpg"
                    className="passport-text-input"
                  />
                </div>
              )}

              {error && <div className="passport-error-message">{error}</div>}
            </div>

            <div className="passport-modal-actions">
              <button className="passport-cancel-button" onClick={onClose}>Cancel</button>
              <button 
                className="passport-save-button" 
                onClick={handleSave}
                disabled={loading || uploading}
              >
                {uploading ? 'Uploading...' : loading ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

export default PassportEditModal;
