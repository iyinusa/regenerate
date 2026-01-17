import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { Chart as ChartJS, RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend } from 'chart.js';
import { Radar } from 'react-chartjs-2';
import * as d3 from 'd3';
import './SkillsSection.css';

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

interface SkillsSectionProps {
  skills: string[];
  journey: any;
  sectionIndex: number;
}

const SkillsSection: React.FC<SkillsSectionProps> = ({ skills, journey, sectionIndex }) => {
  // Handle both legacy and new skills_evolution format
  const skillsEvolution = journey?.skills_evolution || [];
  const bubbleChartRef = useRef<HTMLDivElement>(null);

  // Debug logging to help troubleshoot
  useEffect(() => {
    if (journey) {
      console.log('Journey data in SkillsSection:', {
        hasSkillsEvolution: !!journey.skills_evolution,
        skillsEvolutionLength: journey.skills_evolution?.length || 0,
        skillsEvolutionData: journey.skills_evolution?.slice(0, 2) // First 2 items for debugging
      });
    }
  }, [journey]);

  // Categorize skills
  const categorizedSkills = categorizeSkills(skills);

  // Prepare radar chart data
  const radarData = {
    labels: Object.keys(categorizedSkills),
    datasets: [
      {
        label: 'Skill Proficiency',
        data: Object.values(categorizedSkills).map((skills: any) => skills.length * 10),
        backgroundColor: 'rgba(0, 212, 255, 0.2)',
        borderColor: 'rgba(0, 212, 255, 1)',
        borderWidth: 2,
        pointBackgroundColor: 'rgba(0, 212, 255, 1)',
        pointBorderColor: '#fff',
        pointHoverBackgroundColor: '#fff',
        pointHoverBorderColor: 'rgba(0, 212, 255, 1)',
      },
    ],
  };

  const radarOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        titleColor: '#00d4ff',
        bodyColor: '#fff',
        borderColor: '#00d4ff',
        borderWidth: 1,
      },
    },
    scales: {
      r: {
        angleLines: {
          color: 'rgba(255, 255, 255, 0.1)',
        },
        grid: {
          color: 'rgba(255, 255, 255, 0.1)',
        },
        pointLabels: {
          color: 'rgba(255, 255, 255, 0.8)',
          font: {
            size: 12,
          },
        },
        ticks: {
          display: false,
          backdropColor: 'transparent',
        },
      },
    },
  };

  // Create D3 bubble chart for skills
  useEffect(() => {
    if (!bubbleChartRef.current || skills.length === 0) return;

    const container = bubbleChartRef.current;
    const width = container.clientWidth;
    const height = 400;

    // Clear previous chart
    d3.select(container).selectAll('*').remove();

    const svg = d3.select(container)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .style('overflow', 'visible');

    // Define colors and categories
    const domains = ['Technical', 'Leadership', 'Tools', 'Soft Skills', 'Other'];
    const colors = ['#00d4ff', '#7b2ff7', '#ff2e97', '#00ff88', '#ffaa00'];
    const colorScale = d3.scaleOrdinal().domain(domains).range(colors);

    // Definitions for gradients and filters
    const defs = svg.append('defs');
    
    // Glow filter
    const filter = defs.append('filter').attr('id', 'glow');
    filter.append('feGaussianBlur').attr('stdDeviation', '2.5').attr('result', 'coloredBlur');
    const feMerge = filter.append('feMerge');
    feMerge.append('feMergeNode').attr('in', 'coloredBlur');
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    // Radial gradients for 3D sphere effect
    colors.forEach((c, i) => {
      const grad = defs.append('radialGradient')
        .attr('id', `grad-${i}`)
        .attr('cx', '35%')
        .attr('cy', '35%')
        .attr('r', '60%');
      grad.append('stop').attr('offset', '0%').attr('stop-color', '#ffffff').attr('stop-opacity', 0.9);
      grad.append('stop').attr('offset', '40%').attr('stop-color', c).attr('stop-opacity', 0.9);
      grad.append('stop').attr('offset', '100%').attr('stop-color', d3.color(c)?.darker(0.5).toString() || c).attr('stop-opacity', 1);
    });

    // Prepare data
    const data = skills.map((skill) => ({
      name: skill,
      value: 20 + Math.random() * 30,
      category: getSkillCategory(skill),
    }));

    // Create pack layout
    const pack = d3.pack()
      .size([width, height])
      .padding(5);

    const root = d3.hierarchy({ children: data } as any)
      .sum((d: any) => d.value);

    // @ts-ignore
    const nodes = pack(root).leaves();

    // Create bubbles
    const bubbles = svg.selectAll('.bubble')
      .data(nodes)
      .enter()
      .append('g')
      .attr('class', 'bubble')
      .attr('transform', (d: any) => `translate(${d.x},${d.y})`);

    bubbles.append('circle')
      .attr('r', (d: any) => d.r)
      .attr('fill', (d: any) => {
         const idx = domains.indexOf(d.data.category);
         return `url(#grad-${idx !== -1 ? idx : 4})`;
      })
      .style('filter', 'url(#glow)')
      .attr('stroke', (d: any) => colorScale(d.data.category) as string)
      .attr('stroke-width', 1)
      .attr('stroke-opacity', 0.5)
      .style('cursor', 'pointer')
      .on('mouseenter', function() {
        d3.select(this)
          .transition()
          .duration(300)
          .attr('transform', 'scale(1.1)')
          .style('filter', 'brightness(1.3) url(#glow)');
      })
      .on('mouseleave', function() {
        d3.select(this)
          .transition()
          .duration(300)
          .attr('transform', 'scale(1)')
          .style('filter', 'url(#glow)');
      });

    bubbles.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '.3em')
      .style('fill', '#fff')
      .style('text-shadow', '0 2px 4px rgba(0,0,0,0.8)')
      .style('font-size', (d: any) => `${Math.min(d.r / 2.5, 14)}px`)
      .style('font-weight', '600')
      .style('pointer-events', 'none')
      .text((d: any) => d.data.name);

  }, [skills]);

  return (
    <section className="journey-section skills-section" data-section={sectionIndex}>
      <div className="section-container">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          <h2 className="section-title gradient-text">Skills & Expertise</h2>
          <p className="section-subtitle">A comprehensive view of technical and professional capabilities</p>
        </motion.div>

        <div className="skills-layout">
          {/* Radar Chart */}
          <motion.div
            className="radar-container glass card-glow"
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.2 }}
          >
            <h3 className="chart-title">Skill Distribution</h3>
            <div className="radar-chart">
              <Radar data={radarData} options={radarOptions} />
            </div>
          </motion.div>

          {/* Bubble Chart */}
          <motion.div
            className="bubble-container glass card-glow"
            initial={{ opacity: 0, scale: 0.9 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.4 }}
          >
            <h3 className="chart-title">Skills Overview</h3>
            <div ref={bubbleChartRef} className="bubble-chart"></div>
          </motion.div>
        </div>

        {/* Categorized Skills */}
        <motion.div
          className="categorized-skills"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.6 }}
        >
          {Object.entries(categorizedSkills).map(([category, categorySkills]: [string, any], index) => (
            <motion.div
              key={category}
              className="skill-category glass"
              initial={{ opacity: 0, x: -20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
            >
              <h4 className="category-title gradient-text">{category}</h4>
              <div className="skill-tags">
                {categorySkills.map((skill: string, i: number) => (
                  <motion.span
                    key={i}
                    className="skill-tag glass"
                    whileHover={{ scale: 1.1, y: -3 }}
                    transition={{ type: 'spring', stiffness: 300 }}
                  >
                    {skill}
                  </motion.span>
                ))}
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Skills Evolution */}
        {skillsEvolution.length > 0 && (
          <motion.div
            className="skills-evolution"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.8 }}
          >
            <h3 className="evolution-title gradient-text">Skills Evolution Journey</h3>
            <div className="evolution-timeline">
              {skillsEvolution.map((evolution: any, index: number) => (
                <motion.div
                  key={index}
                  className="evolution-item glass"
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: index * 0.1 }}
                >
                  <div className="evolution-period">{evolution.period || evolution.year || evolution.acquired_date || 'N/A'}</div>
                  <div className="evolution-content">
                    <h5>{evolution.milestone || evolution.stage || evolution.skill || 'Skill Development'}</h5>
                    <p>{evolution.description || evolution.proficiency_growth || 'Skills development phase'}</p>
                    {(evolution.skills_acquired || (evolution.skill && [evolution.skill])) && (
                      <div className="acquired-skills">
                        {(evolution.skills_acquired || [evolution.skill]).map((skill: string, i: number) => (
                          <span key={i} className="acquired-tag">+{skill}</span>
                        ))}
                      </div>
                    )}
                    {evolution.context && (
                      <p className="evolution-context">{evolution.context}</p>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </section>
  );
};

// Helper function to categorize skills
function categorizeSkills(skills: string[]): Record<string, string[]> {
  const categories: Record<string, string[]> = {
    'Technical': [],
    'Leadership': [],
    'Tools': [],
    'Soft Skills': [],
    'Other': [],
  };

  const technicalKeywords = ['python', 'java', 'javascript', 'react', 'node', 'api', 'sql', 'aws', 'azure', 'docker', 'kubernetes', 'backend', 'frontend', 'fullstack', 'typescript', 'go', 'rust', 'c++', 'c#', '.net'];
  const leadershipKeywords = ['leadership', 'management', 'team', 'agile', 'scrum', 'mentor', 'coach'];
  const toolsKeywords = ['git', 'jira', 'jenkins', 'gitlab', 'github', 'vscode', 'postman', 'figma'];
  const softSkillsKeywords = ['communication', 'problem-solving', 'critical thinking', 'collaboration', 'creativity'];

  skills.forEach(skill => {
    const lowerSkill = skill.toLowerCase();
    if (technicalKeywords.some(kw => lowerSkill.includes(kw))) {
      categories['Technical'].push(skill);
    } else if (leadershipKeywords.some(kw => lowerSkill.includes(kw))) {
      categories['Leadership'].push(skill);
    } else if (toolsKeywords.some(kw => lowerSkill.includes(kw))) {
      categories['Tools'].push(skill);
    } else if (softSkillsKeywords.some(kw => lowerSkill.includes(kw))) {
      categories['Soft Skills'].push(skill);
    } else {
      categories['Other'].push(skill);
    }
  });

  // Remove empty categories
  Object.keys(categories).forEach(key => {
    if (categories[key].length === 0) {
      delete categories[key];
    }
  });

  return categories;
}

function getSkillCategory(skill: string): string {
  const lowerSkill = skill.toLowerCase();
  const technicalKeywords = ['python', 'java', 'javascript', 'react', 'node', 'api', 'sql', 'aws', 'azure', 'docker', 'kubernetes'];
  const leadershipKeywords = ['leadership', 'management', 'team', 'agile', 'scrum'];
  const toolsKeywords = ['git', 'jira', 'jenkins', 'gitlab', 'github'];
  const softSkillsKeywords = ['communication', 'problem-solving', 'critical thinking'];

  if (technicalKeywords.some(kw => lowerSkill.includes(kw))) return 'Technical';
  if (leadershipKeywords.some(kw => lowerSkill.includes(kw))) return 'Leadership';
  if (toolsKeywords.some(kw => lowerSkill.includes(kw))) return 'Tools';
  if (softSkillsKeywords.some(kw => lowerSkill.includes(kw))) return 'Soft Skills';
  return 'Other';
}

export default SkillsSection;
