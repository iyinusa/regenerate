import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Chart as ChartJS, RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend } from 'chart.js';
import { Radar } from 'react-chartjs-2';
import './SkillsSection.css';

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

interface SkillsSectionProps {
  skills: string[];
  journey: any;
  profile: any;
  sectionIndex: number;
}

const SkillsSection: React.FC<SkillsSectionProps> = ({ skills, journey, profile, sectionIndex }) => {
  // Handle both legacy and new skills_evolution format
  const skillsEvolution = journey?.skills_evolution || [];
  
  // State for interactive radar chart
  const [radarView, setRadarView] = useState<'domains' | 'skills'>('domains');
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);

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

  // Calculate skill proficiency scores based on frequency, recency, depth, and real-world application
  const skillProficiencyScores = calculateSkillProficiency(
    skills, 
    skillsEvolution, 
    categorizedSkills,
    profile
  );

  // Prepare radar data based on current view
  let radarData;
  
  if (radarView === 'domains') {
    // Show domain-level proficiency - ensure all domains are visible
    const allDomains = ['Technical', 'Leadership', 'Tools', 'Soft Skills', 'Other'];
    radarData = {
      labels: allDomains,
      datasets: [
        {
          label: 'Domain Proficiency',
          data: allDomains.map(domain => skillProficiencyScores.scores[domain] || 0),
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
  } else {
    // Show individual skills for selected domain
    const domainSkills = selectedDomain ? categorizedSkills[selectedDomain] || [] : [];
    let skillsForRadar;
    
    if (domainSkills.length > 0) {
      // Use domain-specific skills
      skillsForRadar = getDomainSkillsForRadar(skillProficiencyScores.metrics, domainSkills);
    } else {
      // Fallback: show top skills from that domain based on category matching
      const topSkills = getTopSkillsForRadar(skillProficiencyScores.metrics, 8);
      skillsForRadar = topSkills.filter(skill => skill.category === selectedDomain);
      
      // If still no skills, show a message or empty state
      if (skillsForRadar.length === 0) {
        skillsForRadar = [{ skill: 'No skills found', score: 0, category: selectedDomain || 'Other' }];
      }
    }
    
    radarData = {
      labels: skillsForRadar.map(s => s.skill),
      datasets: [
        {
          label: `${selectedDomain} Skills`,
          data: skillsForRadar.map(s => s.score),
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
  }

  const radarOptions = {
    responsive: true,
    maintainAspectRatio: false,
    onClick: (_event: any, elements: any) => {
      if (radarView === 'domains' && elements.length > 0) {
        const index = elements[0].index;
        const allDomains = ['Technical', 'Leadership', 'Tools', 'Soft Skills', 'Other'];
        const domain = allDomains[index];
        // Only allow clicking if domain has skills or we want to show empty state
        setSelectedDomain(domain);
        setRadarView('skills');
      }
    },
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
        callbacks: {
          label: function(context: any) {
            const label = context.label;
            const score = context.parsed.r || 0;
            
            if (radarView === 'domains') {
              // Domain-level tooltip
              const skillCount = categorizedSkills[label]?.length || 0;
              const hasSkills = skillCount > 0;
              return [
                `${label}`,
                `Proficiency: ${score}/100`,
                `Skills: ${skillCount}`,
                `Level: ${score >= 80 ? 'Expert' : score >= 60 ? 'Advanced' : score >= 40 ? 'Intermediate' : score > 0 ? 'Beginner' : 'No Skills'}`,
                hasSkills ? 'Click to view skills →' : 'No skills in this domain'
              ];
            } else {
              // Skill-level tooltip
              const metrics = skillProficiencyScores.metrics[label.toLowerCase()];
              
              if (!metrics) {
                return [`Proficiency: ${score}/100`];
              }
              
              return [
                `${label}`,
                `Proficiency: ${score}/100`,
                `Level: ${score >= 80 ? 'Expert' : score >= 60 ? 'Advanced' : score >= 40 ? 'Intermediate' : 'Beginner'}`,
                metrics.projectUsage > 0 ? `Projects: ${Math.round(metrics.projectUsage)}` : '',
                metrics.experienceUsage > 0 ? `Experience: ${Math.round(metrics.experienceUsage)}` : '',
                metrics.certificationCount > 0 ? `Certs: ${metrics.certificationCount}` : ''
              ].filter(Boolean);
            }
          }
        }
      },
    },
    scales: {
      r: {
        min: 0,
        max: 100,
        angleLines: {
          color: 'rgba(255, 255, 255, 0.1)',
        },
        grid: {
          color: 'rgba(255, 255, 255, 0.1)',
        },
        pointLabels: {
          color: 'rgba(255, 255, 255, 0.8)',
          font: {
            size: radarView === 'domains' ? 14 : 11,
            weight: radarView === 'domains' ? 'bold' as const : 'normal' as const,
          },
        },
        ticks: {
          display: true,
          backdropColor: 'transparent',
          color: 'rgba(255, 255, 255, 0.5)',
          stepSize: 20,
        },
      },
    },
  };



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

        {/* Radar Chart */}
        <motion.div
          className="radar-container glass card-glow"
          initial={{ opacity: 0, scale: 0.9 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, delay: 0.2 }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 className="chart-title" style={{ margin: 0 }}>
              {radarView === 'domains' ? 'Skill Domains' : `${selectedDomain} Skills`}
            </h3>
            {radarView === 'skills' && (
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => {
                  setRadarView('domains');
                  setSelectedDomain(null);
                }}
                style={{
                  background: 'rgba(0, 212, 255, 0.2)',
                  border: '1px solid rgba(0, 212, 255, 0.5)',
                  borderRadius: '8px',
                  padding: '8px 16px',
                  color: '#00d4ff',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '600',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <span>←</span> Back to Domains
              </motion.button>
            )}
          </div>
          {radarView === 'domains' && (
            <p style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.6)', marginBottom: '1rem', marginTop: '-0.5rem' }}>
              Click on any domain to view individual skills
            </p>
          )}
          <div className="radar-chart">
            <Radar data={radarData} options={radarOptions} />
          </div>
        </motion.div>



        {/* Skills Evolution */}
        {skillsEvolution.length > 0 && (
          <motion.div
            className="skills-evolution"
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, delay: 0.4 }}
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

  const technicalKeywords = [
    // Programming Languages
    'python', 'java', 'javascript', 'typescript', 'c++', 'c#', '.net', 'go', 'rust', 'php', 'ruby', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'perl', 'shell', 'bash', 'powershell', 'julia', 'dart', 'objective-c', 'assembly', 'cobol', 'fortran', 'haskell', 'elixir', 'clojure', 'lua', 'groovy', 'vb.net', 'visual basic',
    // Web Frameworks & Libraries
    'react', 'angular', 'vue', 'svelte', 'nextjs', 'next.js', 'gatsby', 'nuxt', 'ember', 'backbone', 'jquery', 'redux', 'mobx', 'rxjs',
    // Backend Frameworks
    'node', 'express', 'django', 'flask', 'fastapi', 'spring', 'spring boot', 'laravel', 'rails', 'ruby on rails', 'asp.net', '.net core', 'nest.js', 'koa', 'fastify', 'gin', 'fiber', 'symfony', 'codeigniter',
    // Mobile Development
    'ios', 'android', 'react native', 'flutter', 'xamarin', 'ionic', 'cordova', 'swift ui', 'jetpack compose',
    // Databases & Data Storage
    'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'cassandra', 'dynamodb', 'oracle', 'mssql', 'sql server', 'sqlite', 'mariadb', 'couchdb', 'neo4j', 'firebase', 'firestore', 'cosmos db', 'bigquery', 'snowflake', 'redshift',
    // Cloud Platforms
    'aws', 'azure', 'gcp', 'google cloud', 'ibm cloud', 'alibaba cloud', 'digitalocean', 'heroku', 'vercel', 'netlify', 'cloudflare', 'linode', 'oracle cloud',
    // DevOps & Infrastructure
    'docker', 'kubernetes', 'k8s', 'terraform', 'ansible', 'puppet', 'chef', 'vagrant', 'jenkins', 'ci/cd', 'circleci', 'travis ci', 'github actions', 'gitlab ci', 'bamboo', 'teamcity', 'argo cd', 'helm', 'istio', 'prometheus', 'grafana', 'nginx', 'apache', 'iis', 'load balancing', 'microservices', 'serverless', 'lambda',
    // Testing & QA
    'jest', 'mocha', 'chai', 'jasmine', 'pytest', 'junit', 'testng', 'selenium', 'cypress', 'playwright', 'puppeteer', 'webdriver', 'katalon', 'appium', 'cucumber', 'test automation', 'unit testing', 'integration testing', 'e2e testing', 'tdd', 'bdd',
    // API & Integration
    'rest', 'restful', 'graphql', 'grpc', 'soap', 'websocket', 'api', 'microservices', 'oauth', 'jwt', 'openapi', 'swagger', 'postman',
    // Data & Analytics
    'data science', 'machine learning', 'ml', 'ai', 'artificial intelligence', 'deep learning', 'neural networks', 'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'pandas', 'numpy', 'matplotlib', 'seaborn', 'nlp', 'natural language processing', 'computer vision', 'data analysis', 'data engineering', 'etl', 'data pipeline', 'spark', 'hadoop', 'kafka', 'airflow', 'dbt', 'tableau', 'power bi', 'looker', 'qlik',
    // Security & Compliance
    'cybersecurity', 'security', 'encryption', 'penetration testing', 'vulnerability assessment', 'soc', 'siem', 'iam', 'zero trust', 'compliance', 'gdpr', 'hipaa', 'pci dss', 'iso 27001', 'owasp',
    // Other Technical
    'blockchain', 'web3', 'ethereum', 'solidity', 'smart contracts', 'iot', 'edge computing', 'ar', 'vr', 'augmented reality', 'virtual reality', 'game development', 'unity', 'unreal engine', 'embedded systems', 'firmware', 'backend', 'frontend', 'fullstack', 'full-stack', 'responsive design', 'ui', 'ux', 'html', 'css', 'sass', 'less', 'webpack', 'vite', 'babel', 'version control'
  ];
  const leadershipKeywords = [
    'leadership', 'entrepreneurship', 'management', 'team lead', 'team leader', 'project management', 'product management', 'program management', 'people management', 'engineering management', 'technical leadership',
    'agile', 'scrum', 'kanban', 'lean', 'safe', 'waterfall', 'project planning', 'sprint planning',
    'mentor', 'mentoring', 'coaching', 'training', 'onboarding', 'career development', 'performance management', 'talent development',
    'strategic planning', 'strategy', 'vision', 'roadmap', 'okr', 'kpi', 'goal setting',
    'stakeholder management', 'client management', 'vendor management', 'partnership',
    'change management', 'transformation', 'innovation', 'process improvement',
    'budget management', 'resource allocation', 'capacity planning', 'hiring', 'recruitment',
    'cross-functional', 'collaboration', 'delegation', 'decision making', 'risk management', 'conflict resolution'
  ];
  const toolsKeywords = [
    // Version Control
    'git', 'github', 'gitlab', 'bitbucket', 'svn', 'mercurial', 'perforce',
    // Project Management
    'jira', 'confluence', 'trello', 'asana', 'monday.com', 'clickup', 'notion', 'basecamp', 'smartsheet', 'airtable', 'wrike', 'ms project', 'azure devops',
    // Development Tools
    'vscode', 'visual studio', 'intellij', 'pycharm', 'webstorm', 'eclipse', 'netbeans', 'sublime', 'atom', 'vim', 'emacs',
    // Design Tools
    'figma', 'sketch', 'adobe xd', 'invision', 'zeplin', 'framer', 'adobe photoshop', 'adobe illustrator', 'canva', 'miro', 'lucidchart', 'draw.io',
    // Communication & Collaboration
    'slack', 'microsoft teams', 'zoom', 'discord', 'google meet', 'webex', 'skype', 'mattermost',
    // CI/CD Tools
    'jenkins', 'circleci', 'travis ci', 'bamboo', 'teamcity', 'octopus deploy',
    // Monitoring & Analytics
    'datadog', 'new relic', 'splunk', 'dynatrace', 'appinsights', 'google analytics', 'mixpanel', 'amplitude', 'segment', 'hotjar', 'pendo',
    // Testing Tools
    'postman', 'insomnia', 'soapui', 'browserstack', 'saucelabs', 'lambdatest',
    // Documentation
    'swagger', 'readme', 'gitbook', 'docusaurus', 'mkdocs', 'sphinx'
  ];
  const softSkillsKeywords = [
    'communication', 'verbal communication', 'written communication', 'presentation', 'public speaking', 'storytelling', 'active listening',
    'problem-solving', 'critical thinking', 'analytical thinking', 'creative thinking', 'troubleshooting', 'root cause analysis',
    'collaboration', 'teamwork', 'team player', 'cross-functional collaboration', 'interpersonal', 'relationship building',
    'adaptability', 'flexibility', 'resilience', 'learning agility', 'growth mindset', 'continuous learning',
    'time management', 'organization', 'prioritization', 'multitasking', 'productivity', 'efficiency',
    'creativity', 'innovation', 'design thinking', 'ideation', 'brainstorming',
    'emotional intelligence', 'empathy', 'self-awareness', 'social skills', 'cultural awareness', 'diversity', 'inclusion',
    'attention to detail', 'quality focus', 'accuracy', 'thoroughness',
    'customer focus', 'client relations', 'user-centric', 'service orientation',
    'negotiation', 'persuasion', 'influence', 'diplomacy', 'mediation',
    'accountability', 'ownership', 'responsibility', 'integrity', 'ethics', 'professionalism',
    'initiative', 'proactive', 'self-motivated', 'drive', 'passion', 'enthusiasm',
    'documentation', 'technical writing', 'report writing', 'business writing'
  ];

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

  // Keep all categories for consistent radar display, even if empty
  // This ensures all domains show on the radar chart for better UX
  return categories;
}

// Calculate skill proficiency scores for radar chart
// This function creates a comprehensive skill assessment by analyzing multiple data sources:
// 1. Explicit skills list from profile
// 2. Skills evolution timeline (recency and frequency)
// 3. Projects (technologies used and mentioned)
// Get skills for a specific domain
function getDomainSkillsForRadar(
  skillMetrics: Record<string, any>,
  domainSkills: string[]
): Array<{ skill: string; score: number; category: string }> {
  const skillScores: Array<{ skill: string; score: number; category: string }> = [];
  
  domainSkills.forEach(skill => {
    const skillKey = skill.toLowerCase();
    const metrics = skillMetrics[skillKey];
    
    if (metrics) {
      // Apply same scoring formula
      const baseScore = 10;
      const frequencyScore = Math.min(metrics.frequency * 4, 20);
      const recencyScore = (metrics.recencyWeight - 1) * 8;
      const projectScore = Math.min(metrics.projectUsage * 8, 20);
      const experienceScore = Math.min(metrics.experienceUsage * 3, 15);
      const certificationScore = metrics.certificationCount * 12;
      const educationScore = Math.min(metrics.educationMentions * 5, 10);
      
      const totalScore = baseScore + frequencyScore + recencyScore + 
                        projectScore + experienceScore + certificationScore + educationScore;
      
      skillScores.push({
        skill: skill,
        score: Math.min(Math.round(totalScore), 100),
        category: metrics.category
      });
    }
  });
  
  // Sort by score (descending)
  return skillScores.sort((a, b) => b.score - a.score);
}

// Get top skills for radar chart display (useful for domain insights)
function getTopSkillsForRadar(
  skillMetrics: Record<string, any>,
  limit: number = 8
): Array<{ skill: string; score: number; category: string }> {
  const skillScores: Array<{ skill: string; score: number; category: string }> = [];
  
  // Calculate scores for all skills
  Object.entries(skillMetrics).forEach(([skillKey, metrics]) => {
    const skill = skillKey.charAt(0).toUpperCase() + skillKey.slice(1);
    
    // Apply comprehensive scoring formula
    const baseScore = 10;
    const frequencyScore = Math.min(metrics.frequency * 4, 20);
    const recencyScore = (metrics.recencyWeight - 1) * 8;
    const projectScore = Math.min(metrics.projectUsage * 8, 20);
    const experienceScore = Math.min(metrics.experienceUsage * 3, 15);
    const certificationScore = metrics.certificationCount * 12;
    const educationScore = Math.min(metrics.educationMentions * 5, 10);
    
    const totalScore = baseScore + frequencyScore + recencyScore + 
                      projectScore + experienceScore + certificationScore + educationScore;
    
    skillScores.push({
      skill: skill,
      score: Math.min(Math.round(totalScore), 100),
      category: metrics.category
    });
  });
  
  // Sort by score (descending) and return top skills
  return skillScores
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}

// Calculate skill proficiency scores for radar chart
// This function creates a comprehensive skill assessment by analyzing multiple data sources:
// 1. Explicit skills list from profile
// 2. Skills evolution timeline (recency and frequency)
// 3. Projects (technologies used and mentioned)
// 4. Work experiences (skills mentioned in descriptions/highlights)
// 5. Certifications (validated proficiency)
// 6. Education (foundational skills)
//
// Scoring Formula (0-100 scale):
// - Base Score: 10 points (every skill gets foundation)
// - Frequency: 4 points per mention (max 20) - shows depth over time
// - Recency: 0-8 points - recent skills weighted higher
// - Projects: 8 points per usage (max 20) - practical application
// - Experience: 3 points per mention (max 15) - real-world usage
// - Certifications: 12 points each - formal validation
// - Education: 5 points per mention (max 10) - foundational learning
//
// Proficiency Levels: Beginner (0-39), Intermediate (40-59), Advanced (60-79), Expert (80-100)
function calculateSkillProficiency(
  skills: string[], 
  skillsEvolution: any[], 
  categorizedSkills: Record<string, string[]>,
  profile: any
): { scores: Record<string, number>; metrics: Record<string, any> } {
  const proficiencyScores: Record<string, number> = {};
  
  // If no skills, return empty scores
  if (!skills || skills.length === 0) {
    return { scores: proficiencyScores, metrics: {} };
  }

  // Build skill frequency and recency map with enhanced tracking
  const skillMetrics: Record<string, { 
    frequency: number; 
    recencyWeight: number; 
    category: string;
    projectUsage: number;
    experienceUsage: number;
    certificationCount: number;
    educationMentions: number;
  }> = {};
  
  // Track all skills and their base presence
  skills.forEach(skill => {
    const category = getSkillCategory(skill);
    skillMetrics[skill.toLowerCase()] = {
      frequency: 1, // Base frequency
      recencyWeight: 1, // Base recency weight
      category,
      projectUsage: 0,
      experienceUsage: 0,
      certificationCount: 0,
      educationMentions: 0
    };
  });

  // Helper function to add or update skill metrics
  const updateSkillMetric = (skill: string, updates: Partial<typeof skillMetrics[string]>) => {
    const skillLower = skill.toLowerCase();
    if (skillMetrics[skillLower]) {
      Object.assign(skillMetrics[skillLower], updates);
    } else {
      const category = getSkillCategory(skill);
      skillMetrics[skillLower] = {
        frequency: 1,
        recencyWeight: 1,
        category,
        projectUsage: 0,
        experienceUsage: 0,
        certificationCount: 0,
        educationMentions: 0,
        ...updates
      };
    }
  };

  // Enhance metrics with skills_evolution data
  if (skillsEvolution && skillsEvolution.length > 0) {
    // Process evolution in reverse order (most recent first) for recency weighting
    const reversedEvolution = [...skillsEvolution].reverse();
    
    reversedEvolution.forEach((evolution, index) => {
      const acquiredSkills = evolution.skills_acquired || 
                           (evolution.skill ? [evolution.skill] : []);
      
      // Recency weight: most recent = 2.0, decreases by 0.1 per period
      const recencyBoost = 2.0 - (index * 0.1);
      
      acquiredSkills.forEach((skill: string) => {
        const skillLower = skill.toLowerCase();
        
        if (skillMetrics[skillLower]) {
          // Skill appeared in evolution - increase frequency and apply recency boost
          skillMetrics[skillLower].frequency += 1;
          skillMetrics[skillLower].recencyWeight = Math.max(
            skillMetrics[skillLower].recencyWeight,
            recencyBoost
          );
        } else {
          // New skill from evolution not in main skills list
          updateSkillMetric(skill, {
            recencyWeight: recencyBoost
          });
        }
      });
    });
  }

  // Extract skills from projects (technologies used)
  if (profile?.projects && Array.isArray(profile.projects)) {
    profile.projects.forEach((project: any) => {
      // Technologies array
      if (project.technologies && Array.isArray(project.technologies)) {
        project.technologies.forEach((tech: string) => {
          const skillLower = tech.toLowerCase();
          if (skillMetrics[skillLower]) {
            skillMetrics[skillLower].projectUsage += 1;
            skillMetrics[skillLower].frequency += 1;
          } else {
            updateSkillMetric(tech, { projectUsage: 1 });
          }
        });
      }
      
      // Scan project description for skill mentions
      if (project.description) {
        Object.keys(skillMetrics).forEach(skillKey => {
          if (project.description.toLowerCase().includes(skillKey)) {
            skillMetrics[skillKey].projectUsage += 0.5; // Partial credit for mentions
          }
        });
      }
    });
  }

  // Extract skills from work experiences
  if (profile?.experiences && Array.isArray(profile.experiences)) {
    profile.experiences.forEach((exp: any) => {
      // Check highlights/responsibilities for skill mentions
      const textToScan = [
        exp.description,
        ...(exp.highlights || []),
        ...(exp.responsibilities || [])
      ].filter(Boolean).join(' ').toLowerCase();
      
      if (textToScan) {
        Object.keys(skillMetrics).forEach(skillKey => {
          // Count occurrences in experience text
          const regex = new RegExp(`\\b${skillKey}\\b`, 'gi');
          const matches = textToScan.match(regex);
          if (matches) {
            skillMetrics[skillKey].experienceUsage += matches.length;
            skillMetrics[skillKey].frequency += matches.length * 0.5; // Weight experience mentions
          }
        });
      }
    });
  }

  // Extract skills from certifications
  if (profile?.certifications && Array.isArray(profile.certifications)) {
    profile.certifications.forEach((cert: any) => {
      const certText = `${cert.name || ''} ${cert.description || ''}`.toLowerCase();
      
      Object.keys(skillMetrics).forEach(skillKey => {
        if (certText.includes(skillKey)) {
          skillMetrics[skillKey].certificationCount += 1;
          skillMetrics[skillKey].frequency += 2; // Certifications are strong signals
        }
      });
    });
  }

  // Extract skills from education
  if (profile?.education && Array.isArray(profile.education)) {
    profile.education.forEach((edu: any) => {
      const eduText = [
        edu.field,
        edu.degree,
        ...(edu.achievements || [])
      ].filter(Boolean).join(' ').toLowerCase();
      
      if (eduText) {
        Object.keys(skillMetrics).forEach(skillKey => {
          if (eduText.includes(skillKey)) {
            skillMetrics[skillKey].educationMentions += 1;
            skillMetrics[skillKey].frequency += 0.5; // Education mentions add value
          }
        });
      }
    });
  }

  // Calculate proficiency score for each category
  Object.keys(categorizedSkills).forEach(category => {
    let categoryScore = 0;
    const categorySkills = categorizedSkills[category];
    
    categorySkills.forEach(skill => {
      const skillLower = skill.toLowerCase();
      const metrics = skillMetrics[skillLower];
      
      if (metrics) {
        // Enhanced score formula incorporating real-world application
        const baseScore = 10;
        const frequencyScore = Math.min(metrics.frequency * 4, 20); // Cap at 20
        const recencyScore = (metrics.recencyWeight - 1) * 8; // 0-8 range
        
        // Practical application bonuses
        const projectScore = Math.min(metrics.projectUsage * 8, 20); // Up to 20 points
        const experienceScore = Math.min(metrics.experienceUsage * 3, 15); // Up to 15 points
        const certificationScore = metrics.certificationCount * 12; // 12 points per cert
        const educationScore = Math.min(metrics.educationMentions * 5, 10); // Up to 10 points
        
        // Total possible: 10 + 20 + 8 + 20 + 15 + 12+ + 10 = 95+ (can exceed 100 before normalization)
        categoryScore += baseScore + frequencyScore + recencyScore + 
                        projectScore + experienceScore + certificationScore + educationScore;
      }
    });
    
    // Average the score and normalize to 0-100 scale
    if (categorySkills.length > 0) {
      const averageScore = categoryScore / categorySkills.length;
      // Normalize: cap at 100
      proficiencyScores[category] = Math.min(Math.round(averageScore), 100);
    } else {
      proficiencyScores[category] = 0;
    }
  });

  return { scores: proficiencyScores, metrics: skillMetrics };
}

function getSkillCategory(skill: string): string {
  const lowerSkill = skill.toLowerCase();
  
  const technicalKeywords = [
    // Programming Languages
    'python', 'java', 'javascript', 'typescript', 'c++', 'c#', '.net', 'go', 'rust', 'php', 'ruby', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'perl', 'shell', 'bash', 'powershell', 'julia', 'dart', 'objective-c', 'assembly', 'cobol', 'fortran', 'haskell', 'elixir', 'clojure', 'lua', 'groovy', 'vb.net', 'visual basic',
    // Web Frameworks & Libraries
    'react', 'angular', 'vue', 'svelte', 'nextjs', 'next.js', 'gatsby', 'nuxt', 'ember', 'backbone', 'jquery', 'redux', 'mobx', 'rxjs',
    // Backend Frameworks
    'node', 'express', 'django', 'flask', 'fastapi', 'spring', 'spring boot', 'laravel', 'rails', 'ruby on rails', 'asp.net', '.net core', 'nest.js', 'koa', 'fastify', 'gin', 'fiber', 'symfony', 'codeigniter',
    // Mobile Development
    'ios', 'android', 'react native', 'flutter', 'xamarin', 'ionic', 'cordova', 'swift ui', 'jetpack compose',
    // Databases & Data Storage
    'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch', 'cassandra', 'dynamodb', 'oracle', 'mssql', 'sql server', 'sqlite', 'mariadb', 'couchdb', 'neo4j', 'firebase', 'firestore', 'cosmos db', 'bigquery', 'snowflake', 'redshift',
    // Cloud Platforms
    'aws', 'azure', 'gcp', 'google cloud', 'ibm cloud', 'alibaba cloud', 'digitalocean', 'heroku', 'vercel', 'netlify', 'cloudflare', 'linode', 'oracle cloud',
    // DevOps & Infrastructure
    'docker', 'kubernetes', 'k8s', 'terraform', 'ansible', 'puppet', 'chef', 'vagrant', 'jenkins', 'ci/cd', 'circleci', 'travis ci', 'github actions', 'gitlab ci', 'bamboo', 'teamcity', 'argo cd', 'helm', 'istio', 'prometheus', 'grafana', 'nginx', 'apache', 'iis', 'load balancing', 'microservices', 'serverless', 'lambda',
    // Testing & QA
    'jest', 'mocha', 'chai', 'jasmine', 'pytest', 'junit', 'testng', 'selenium', 'cypress', 'playwright', 'puppeteer', 'webdriver', 'katalon', 'appium', 'cucumber', 'test automation', 'unit testing', 'integration testing', 'e2e testing', 'tdd', 'bdd',
    // API & Integration
    'rest', 'restful', 'graphql', 'grpc', 'soap', 'websocket', 'api', 'microservices', 'oauth', 'jwt', 'openapi', 'swagger', 'postman',
    // Data & Analytics
    'data science', 'machine learning', 'ml', 'ai', 'artificial intelligence', 'deep learning', 'neural networks', 'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'pandas', 'numpy', 'matplotlib', 'seaborn', 'nlp', 'natural language processing', 'computer vision', 'data analysis', 'data engineering', 'etl', 'data pipeline', 'spark', 'hadoop', 'kafka', 'airflow', 'dbt', 'tableau', 'power bi', 'looker', 'qlik',
    // Security & Compliance
    'cybersecurity', 'security', 'encryption', 'penetration testing', 'vulnerability assessment', 'soc', 'siem', 'iam', 'zero trust', 'compliance', 'gdpr', 'hipaa', 'pci dss', 'iso 27001', 'owasp',
    // Other Technical
    'blockchain', 'web3', 'ethereum', 'solidity', 'smart contracts', 'iot', 'edge computing', 'ar', 'vr', 'augmented reality', 'virtual reality', 'game development', 'unity', 'unreal engine', 'embedded systems', 'firmware', 'backend', 'frontend', 'fullstack', 'full-stack', 'responsive design', 'ui', 'ux', 'html', 'css', 'sass', 'less', 'webpack', 'vite', 'babel', 'version control'
  ];
  
  const leadershipKeywords = [
    'leadership', 'management', 'team lead', 'team leader', 'project management', 'product management', 'program management', 'people management', 'engineering management', 'technical leadership',
    'agile', 'scrum', 'kanban', 'lean', 'safe', 'waterfall', 'project planning', 'sprint planning',
    'mentor', 'mentoring', 'coaching', 'training', 'onboarding', 'career development', 'performance management', 'talent development',
    'strategic planning', 'strategy', 'vision', 'roadmap', 'okr', 'kpi', 'goal setting',
    'stakeholder management', 'client management', 'vendor management', 'partnership',
    'change management', 'transformation', 'innovation', 'process improvement',
    'budget management', 'resource allocation', 'capacity planning', 'hiring', 'recruitment',
    'cross-functional', 'collaboration', 'delegation', 'decision making', 'risk management', 'conflict resolution'
  ];
  
  const toolsKeywords = [
    // Version Control
    'git', 'github', 'gitlab', 'bitbucket', 'svn', 'mercurial', 'perforce',
    // Project Management
    'jira', 'confluence', 'trello', 'asana', 'monday.com', 'clickup', 'notion', 'basecamp', 'smartsheet', 'airtable', 'wrike', 'ms project', 'devops',
    // Development Tools
    'vscode', 'visual studio', 'intellij', 'pycharm', 'webstorm', 'eclipse', 'netbeans', 'sublime', 'atom', 'vim', 'emacs',
    // Design Tools
    'figma', 'sketch', 'adobe xd', 'invision', 'zeplin', 'framer', 'adobe photoshop', 'adobe illustrator', 'canva', 'miro', 'lucidchart', 'draw.io',
    // Communication & Collaboration
    'slack', 'microsoft teams', 'zoom', 'discord', 'google meet', 'webex', 'skype', 'mattermost',
    // CI/CD Tools
    'jenkins', 'circleci', 'travis ci', 'bamboo', 'teamcity', 'octopus deploy',
    // Monitoring & Analytics
    'datadog', 'new relic', 'splunk', 'dynatrace', 'appinsights', 'google analytics', 'mixpanel', 'amplitude', 'segment', 'hotjar', 'pendo',
    // Testing Tools
    'postman', 'insomnia', 'soapui', 'browserstack', 'saucelabs', 'lambdatest',
    // Documentation
    'swagger', 'readme', 'gitbook', 'docusaurus', 'mkdocs', 'sphinx'
  ];
  
  const softSkillsKeywords = [
    'communication', 'verbal communication', 'written communication', 'presentation', 'public speaking', 'storytelling', 'active listening',
    'problem-solving', 'critical thinking', 'analytical thinking', 'creative thinking', 'troubleshooting', 'root cause analysis',
    'collaboration', 'teamwork', 'team player', 'cross-functional collaboration', 'interpersonal', 'relationship building',
    'adaptability', 'flexibility', 'resilience', 'learning agility', 'growth mindset', 'continuous learning',
    'time management', 'organization', 'prioritization', 'multitasking', 'productivity', 'efficiency',
    'creativity', 'innovation', 'design thinking', 'ideation', 'brainstorming',
    'emotional intelligence', 'empathy', 'self-awareness', 'social skills', 'cultural awareness', 'diversity', 'inclusion',
    'attention to detail', 'quality focus', 'accuracy', 'thoroughness',
    'customer focus', 'client relations', 'user-centric', 'service orientation',
    'negotiation', 'persuasion', 'influence', 'diplomacy', 'mediation',
    'accountability', 'ownership', 'responsibility', 'integrity', 'ethics', 'professionalism',
    'initiative', 'proactive', 'self-motivated', 'drive', 'passion', 'enthusiasm',
    'documentation', 'technical writing', 'report writing', 'business writing'
  ];

  if (technicalKeywords.some(kw => lowerSkill.includes(kw))) return 'Technical';
  if (leadershipKeywords.some(kw => lowerSkill.includes(kw))) return 'Leadership';
  if (toolsKeywords.some(kw => lowerSkill.includes(kw))) return 'Tools';
  if (softSkillsKeywords.some(kw => lowerSkill.includes(kw))) return 'Soft Skills';
  return 'Other';
}

export default SkillsSection;
