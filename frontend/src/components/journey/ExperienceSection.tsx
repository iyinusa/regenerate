import { motion } from 'framer-motion';
import { useSpring, animated } from '@react-spring/web';
import { useState } from 'react';
import './ExperienceSection.css';

interface ExperienceSectionProps {
  experiences: any[];
  journey: any;
  sectionIndex: number;
}

const ExperienceSection: React.FC<ExperienceSectionProps> = ({ experiences, journey, sectionIndex }) => {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const careerChapters = journey?.career_chapters || [];

  return (
    <section className="journey-section experience-section" data-section={sectionIndex}>
      <div className="section-container">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          <h2 className="section-title gradient-text">Professional Experience</h2>
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
            {experiences.map((exp, index) => (
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
                <motion.div
                  key={index}
                  className="chapter-card glass card-glow"
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: index * 0.1 }}
                  whileHover={{ scale: 1.03, y: -5 }}
                >
                  <div className="chapter-number">Chapter {index + 1}</div>
                  <h4 className="chapter-title">{chapter.title || chapter.phase}</h4>
                  <p className="chapter-period">{chapter.period || chapter.timeframe}</p>
                  <p className="chapter-description">{chapter.summary || chapter.description}</p>
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
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </section>
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

      {experience.achievements && experience.achievements.length > 0 && (
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
