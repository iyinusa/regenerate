import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import SectionDataEditor from './SectionDataEditor';
import { projectsConfig } from './sectionEditorConfig';
import './ProjectsSection.css';

interface ProjectsSectionProps {
  projects: any[];
  achievements?: any[];
  sectionIndex: number;
  historyId?: string; // For editing functionality
  onRequestEdit?: (action: string, callback: () => void) => void;
}

const ProjectsSection: React.FC<ProjectsSectionProps> = ({ 
  projects: initialProjects, 
  achievements = [], 
  sectionIndex, 
  historyId,
  onRequestEdit
}) => {
  const [selectedProject, setSelectedProject] = useState<number | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [projects, setProjects] = useState(initialProjects || []);
  const carouselRef = useRef<HTMLDivElement>(null);
  const spinContainerRef = useRef<HTMLDivElement>(null);
  const [isCarouselReady, setIsCarouselReady] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const projectsCarouselRef = useRef<HTMLDivElement>(null);
  const [touchStart, setTouchStart] = useState<number | null>(null);
  const [touchEnd, setTouchEnd] = useState<number | null>(null);

  // Minimum swipe distance (in px)
  const minSwipeDistance = 50;

  // Update local projects when prop changes
  useEffect(() => {
    setProjects(initialProjects || []);
  }, [initialProjects]);

  // Handler for projects update from modal
  const handleProjectsUpdate = (updatedProjects: any[]) => {
    setProjects(updatedProjects);
    setSelectedProject(null); // Close any open project detail
  };

  // Handler to open edit modal
  const handleOpenEditModal = () => {
    const openModal = () => {
      setIsEditModalOpen(true);
      setSelectedProject(null); // Close any open project detail
    };
    
    if (onRequestEdit) {
      onRequestEdit('edit projects', openModal);
    } else {
      openModal();
    }
  };

  // Projects carousel navigation
  const nextProject = () => {
    setCurrentIndex((prev) => (prev + 1) % projects.length);
  };

  const prevProject = () => {
    setCurrentIndex((prev) => (prev - 1 + projects.length) % projects.length);
  };

  const goToProject = (index: number) => {
    setCurrentIndex(index);
  };

  // Touch/Swipe handlers
  const onTouchStart = (e: React.TouchEvent) => {
    setTouchEnd(null);
    setTouchStart(e.targetTouches[0].clientX);
  };

  const onTouchMove = (e: React.TouchEvent) => {
    setTouchEnd(e.targetTouches[0].clientX);
  };

  const onTouchEnd = () => {
    if (!touchStart || !touchEnd) return;
    
    const distance = touchStart - touchEnd;
    const isLeftSwipe = distance > minSwipeDistance;
    const isRightSwipe = distance < -minSwipeDistance;

    if (isLeftSwipe) {
      nextProject();
    } else if (isRightSwipe) {
      prevProject();
    }
  };

  // Mouse drag handlers for desktop
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState<number | null>(null);

  const onMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart(e.clientX);
    e.preventDefault();
  };

  const onMouseMove = (e: React.MouseEvent) => {
    if (!isDragging || !dragStart) return;
    e.preventDefault();
  };

  const onMouseUp = (e: React.MouseEvent) => {
    if (!isDragging || !dragStart) return;
    
    const distance = dragStart - e.clientX;
    const isLeftDrag = distance > minSwipeDistance;
    const isRightDrag = distance < -minSwipeDistance;

    if (isLeftDrag) {
      nextProject();
    } else if (isRightDrag) {
      prevProject();
    }

    setIsDragging(false);
    setDragStart(null);
  };

  // 3D Carousel initialization and controls
  useEffect(() => {
    const initCarousel = () => {
      if (!carouselRef.current || !spinContainerRef.current || achievements.length === 0) return;

      const spinContainer = spinContainerRef.current;
      const cards = spinContainer.querySelectorAll('.achievement-carousel-card');
      const radius = 350; // Carousel radius
      const autoRotate = true;
      const rotateSpeed = -60; // seconds per 360 degrees
      
      // Position cards in 3D circle
      cards.forEach((card, i) => {
        const angle = i * (360 / cards.length);
        (card as HTMLElement).style.transform = `rotateY(${angle}deg) translateZ(${radius}px)`;
        (card as HTMLElement).style.transition = 'transform 1s';
        (card as HTMLElement).style.transitionDelay = `${(cards.length - i) / 4}s`;
      });

      // Auto rotation animation
      if (autoRotate) {
        const animationName = rotateSpeed > 0 ? 'spin' : 'spinRevert';
        spinContainer.style.animation = `${animationName} ${Math.abs(rotateSpeed)}s infinite linear`;
      }

      // Mouse interaction variables
      let sX: number, sY: number, nX: number, nY: number;
      let desX = 0, desY = 0, tX = 0, tY = 10;
      let animationTimer: number;

      const applyTransform = (obj: HTMLElement) => {
        // Constrain the angle of camera (between 0 and 180)
        if (tY > 180) tY = 180;
        if (tY < 0) tY = 0;
        // Apply the angle
        obj.style.transform = `rotateX(${-tY}deg) rotateY(${tX}deg)`;
      };

      const playSpin = (yes: boolean) => {
        if (spinContainer) {
          spinContainer.style.animationPlayState = yes ? 'running' : 'paused';
        }
      };

      // Pointer events for smooth interaction
      const handlePointerDown = (e: PointerEvent) => {
        if (animationTimer) clearInterval(animationTimer);
        // Don't prevent default for clicks on cards
        if ((e.target as HTMLElement).closest('.achievement-carousel-card')) {
          // Allow click to pass through
        } else {
          e.preventDefault();
        }
        
        sX = e.clientX;
        sY = e.clientY;
        playSpin(false);

        let hasMoved = false;

        const handlePointerMove = (e: PointerEvent) => {
          hasMoved = true;
          nX = e.clientX;
          nY = e.clientY;
          desX = nX - sX;
          desY = nY - sY;
          tX += desX * 0.1;
          tY += desY * 0.1;
          applyTransform(carouselRef.current!);
          sX = nX;
          sY = nY;
        };

        const handlePointerUp = () => {
          if (hasMoved) {
            animationTimer = window.setInterval(() => {
              desX *= 0.95;
              desY *= 0.95;
              tX += desX * 0.1;
              tY += desY * 0.1;
              applyTransform(carouselRef.current!);
              
              if (Math.abs(desX) < 0.5 && Math.abs(desY) < 0.5) {
                clearInterval(animationTimer);
                playSpin(true);
              }
            }, 17);
          } else {
            // No movement, just resume animation
            playSpin(true);
          }
          
          document.removeEventListener('pointermove', handlePointerMove);
          document.removeEventListener('pointerup', handlePointerUp);
        };

        document.addEventListener('pointermove', handlePointerMove);
        document.addEventListener('pointerup', handlePointerUp);
      };

      // Mouse wheel for zoom
      const handleWheel = (e: WheelEvent) => {
        // Only zoom if not scrolling the page
        if (Math.abs(e.deltaY) > 0) {
          e.preventDefault();
          const scale = e.deltaY > 0 ? 0.95 : 1.05;
          const currentScale = parseFloat(getComputedStyle(spinContainer).getPropertyValue('--scale') || '1');
          const newScale = Math.max(0.3, Math.min(1.5, currentScale * scale));
          spinContainer.style.setProperty('--scale', newScale.toString());
        }
      };

      const carouselElement = carouselRef.current;
      carouselElement.addEventListener('pointerdown', handlePointerDown);
      carouselElement.addEventListener('wheel', handleWheel, { passive: false });

      setIsCarouselReady(true);

      return () => {
        if (animationTimer) clearInterval(animationTimer);
        if (carouselElement) {
          carouselElement.removeEventListener('pointerdown', handlePointerDown);
          carouselElement.removeEventListener('wheel', handleWheel);
        }
      };
    };

    const timeoutId = setTimeout(initCarousel, 500);
    return () => clearTimeout(timeoutId);
  }, [achievements]);

  return (
    <section className="journey-section projects-section" data-section={sectionIndex}>
      <div className="section-container">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
            <h2 className="section-title gradient-text" style={{ margin: 0 }}>Achievements</h2>
            {historyId && (
              <button
                onClick={handleOpenEditModal}
                className="edit-section-btn"
                title="Edit Achievements"
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(31, 74, 174, 0.25)';
                  e.currentTarget.style.transform = 'scale(1.05)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(31, 74, 174, 0.15)';
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
          <p className="section-subtitle">Innovative solutions and impactful contributions</p>
        </motion.div>



        {/* Projects Carousel */}
        <motion.div
          className="projects-carousel-container"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.2 }}
        >
          <div 
            className="projects-carousel" 
            ref={projectsCarouselRef}
            onTouchStart={onTouchStart}
            onTouchMove={onTouchMove}
            onTouchEnd={onTouchEnd}
            onMouseDown={onMouseDown}
            onMouseMove={onMouseMove}
            onMouseUp={onMouseUp}
            onMouseLeave={() => {
              setIsDragging(false);
              setDragStart(null);
            }}
            style={{ cursor: isDragging ? 'grabbing' : 'grab' }}
          >
            {/* Carousel Cards */}
            <div className="projects-carousel-track">
              <AnimatePresence mode="popLayout">
                {projects.map((project, index) => {
                  const isActive = index === currentIndex;
                  const isNext = index === (currentIndex + 1) % projects.length;
                  const isPrev = index === (currentIndex - 1 + projects.length) % projects.length;
                  
                  return (
                    <motion.div
                      key={project.name || index}
                      className={`project-carousel-card glass ${
                        isActive ? 'active' : isNext || isPrev ? 'adjacent' : 'hidden'
                      }`}
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ 
                        opacity: isActive ? 1 : isNext || isPrev ? 0.4 : 0,
                        scale: isActive ? 1 : isNext || isPrev ? 0.8 : 0.6,
                        x: isActive ? 0 : isNext ? '60%' : isPrev ? '-60%' : 0,
                        zIndex: isActive ? 10 : isNext || isPrev ? 5 : 1,
                        rotateY: isActive ? 0 : isNext ? -15 : isPrev ? 15 : 0
                      }}
                      transition={{ 
                        duration: 0.6, 
                        ease: "easeInOut",
                        opacity: { duration: 0.4 },
                        scale: { duration: 0.5 },
                        x: { duration: 0.6 },
                        rotateY: { duration: 0.6 }
                      }}
                      whileHover={isActive ? { y: -10, scale: 1.02 } : {}}
                      onClick={() => {
                        if (isActive) {
                          setSelectedProject(index);
                        } else {
                          setCurrentIndex(index);
                        }
                      }}
                      style={{
                        position: 'absolute',
                        left: 'auto',
                        top: '0%',
                        transform: 'translate(auto, -0%)',
                      }}
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
                  );
                })}
              </AnimatePresence>
            </div>

            {/* Carousel Indicators */}
            <div className="carousel-indicators">
              {projects.map((_, index) => (
                <button
                  key={index}
                  className={`carousel-indicator ${index === currentIndex ? 'active' : ''}`}
                  onClick={() => goToProject(index)}
                />
              ))}
            </div>

            {/* Swipe Hint */}
            <div className="swipe-hint">
              <span>Swipe or drag to navigate</span>
            </div>
          </div>
        </motion.div>

        {/* Achievements - 3D Carousel */}
        {achievements.length > 0 && (
          <motion.div
            className="achievements-3d-section"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.6 }}
          >
            <h3 className="achievements-title gradient-text">Notable Achievements</h3>
            
            <div className="carousel-3d-container">
              <div 
                ref={carouselRef}
                className="drag-container"
                style={{ cursor: 'grab' }}
              >
                <div 
                  ref={spinContainerRef}
                  className="spin-container"
                  style={{ '--scale': '1' } as React.CSSProperties}
                >
                  {achievements.map((achievement: any, index: number) => (
                    <div
                      key={index}
                      className="achievement-carousel-card glass"
                      style={{ opacity: isCarouselReady ? 1 : 0, transition: 'opacity 0.5s' }}
                    >
                      <div className="achievement-icon">
                        <svg viewBox="0 0 24 24" fill="none" width="32" height="32">
                          <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" fill="currentColor"/>
                        </svg>
                      </div>
                      <div className="achievement-date">{achievement.date}</div>
                      <h4 className="achievement-title">{achievement.title || achievement.name}</h4>
                      <p className="achievement-description">{achievement.description}</p>
                    </div>
                  ))}
                  {/* Central title */}
                  <div className="carousel-center-title">
                    <h4>Key Achievements</h4>
                  </div>
                </div>
                {/* Ground reflection effect */}
                <div className="carousel-ground"></div>
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

                <ProjectDetail project={projects[selectedProject]} />
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Edit Modal */}
        {historyId && (
          <SectionDataEditor
            isOpen={isEditModalOpen}
            onClose={() => setIsEditModalOpen(false)}
            config={projectsConfig}
            items={projects}
            historyId={historyId}
            onItemsUpdate={handleProjectsUpdate}
          />
        )}
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
