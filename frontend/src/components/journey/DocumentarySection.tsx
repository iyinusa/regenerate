import { motion } from 'framer-motion';
import './DocumentarySection.css';

interface DocumentarySectionProps {
  documentary: any;
  profile: any;
  sectionIndex: number;
}

const DocumentarySection: React.FC<DocumentarySectionProps> = ({ documentary, profile, sectionIndex }) => {
  const segments = documentary?.segments || [];

  return (
    <section className="journey-section documentary-section" data-section={sectionIndex}>
      <div className="section-container">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          <h2 className="section-title gradient-text">Your Story, Cinematic</h2>
          <p className="section-subtitle">A narrative journey through your professional evolution</p>
        </motion.div>

        {/* Documentary Overview */}
        <motion.div
          className="documentary-overview glass card-glow"
          initial={{ opacity: 0, scale: 0.9 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.2 }}
        >
          {documentary.title && (
            <h3 className="documentary-title gradient-text">{documentary.title}</h3>
          )}
          {documentary.tagline && (
            <p className="documentary-tagline">{documentary.tagline}</p>
          )}
          {documentary.duration_estimate && (
            <div className="documentary-duration">
              <svg viewBox="0 0 24 24" fill="none" width="20" height="20">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
                <path d="M12 6v6l4 2" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
              </svg>
              <span>Estimated Duration: {documentary.duration_estimate}</span>
            </div>
          )}
        </motion.div>

        {/* Documentary Segments */}
        {segments.length > 0 && (
          <motion.div
            className="documentary-segments"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.4 }}
          >
            <h3 className="segments-title gradient-text">Story Segments</h3>
            <div className="segments-timeline">
              {segments.map((segment: any, index: number) => (
                <motion.div
                  key={index}
                  className="segment-card glass"
                  initial={{ opacity: 0, x: -30 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: index * 0.1 }}
                  whileHover={{ scale: 1.02, x: 10 }}
                >
                  <div className="segment-number">
                    <span>{String(index + 1).padStart(2, '0')}</span>
                  </div>
                  
                  <div className="segment-content">
                    <h4 className="segment-title">{segment.title || segment.name}</h4>
                    
                    {segment.duration && (
                      <div className="segment-duration">{segment.duration}s</div>
                    )}
                    
                    {segment.narration && (
                      <div className="segment-narration">
                        <div className="narration-icon">
                          <svg viewBox="0 0 24 24" fill="none" width="16" height="16">
                            <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" fill="currentColor"/>
                            <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" fill="currentColor"/>
                          </svg>
                        </div>
                        <p>{segment.narration}</p>
                      </div>
                    )}
                    
                    {segment.visuals && (
                      <div className="segment-visuals">
                        <strong>Visuals:</strong> {segment.visuals}
                      </div>
                    )}

                    {segment.key_moments && segment.key_moments.length > 0 && (
                      <ul className="segment-moments">
                        {segment.key_moments.map((moment: string, i: number) => (
                          <li key={i}>{moment}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Closing Statement */}
        {documentary.closing_statement && (
          <motion.div
            className="documentary-closing glass card-glow"
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

        {/* Video Generation CTA */}
        <motion.div
          className="video-cta"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.8 }}
        >
          <button className="generate-video-btn glass card-glow">
            <svg viewBox="0 0 24 24" fill="none" width="24" height="24">
              <path d="M8 5v14l11-7z" fill="currentColor"/>
            </svg>
            <span>Generate Documentary Video</span>
          </button>
          <p className="video-note">
            <svg viewBox="0 0 24 24" fill="none" width="16" height="16">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
              <path d="M12 8v4M12 16h.01" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            Powered by Gemini Veo 3.1 for AI-generated video content
          </p>
        </motion.div>

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
