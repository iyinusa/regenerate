import { useEffect, useRef, useState } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { Timeline, DataSet } from 'vis-timeline/standalone';
import 'vis-timeline/styles/vis-timeline-graph2d.min.css';
import './TimelineSection.css';

interface TimelineSectionProps {
  timeline: any;
  journey: any;
  sectionIndex: number;
}

const TimelineSection: React.FC<TimelineSectionProps> = ({ timeline, journey, sectionIndex }) => {
  const timelineRef = useRef<HTMLDivElement>(null);
  const visTimelineRef = useRef<Timeline | null>(null);
  const carouselRef = useRef<HTMLDivElement>(null);
  const spinContainerRef = useRef<HTMLDivElement>(null);
  const [isCarouselReady, setIsCarouselReady] = useState(false);

  const { scrollY } = useScroll();

  useEffect(() => {
    if (!timelineRef.current || !timeline?.events) return;

    // Prepare timeline data
    const items = new DataSet<any>(
      timeline.events.map((event: any, index: number) => ({
        id: index,
        content: event.title || event.name || 'Event',
        start: event.start_date || event.date || new Date(),
        end: event.end_date,
        className: event.type || 'default',
        title: event.description || '',
      }))
    );

    // Timeline options
    const options = {
      width: '100%',
      height: '400px',
      margin: {
        item: 20,
      },
      orientation: 'top' as const,
      showCurrentTime: false,
      zoomable: true,
      moveable: true,
      verticalScroll: false,
      horizontalScroll: true,
      stack: true,
      tooltip: {
        followMouse: true,
        overflowMethod: 'cap' as const,
      },
      template: (item: any) => {
        return `<div class="timeline-item-content">${item.content}</div>`;
      },
    };

    // Create timeline
    const visTimeline = new Timeline(timelineRef.current, items, options);
    visTimelineRef.current = visTimeline;

    // Cleanup
    return () => {
      visTimeline.destroy();
    };
  }, [timeline]);

  // 3D Carousel initialization and controls
  useEffect(() => {
    const initCarousel = () => {
      const milestones = journey?.milestones || [];
      if (!carouselRef.current || !spinContainerRef.current || milestones.length === 0) return;

      const spinContainer = spinContainerRef.current;
      const cards = spinContainer.querySelectorAll('.milestone-carousel-card');
      const radius = 280; // Carousel radius
      const autoRotate = true;
      const rotateSpeed = -45; // seconds per 360 degrees
      
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
        e.preventDefault();
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
        e.preventDefault();
        const scale = e.deltaY > 0 ? 0.9 : 1.1;
        const currentScale = parseFloat(getComputedStyle(spinContainer).getPropertyValue('--scale') || '1');
        const newScale = Math.max(0.5, Math.min(2, currentScale * scale));
        spinContainer.style.setProperty('--scale', newScale.toString());
      };

      carouselRef.current.addEventListener('pointerdown', handlePointerDown);
      carouselRef.current.addEventListener('wheel', handleWheel);

      setIsCarouselReady(true);

      return () => {
        if (animationTimer) clearInterval(animationTimer);
        if (carouselRef.current) {
          carouselRef.current.removeEventListener('pointerdown', handlePointerDown);
          carouselRef.current.removeEventListener('wheel', handleWheel);
        }
      };
    };

    const timeoutId = setTimeout(initCarousel, 200);
    return () => clearTimeout(timeoutId);
  }, [journey?.milestones]);

  // Get milestone data
  const milestones = journey?.milestones || [];
  const eras = timeline?.eras || [];

  // Parallax and fade effects on scroll
  const opacity = useTransform(scrollY, [0, 950], [0.5, 1]);
  const scale = useTransform(scrollY, [0, 950], [0.5, 1]);
  const y = useTransform(scrollY, [0, 950], [100, 0]);

  return (
    <section className="journey-section timeline-section" data-section={sectionIndex}>
      <div className="section-container">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }} 
          style={{ opacity, scale, y }}
        >
          <h2 className="section-title gradient-text">The Journey</h2>
          <p className="section-subtitle">A chronological exploration of milestones and achievements</p>
        </motion.div>

        {/* Eras Overview */}
        {eras.length > 0 && (
          <motion.div
            className="eras-container"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.2 }} 
            style={{ opacity, scale, y }}
          >
            {eras.map((era: any, index: number) => (
              <motion.div
                key={index}
                className="era-card glass card-glow"
                initial={{ opacity: 0, x: -30 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                whileHover={{ scale: 1.02, y: -5 }}
              >
                <div className="era-period">{era.period || `Era ${index + 1}`}</div>
                <h3 className="era-title">{era.title || era.name}</h3>
                <p className="era-description">{era.description}</p>
                {era.highlights && (
                  <ul className="era-highlights">
                    {era.highlights.slice(0, 3).map((highlight: string, i: number) => (
                      <li key={i}>{highlight}</li>
                    ))}
                  </ul>
                )}
              </motion.div>
            ))}
          </motion.div>
        )}

        {/* Interactive Timeline */}
        <motion.div
          className="timeline-container glass"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.4 }} 
          style={{ opacity, scale, y }}
        >
          <div ref={timelineRef} className="vis-timeline-wrapper"></div>
        </motion.div>

        {/* Key Milestones - 3D Carousel */}
        {milestones.length > 0 && (
          <motion.div
            className="milestones-3d-section"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.6 }} 
            style={{ opacity, scale, y }}
          >
            <h3 className="milestones-title gradient-text">Key Milestones</h3>
            <p className="carousel-subtitle">Drag to explore • Scroll to zoom</p>
            
            <div className="carousel-3d-container">
              <div 
                ref={carouselRef}
                className="drag-container"
                style={{ cursor: 'grab' }}
                onMouseDown={(e) => e.currentTarget.style.cursor = 'grabbing'}
                onMouseUp={(e) => e.currentTarget.style.cursor = 'grab'}
              >
                <div 
                  ref={spinContainerRef}
                  className="spin-container"
                  style={{ '--scale': '1' } as React.CSSProperties}
                >
                  {milestones.map((milestone: any, index: number) => (
                    <motion.div
                      key={index}
                      className="milestone-card glass milestone-carousel-card"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: isCarouselReady ? 1 : 0 }}
                      transition={{ duration: 0.5, delay: index * 0.1 }}
                    >
                      <div className="milestone-icon">
                        <svg viewBox="0 0 24 24" fill="none" width="24" height="24">
                          <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" fill="currentColor"/>
                        </svg>
                      </div>
                      <div className="milestone-date">{milestone.date || milestone.year}</div>
                      <h4 className="milestone-title">{milestone.title || milestone.achievement}</h4>
                      <p className="milestone-description">{milestone.description}</p>
                      {milestone.impact && (
                        <div className="milestone-impact">
                          <span className="impact-label">Impact:</span>
                          <span className="impact-value">{milestone.impact}</span>
                        </div>
                      )}
                    </motion.div>
                  ))}
                  {/* Central title */}
                  <div className="carousel-center-title">
                    <h4>Key Milestones</h4>
                  </div>
                </div>
                {/* Ground reflection effect */}
                <div className="carousel-ground"></div>
              </div>
            </div>
          </motion.div>
        )}
      </div>
    </section>
  );
};

export default TimelineSection;
