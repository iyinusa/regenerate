import { motion } from 'framer-motion';
import { useState, useEffect } from 'react';
import SectionDataEditor from './SectionDataEditor';
import { certificationsConfig } from './sectionEditorConfig';
import './CertificationsSection.css';

interface CertificationsSectionProps {
  certifications: any[];
  journey?: any;
  sectionIndex: number;
  historyId?: string;
  onRequestEdit?: (action: string, callback: () => void) => void;
}

const CertificationsSection: React.FC<CertificationsSectionProps> = ({ 
  certifications: initialCertifications,
  sectionIndex,
  historyId,
  onRequestEdit 
}) => {
  const [certifications, setCertifications] = useState(initialCertifications || []);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  useEffect(() => {
    setCertifications(initialCertifications || []);
  }, [initialCertifications]);

  const handleOpenEditModal = () => {
    const openModal = () => setIsEditModalOpen(true);
    if (onRequestEdit) {
      onRequestEdit('edit certifications', openModal);
    } else {
      openModal();
    }
  };

  const handleUpdate = (updatedItems: any[]) => {
    setCertifications(updatedItems);
  };

  return (
    <section className="journey-section certifications-section" data-section={sectionIndex}>
      <div className="cert-grid-bg"></div>
      
      <div className="section-container certifications-container">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '1rem', marginBottom: '3rem', position: 'relative', zIndex: 10 }}>
          <motion.h2 
            className="section-title gradient-text"
            style={{ margin: 0 }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            Certifications
          </motion.h2>

          {historyId && (
            <button
              onClick={handleOpenEditModal}
              className="edit-section-btn"
              title="Edit Certifications"
              style={{
                background: 'rgba(255, 215, 0, 0.15)',
                border: '1px solid rgba(255, 215, 0, 0.3)',
                borderRadius: '8px',
                padding: '8px',
                cursor: 'pointer',
                color: '#FFD700',
                zIndex: 20
              }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="m18 2 4 4-5.5 5.5-4-4L18 2z"></path>
                <path d="M11.5 6.5 6 12v4h4l5.5-5.5"></path>
              </svg>
            </button>
          )}
        </div>

        <div className="cert-masonry">
          {certifications.length === 0 ? (
            <div className="empty-state" style={{ textAlign: 'center', color: '#64748b', padding: '2rem' }}>
              No certifications added yet.
            </div>
          ) : (
            certifications.map((cert, index) => (
              <motion.div
                key={index}
                className="cert-card"
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <div className="cert-inner">
                  <div className="cert-badge-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M12 15l-2 5l-9-5.32L12 1l11 13.68L14 20l-2-5z"/>
                    </svg>
                  </div>
                  
                  <h3 className="cert-name">{cert.name}</h3>
                  <div className="cert-issuer">{cert.issuer}</div>
                  
                  {cert.description && (
                    <p style={{ fontSize: '0.85rem', color: '#cbd5e1', marginBottom: '1rem', lineHeight: '1.5' }}>
                      {cert.description}
                    </p>
                  )}

                  <div className="cert-meta">
                    <div className="cert-date">
                      Issued: {cert.date || 'N/A'}
                    </div>
                    {cert.url && (
                      <a href={cert.url} target="_blank" rel="noopener noreferrer" className="cert-link">
                        <span>Verify</span>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                          <polyline points="15 3 21 3 21 9"></polyline>
                          <line x1="10" y1="14" x2="21" y2="3"></line>
                        </svg>
                      </a>
                    )}
                  </div>
                </div>
              </motion.div>
            ))
          )}
        </div>
      </div>

      <SectionDataEditor
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        config={certificationsConfig}
        items={certifications}
        historyId={historyId || ''}
        onItemsUpdate={handleUpdate}
      />
    </section>
  );
};

export default CertificationsSection;
