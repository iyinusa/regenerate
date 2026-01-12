import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
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

  // Get milestone data
  const milestones = journey?.milestones || [];
  const eras = timeline?.eras || [];

  return (
    <section className="journey-section timeline-section" data-section={sectionIndex}>
      <div className="section-container">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
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
        >
          <div ref={timelineRef} className="vis-timeline-wrapper"></div>
        </motion.div>

        {/* Key Milestones */}
        {milestones.length > 0 && (
          <motion.div
            className="milestones-grid"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.6 }}
          >
            <h3 className="milestones-title gradient-text">Key Milestones</h3>
            <div className="milestones-list">
              {milestones.map((milestone: any, index: number) => (
                <motion.div
                  key={index}
                  className="milestone-card glass"
                  initial={{ opacity: 0, scale: 0.9 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  whileHover={{ scale: 1.05 }}
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
            </div>
          </motion.div>
        )}
      </div>
    </section>
  );
};

export default TimelineSection;
