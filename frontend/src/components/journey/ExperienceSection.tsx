import { motion } from 'framer-motion';
import { useSpring, animated } from '@react-spring/web';
import { useState, useEffect } from 'react';
import SectionDataEditor from './SectionDataEditor';
import { experiencesConfig } from './sectionEditorConfig';
import './ExperienceSection.css';

interface ExperienceSectionProps {
  experiences: any[];
  journey: any;
  sectionIndex: number;
  historyId?: string; // For editing functionality
}

const ExperienceSection: React.FC<ExperienceSectionProps> = ({ experiences: initialExperiences, journey, sectionIndex, historyId }) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [experiences, setExperiences] = useState(initialExperiences || []);
  const careerChapters = journey?.career_chapters || [];

  // Update local experiences when prop changes
  useEffect(() => {
    setExperiences(initialExperiences || []);
  }, [initialExperiences]);

  // Handler for experiences update from modal
  const handleExperiencesUpdate = (updatedExperiences: any[]) => {
    setExperiences(updatedExperiences);
    // Reset selected index if it's out of bounds
    if (selectedIndex >= updatedExperiences.length) {
      setSelectedIndex(Math.max(0, updatedExperiences.length - 1));
    }
  };

  // Handler to open edit modal
  const handleOpenEditModal = () => {
    console.log('Opening edit modal, experiences:', experiences);
    console.log('Is experiences an array?', Array.isArray(experiences));
    setIsEditModalOpen(true);
  };

  return (
    <section className="journey-section experience-section" data-section={sectionIndex}>
      <div className="section-container">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
            <h2 className="section-title gradient-text" style={{ margin: 0 }}>Professional Experience</h2>
            {historyId && (
              <button
                onClick={handleOpenEditModal}
                className="edit-section-btn"
                title="Edit Professional Experience"
                style={{
                  background: 'rgba(0, 212, 255, 0.15)',
                  border: '1px solid rgba(0, 212, 255, 0.3)',
                  borderRadius: '8px',
                  padding: '8px',
                  cursor: 'pointer',
                  color: '#00d4ff',
                  transition: 'all 0.3s ease',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(0, 212, 255, 0.25)';
                  e.currentTarget.style.transform = 'scale(1.05)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(0, 212, 255, 0.15)';
                  e.currentTarget.style.transform = 'scale(1)';
                }}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="m18 2 4 4-5.5 5.5-4-4L18 2z"></path>
                  <path d="M11.5 6.5 6 12v4h4l5.5-5.5"></path>
                </svg>
              </button>
            )}
          </div>
          <p className="section-subtitle">A chronicle of growth, leadership, and innovation</p>
        </motion.div>

        <div className="experience-layout">
          {/* Experience Timeline Navigation */}
          <motion.div
            className="experience-nav glass"
            initial={{ opacity: 0, x: -30 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            {Array.isArray(experiences) && experiences.map((exp, index) => (
              <button
                key={index}
                className={`exp-nav-item ${selectedIndex === index ? 'active' : ''}`}
                onClick={() => setSelectedIndex(index)}
              >
                <div className="exp-nav-company">{exp.company || exp.organization || `Position ${index + 1}`}</div>
                <div className="exp-nav-duration">{exp.duration || exp.period}</div>
              </button>
            ))}
          </motion.div>

          {/* Experience Details */}
          <motion.div
            className="experience-details"
            key={selectedIndex}
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
          >
            <ExperienceCard experience={experiences[selectedIndex]} />
          </motion.div>
        </div>

        {/* Career Chapters */}
        {careerChapters.length > 0 && (
          <motion.div
            className="career-chapters"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.4 }}
          >
            <h3 className="chapters-title gradient-text">Career Chapters</h3>
            <div className="chapters-grid">
              {careerChapters.map((chapter: any, index: number) => (
                <ChapterCard key={index} chapter={chapter} index={index} />
              ))}
            </div>
          </motion.div>
        )}
      </div>

      {/* Section Data Editor - Modal for Professional Experience editing */}
      <SectionDataEditor
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        config={experiencesConfig}
        items={Array.isArray(experiences) ? experiences : []}
        historyId={historyId || ''}
        onItemsUpdate={handleExperiencesUpdate}
      />
    </section>
  );
};

const ChapterCard: React.FC<{ chapter: any; index: number }> = ({ chapter, index }) => {
  const [isFlipped, setIsFlipped] = useState(false);
  const [rotateAxis, setRotateAxis] = useState<'y' | 'x'>('y');

  // Randomize rotation axis on flip to create dynamic 3D feel
  const handleToggleFlip = () => {
    if (!isFlipped) {
      setRotateAxis(Math.random() > 0.5 ? 'y' : 'x');
    }
    setIsFlipped(!isFlipped);
  };

  return (
    <motion.div
      className="chapter-card-container"
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ duration: 0.6, delay: index * 0.1 }}
      onClick={handleToggleFlip}
    >
      <motion.div
        className="chapter-card-inner"
        animate={{ 
          rotateY: isFlipped && rotateAxis === 'y' ? 180 : 0,
          rotateX: isFlipped && rotateAxis === 'x' ? 180 : 0 
        }}
        transition={{ 
          type: 'spring', 
          stiffness: 40,
          damping: 14,
          mass: 1.2
        }}
        style={{ transformStyle: 'preserve-3d', position: 'relative', width: '100%', height: '100%' }}
      >
        {/* Front Face */}
        <div className="chapter-card-face chapter-card-front">
          <div className="chapter-number">Chapter {index + 1}</div>
          <h4 className="chapter-title">{chapter.title || chapter.phase}</h4>
          <p className="chapter-period">{chapter.period || chapter.timeframe}</p>
          <div className="flip-hint">
            <span>Click to reveal</span>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="m9 18 6-6-6-6"/>
            </svg>
          </div>
        </div>

        {/* Back Face */}
        <div 
          className="chapter-card-face chapter-card-back"
          style={{
            transform: rotateAxis === 'y' ? 'rotateY(180deg)' : 'rotateX(180deg)'
          }}
        >
          <div className="chapter-number">Chapter {index + 1} - Insights</div>
          <p className="chapter-description">{chapter.narrative || chapter.description}</p>
          {chapter.key_learnings && (
            <div className="chapter-learnings">
              <div className="learnings-title">Key Learnings:</div>
              <ul>
                {chapter.key_learnings.slice(0, 3).map((learning: string, i: number) => (
                  <li key={i}>{learning}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
};

const ExperienceCard: React.FC<{ experience: any }> = ({ experience }) => {
  const [hovered, setHovered] = useState(false);

  const springProps = useSpring({
    transform: hovered ? 'scale(1.02)' : 'scale(1)',
    boxShadow: hovered
      ? '0 20px 60px rgba(0, 212, 255, 0.2)'
      : '0 8px 32px rgba(0, 212, 255, 0.1)',
  });

  return (
    <animated.div
      className="experience-card glass"
      style={springProps}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div className="exp-header">
        <div>
          <h3 className="exp-title">{experience.title || experience.role}</h3>
          <div className="exp-company">{experience.company || experience.organization}</div>
        </div>
        <div className="exp-duration">{experience.duration || experience.period}</div>
      </div>

      {experience.location && (
        <div className="exp-location">
          <svg viewBox="0 0 24 24" fill="none" width="16" height="16">
            <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z" fill="currentColor"/>
          </svg>
          <span>{experience.location}</span>
        </div>
      )}

      <div className="exp-description">
        {experience.description || experience.summary}
      </div>

      {experience.highlights && experience.highlights.length > 0 && (
        <div className="exp-achievements">
          <h4>Key Highlights:</h4>
          <ul>
            {experience.highlights.map((highlight: string, index: number) => (
              <li key={index}>{highlight}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Fallback for old data structure */}
      {!experience.highlights && experience.achievements && experience.achievements.length > 0 && (
        <div className="exp-achievements">
          <h4>Key Achievements:</h4>
          <ul>
            {experience.achievements.map((achievement: string, index: number) => (
              <li key={index}>{achievement}</li>
            ))}
          </ul>
        </div>
      )}

      {experience.technologies && experience.technologies.length > 0 && (
        <div className="exp-technologies">
          {experience.technologies.map((tech: string, index: number) => (
            <span key={index} className="tech-tag glass">
              {tech}
            </span>
          ))}
        </div>
      )}

      {experience.skills && experience.skills.length > 0 && !experience.technologies && (
        <div className="exp-technologies">
          {experience.skills.map((skill: string, index: number) => (
            <span key={index} className="tech-tag glass">
              {skill}
            </span>
          ))}
        </div>
      )}
    </animated.div>
  );
};

export default ExperienceSection;
