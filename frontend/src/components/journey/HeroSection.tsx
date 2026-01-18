import { motion, useScroll, useTransform } from 'framer-motion';
import './HeroSection.css';

interface HeroSectionProps {
  profile: any;
  documentary: any;
  journey: any;
  sectionIndex: number;
}

const HeroSection: React.FC<HeroSectionProps> = ({ profile, documentary, journey, sectionIndex }) => {
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
            <h1 className="hero-name gradient-text">
              {profile?.name || 'Professional Journey'}
            </h1>
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

          {/* Video Player Canvas */}
          <motion.div 
            className="hero-video-box glass"
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.6, ease: "easeOut" }}
          >
            <div className="video-canvas-placeholder">
              <span>Documentary Video Player Canvas</span>
            </div>
          </motion.div>
        </div>

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
