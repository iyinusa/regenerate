import { motion } from 'framer-motion';
import { useState, useEffect, useRef } from 'react';
import SectionDataEditor from './SectionDataEditor';
import { educationConfig } from './sectionEditorConfig';
import './EducationSection.css';

interface EducationSectionProps {
  education: any[];
  journey?: any;
  sectionIndex: number;
  historyId?: string;
  onRequestEdit?: (action: string, callback: () => void) => void;
}

const EducationSection: React.FC<EducationSectionProps> = ({ 
  education: initialEducation,
  sectionIndex,
  historyId,
  onRequestEdit
}) => {
  const [educationList, setEducationList] = useState(initialEducation || []);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setEducationList(initialEducation || []);
  }, [initialEducation]);

  const handleOpenEditModal = () => {
    const openModal = () => setIsEditModalOpen(true);
    if (onRequestEdit) {
      onRequestEdit('edit education', openModal);
    } else {
      openModal();
    }
  };

  const handleUpdate = (updatedItems: any[]) => {
    setEducationList(updatedItems);
  };

  return (
    <section className="journey-section education-section" data-section={sectionIndex} ref={containerRef}>
      {/* Background Particles */}
      <div className="edu-background-particles">
        {[...Array(15)].map((_, i) => (
          <motion.div
            key={i}
            className="particle"
            style={{
              width: Math.random() * 100 + 50,
              height: Math.random() * 100 + 50,
              left: `${Math.random() * 100}%`,
              top: `${Math.random() * 100}%`,
              background: i % 2 === 0 ? 'rgba(0, 212, 255, 0.05)' : 'rgba(153, 51, 255, 0.05)',
            }}
            animate={{
              y: [0, -100, 0],
              x: [0, 50, 0],
              scale: [1, 1.2, 1],
              opacity: [0.3, 0.6, 0.3],
            }}
            transition={{
              duration: 10 + Math.random() * 10,
              repeat: Infinity,
              ease: "easeInOut"
            }}
          />
        ))}
      </div>

      <div className="section-container education-container">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '1rem', marginBottom: '3rem', position: 'relative', zIndex: 10 }}>
          <motion.h2 
            className="section-title gradient-text" 
            style={{ margin: 0 }}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            Academics
          </motion.h2>
          
          {historyId && (
            <button
              onClick={handleOpenEditModal}
              className="edit-section-btn"
              title="Edit Education"
              style={{
                background: 'rgba(0, 212, 255, 0.15)',
                border: '1px solid rgba(0, 212, 255, 0.3)',
                borderRadius: '8px',
                padding: '8px',
                cursor: 'pointer',
                color: '#00d4ff',
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

        <div className="education-grid">
          {educationList.length === 0 ? (
             <div className="empty-state" style={{ textAlign: 'center', color: '#64748b', gridColumn: '1/-1' }}>
               No education history added yet.
             </div>
          ) : (
            educationList.map((edu: any, index: number) => (
              <motion.div
                key={index}
                className="education-card-3d"
                initial={{ opacity: 0, y: 50, rotateX: 10 }}
                whileInView={{ opacity: 1, y: 0, rotateX: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
              >
                <div className="education-card-content">
                  <div>
                    <span className="edu-year">
                      {edu.start_date} - {edu.end_date || 'Present'}
                    </span>
                    <h3 className="edu-institution">{edu.institution}</h3>
                    <div className="edu-degree">
                      {edu.degree} • <span style={{ color: '#00d4ff' }}>{edu.field}</span>
                    </div>
                  </div>
                  
                  <p className="edu-description">
                    {edu.description || "Pursued studies in " + edu.field}
                  </p>
                  
                  {/* Decorative Icon */}
                  <div className="edu-icon">
                    <svg width="1em" height="1em" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 3L1 9l11 6 9-4.91V17h2V9M5 13.18v4L12 21l7-3.82v-4L12 17l-7-3.82z"/>
                    </svg>
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
        config={educationConfig}
        items={educationList}
        historyId={historyId || ''}
        onItemsUpdate={handleUpdate}
      />
    </section>
  );
};

export default EducationSection;
