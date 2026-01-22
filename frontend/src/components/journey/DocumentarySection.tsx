import React from 'react';
import { motion } from 'framer-motion';
import './DocumentarySection.css';

interface DocumentarySectionProps {
  documentary: any;
  profile: any;
  sectionIndex: number;
}

const DocumentarySection: React.FC<DocumentarySectionProps> = ({ documentary, profile, sectionIndex }) => {
  const segments = documentary?.segments || [];
  
  // Debug logging to help troubleshoot
  React.useEffect(() => {
    console.log('Documentary data in DocumentarySection:', {
      hasDocumentary: !!documentary,
      title: documentary?.title,
      tagline: documentary?.tagline,
      segmentsLength: segments.length,
      firstSegment: segments[0]
    });
  }, [documentary, segments]);

  return (
    <section className="journey-section documentary-section" data-section={sectionIndex}>
      <div className="section-container">
        {/* Closing Statement */}
        {documentary.closing_statement && (
          <motion.div
            className="documentary-closing glass"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.6 }}
          >
            <div className="closing-icon">
              <svg viewBox="0 0 24 24" fill="none" width="48" height="48">
                <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" fill="currentColor"/>
              </svg>
            </div>
            <h4 className="closing-title">The Journey Continues...</h4>
            <p className="closing-statement">{documentary.closing_statement}</p>
          </motion.div>
        )}

        {/* Footer */}
        <motion.footer
          className="journey-footer"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 1 }}
        >
          <div className="footer-content">
            <p>Regenerated with ❤️ by <span className="gradient-text">reGen</span></p>
            {profile?.name && (
              <p className="footer-name">© {new Date().getFullYear()} {profile.name}</p>
            )}
          </div>
        </motion.footer>
      </div>
    </section>
  );
};

export default DocumentarySection;
