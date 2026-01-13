import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import './ProjectsSection.css';

interface ProjectsSectionProps {
  projects: any[];
  achievements?: any[];
  sectionIndex: number;
}

const ProjectsSection: React.FC<ProjectsSectionProps> = ({ projects, achievements = [], sectionIndex }) => {
  const [selectedProject, setSelectedProject] = useState<number | null>(null);
  const [filter, setFilter] = useState<string>('all');
  const [activeAchievement, setActiveAchievement] = useState(0);
  const [isScrolling, setIsScrolling] = useState(false);
  const carouselRef = useRef<HTMLDivElement>(null);
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);

  // Get unique project types for filtering
  const projectTypes = ['all', ...new Set(projects.map(p => p.type || p.category || 'other'))];

  const filteredProjects = filter === 'all'
    ? projects
    : projects.filter(p => (p.type || p.category || 'other') === filter);

  const handleNextAchievement = () => {
    setActiveAchievement((prev) => (prev + 1) % achievements.length);
  };

  const handlePrevAchievement = () => {
    if (isScrolling) return;
    setActiveAchievement((prev) => (prev - 1 + achievements.length) % achievements.length);
  };

  const throttledScroll = (direction: 'next' | 'prev') => {
    if (isScrolling) return;
    setIsScrolling(true);
    if (direction === 'next') {
      handleNextAchievement();
    } else {
      handlePrevAchievement();
    }
    setTimeout(() => setIsScrolling(false), 300);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
      if (e.deltaY > 0) {
        throttledScroll('next');
      } else {
        throttledScroll('prev');
      }
    }
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    const touch = e.touches[0];
    touchStartRef.current = { x: touch.clientX, y: touch.clientY };
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (!touchStartRef.current) return;
    
    const touch = e.changedTouches[0];
    const deltaX = touch.clientX - touchStartRef.current.x;
    const deltaY = touch.clientY - touchStartRef.current.y;
    
    // Only handle horizontal swipes (ignore vertical scrolling)
    if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
      if (deltaX > 0) {
        throttledScroll('prev');
      } else {
        throttledScroll('next');
      }
    }
    
    touchStartRef.current = null;
  };

  const getAchievementStyle = (index: number) => {
    if (!achievements.length) return {};
    
    const total = achievements.length;
    let diff = (index - activeAchievement) % total;
    if (diff < 0) diff += total;
    if (diff > total / 2) diff -= total;
    
    const baseDistance = 280;
    const rotateAngle = 35;
    
    if (diff === 0) {
      // Center (Active)
      return {
        x: 0,
        z: 0,
        scale: 1,
        zIndex: 10,
        opacity: 1,
        rotateY: 0,
        filter: 'brightness(1.1)',
        pointerEvents: 'auto'
      };
    } else if (diff === -1 || (diff === total - 1)) {
      // Left
      return {
        x: -baseDistance,
        z: -150,
        scale: 0.8,
        zIndex: 5,
        opacity: 0.6,
        rotateY: rotateAngle,
        filter: 'brightness(0.6) blur(2px)',
        pointerEvents: 'auto'
      };
    } else if (diff === 1 || (diff === -(total - 1))) {
      // Right
      return {
        x: baseDistance,
        z: -150,
        scale: 0.8,
        zIndex: 5,
        opacity: 0.6,
        rotateY: -rotateAngle,
        filter: 'brightness(0.6) blur(2px)',
        pointerEvents: 'auto'
      };
    } else {
      // Hidden cards
      const side = diff > 0 ? 1 : -1;
      return {
        x: side * (baseDistance * 1.5),
        z: -300,
        scale: 0.5,
        zIndex: 1,
        opacity: 0.2,
        rotateY: side * (rotateAngle + 20),
        filter: 'brightness(0.3) blur(4px)',
        pointerEvents: 'none'
      };
    }
  };

  return (
    <section className="journey-section projects-section" data-section={sectionIndex}>
      <div className="section-container">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          <h2 className="section-title gradient-text">Projects & Achievements</h2>
          <p className="section-subtitle">Innovative solutions and impactful contributions</p>
        </motion.div>

        {/* Filter */}
        <motion.div
          className="project-filters"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.2 }}
        >
          {projectTypes.map((type, index) => (
            <button
              key={index}
              className={`filter-btn glass ${filter === type ? 'active' : ''}`}
              onClick={() => setFilter(type)}
            >
              {type.charAt(0).toUpperCase() + type.slice(1)}
            </button>
          ))}
        </motion.div>

        {/* Projects Grid */}
        <motion.div
          className="projects-grid"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.4 }}
        >
          <AnimatePresence mode="popLayout">
            {filteredProjects.map((project, index) => (
              <motion.div
                key={project.name || index}
                className="project-card glass card-glow"
                layout
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={{ duration: 0.5 }}
                whileHover={{ y: -10 }}
                onClick={() => setSelectedProject(index)}
              >
                {project.image && (
                  <div className="project-image">
                    <img src={project.image} alt={project.name} />
                  </div>
                )}
                
                <div className="project-content">
                  {(project.type || project.category) && (
                    <span className="project-category">{project.type || project.category}</span>
                  )}
                  
                  <h3 className="project-name">{project.name || project.title}</h3>
                  
                  <p className="project-description">
                    {project.description?.substring(0, 120)}{project.description?.length > 120 ? '...' : ''}
                  </p>

                  {project.technologies && (
                    <div className="project-tech">
                      {project.technologies.slice(0, 4).map((tech: string, i: number) => (
                        <span key={i} className="tech-badge">{tech}</span>
                      ))}
                      {project.technologies.length > 4 && (
                        <span className="tech-badge">+{project.technologies.length - 4}</span>
                      )}
                    </div>
                  )}

                  {(project.link || project.github || project.demo) && (
                    <div className="project-links">
                      {project.link && (
                        <a 
                          href={project.link} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="project-link"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <svg viewBox="0 0 24 24" fill="none" width="18" height="18">
                            <path d="M13 3L16.293 6.293L9.293 13.293L10.707 14.707L17.707 7.707L21 11V3H13Z" fill="currentColor"/>
                            <path d="M19 19H5V5H12L10 3H5C3.89 3 3 3.9 3 5V19C3 20.1 3.89 21 5 21H19C20.1 21 21 20.1 21 19V14L19 12V19Z" fill="currentColor"/>
                          </svg>
                          View
                        </a>
                      )}
                      {project.github && (
                        <a 
                          href={project.github} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="project-link"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
                            <path d="M12 2A10 10 0 0 0 2 12c0 4.42 2.87 8.17 6.84 9.5.5.08.66-.23.66-.5v-1.69c-2.77.6-3.36-1.34-3.36-1.34-.46-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.87 1.52 2.34 1.07 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.92 0-1.11.38-2 1.03-2.71-.1-.25-.45-1.29.1-2.64 0 0 .84-.27 2.75 1.02.79-.22 1.65-.33 2.5-.33.85 0 1.71.11 2.5.33 1.91-1.29 2.75-1.02 2.75-1.02.55 1.35.2 2.39.1 2.64.65.71 1.03 1.6 1.03 2.71 0 3.82-2.34 4.66-4.57 4.91.36.31.69.92.69 1.85V21c0 .27.16.59.67.5C19.14 20.16 22 16.42 22 12A10 10 0 0 0 12 2z"/>
                          </svg>
                          GitHub
                        </a>
                      )}
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </motion.div>

        {/* Achievements */}
        {achievements.length > 0 && (
          <motion.div
            className="achievements-section"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.6 }}
          >
            <h3 className="achievements-title gradient-text">Notable Achievements</h3>
            
            <div 
              className="achievements-carousel"
              ref={carouselRef}
              onWheel={handleWheel}
              onTouchStart={handleTouchStart}
              onTouchEnd={handleTouchEnd}
            >
              <div className="achievements-carousel-container">
                <AnimatePresence mode="popLayout">
                  {achievements.map((achievement, index) => {
                    const style = getAchievementStyle(index);
                    // @ts-ignore
                    const isHidden = style.opacity < 0.1;
                    
                    if (isHidden && achievements.length > 5) return null;
                    
                    return (
                      <motion.div
                        key={index}
                        className={`achievement-carousel-card glass ${index === activeAchievement ? 'active-achievement-card' : ''}`}
                        initial={false}
                        animate={{
                          x: style.x,
                          z: style.z,
                          scale: style.scale,
                          opacity: style.opacity,
                          rotateY: style.rotateY,
                          filter: style.filter
                        } as any}
                        style={{
                          zIndex: style.zIndex,
                          pointerEvents: style.pointerEvents
                        } as any}
                        transition={{ 
                          duration: 0.6, 
                          ease: [0.25, 0.46, 0.45, 0.94]
                        }}
                        onClick={() => setActiveAchievement(index)}
                      >
                        <div className="achievement-icon">
                          <svg viewBox="0 0 24 24" fill="none" width="32" height="32">
                            <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" fill="currentColor"/>
                          </svg>
                        </div>
                        <h4 className="achievement-title">{achievement.title || achievement.name}</h4>
                        <p className="achievement-description">{achievement.description}</p>
                        {achievement.date && (
                          <div className="achievement-date">{achievement.date}</div>
                        )}
                      </motion.div>
                    );
                  })}
                </AnimatePresence>
                
                {/* Navigation Controls */}
                <div className="achievements-carousel-controls">
                  <button className="achievements-carousel-btn prev" onClick={handlePrevAchievement} aria-label="Previous">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="15 18 9 12 15 6"></polyline>
                    </svg>
                  </button>
                  <button className="achievements-carousel-btn next" onClick={handleNextAchievement} aria-label="Next">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="9 18 15 12 9 6"></polyline>
                    </svg>
                  </button>
                </div>
                
                {/* Scroll Hint */}
                <div className="achievements-carousel-scroll-hint">
                  Scroll or swipe to explore achievements
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Project Detail Modal */}
        <AnimatePresence>
          {selectedProject !== null && (
            <motion.div
              className="project-modal-overlay"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedProject(null)}
            >
              <motion.div
                className="project-modal glass"
                initial={{ scale: 0.8, y: 50 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.8, y: 50 }}
                onClick={(e) => e.stopPropagation()}
              >
                <button 
                  className="modal-close"
                  onClick={() => setSelectedProject(null)}
                >
                  <svg viewBox="0 0 24 24" fill="none" width="24" height="24">
                    <path d="M18 6L6 18M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                  </svg>
                </button>

                <ProjectDetail project={filteredProjects[selectedProject]} />
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  );
};

const ProjectDetail: React.FC<{ project: any }> = ({ project }) => {
  return (
    <div className="project-detail">
      {project.image && (
        <div className="detail-image">
          <img src={project.image} alt={project.name} />
        </div>
      )}
      
      <h2 className="detail-title gradient-text">{project.name || project.title}</h2>
      
      {(project.type || project.category) && (
        <span className="detail-category">{project.type || project.category}</span>
      )}

      <p className="detail-description">{project.description}</p>

      {project.highlights && (
        <div className="detail-highlights">
          <h4>Key Highlights:</h4>
          <ul>
            {project.highlights.map((highlight: string, i: number) => (
              <li key={i}>{highlight}</li>
            ))}
          </ul>
        </div>
      )}

      {project.technologies && (
        <div className="detail-technologies">
          <h4>Technologies Used:</h4>
          <div className="tech-tags">
            {project.technologies.map((tech: string, i: number) => (
              <span key={i} className="tech-tag glass">{tech}</span>
            ))}
          </div>
        </div>
      )}

      {project.impact && (
        <div className="detail-impact">
          <h4>Impact:</h4>
          <p>{project.impact}</p>
        </div>
      )}

      {(project.link || project.github || project.demo) && (
        <div className="detail-links">
          {project.link && (
            <a href={project.link} target="_blank" rel="noopener noreferrer" className="detail-link glass">
              Visit Project
            </a>
          )}
          {project.github && (
            <a href={project.github} target="_blank" rel="noopener noreferrer" className="detail-link glass">
              View Code
            </a>
          )}
        </div>
      )}
    </div>
  );
};

export default ProjectsSection;
