/**
 * Generic Section Editor Configuration
 * 
 * This configuration system allows defining CRUD operations for any section
 * of the journey page (Chronicles, Skills, Projects, Experience, etc.)
 */

export interface FieldConfig {
  name: string;
  label: string;
  type: 'text' | 'textarea' | 'select' | 'date' | 'tags' | 'number';
  required?: boolean;
  placeholder?: string;
  options?: Array<{ value: string; label: string; metadata?: any }>;
  rows?: number;
  validation?: (value: any) => string | null;
  defaultValue?: any;
}

export interface SectionEditorConfig {
  sectionName: string;
  displayName: string;
  apiPath: string; // e.g., 'timeline', 'skills', 'projects'
  itemName: string; // Singular name: 'event', 'skill', 'project'
  itemNamePlural: string; // Plural name: 'events', 'skills', 'projects'
  fields: FieldConfig[];
  getItemTitle: (item: any) => string;
  getItemSubtitle?: (item: any) => string;
  getItemDescription?: (item: any) => string;
  getItemBadge?: (item: any) => { text: string; color: string };
  createEmptyItem: () => any;
  sortItems?: (items: any[]) => any[];
}

// Timeline/Chronicles Configuration
export const chroniclesConfig: SectionEditorConfig = {
  sectionName: 'timeline',
  displayName: 'Chronicles',
  apiPath: 'timeline',
  itemName: 'event',
  itemNamePlural: 'events',
  fields: [
    {
      name: 'title',
      label: 'Title',
      type: 'text',
      required: true,
      placeholder: 'Event title...'
    },
    {
      name: 'date',
      label: 'Date',
      type: 'text',
      required: true,
      placeholder: 'YYYY or YYYY-MM-DD'
    },
    {
      name: 'subtitle',
      label: 'Subtitle',
      type: 'text',
      placeholder: 'Optional subtitle...'
    },
    {
      name: 'end_date',
      label: 'End Date',
      type: 'text',
      placeholder: 'For date ranges (optional)'
    },
    {
      name: 'category',
      label: 'Category',
      type: 'select',
      options: [
        { value: 'career', label: 'Career', metadata: { color: '#0066FF', icon: 'briefcase' } },
        { value: 'education', label: 'Education', metadata: { color: '#00CC66', icon: 'graduation-cap' } },
        { value: 'achievement', label: 'Achievement', metadata: { color: '#FFD700', icon: 'trophy' } },
        { value: 'project', label: 'Project', metadata: { color: '#9933FF', icon: 'code' } },
        { value: 'certification', label: 'Certification', metadata: { color: '#FF6633', icon: 'certificate' } }
      ],
      defaultValue: 'career'
    },
    {
      name: 'description',
      label: 'Description',
      type: 'textarea',
      placeholder: 'Event description...',
      rows: 3
    },
    {
      name: 'tags',
      label: 'Tags',
      type: 'tags',
      placeholder: 'Press Enter or comma to add tags...'
    }
  ],
  getItemTitle: (item) => item.title,
  getItemSubtitle: (item) => item.subtitle,
  getItemDescription: (item) => item.description,
  getItemBadge: (item) => ({
    text: item.category || 'career',
    color: item.color || '#0066FF'
  }),
  createEmptyItem: () => ({
    id: '',
    date: new Date().getFullYear().toString(),
    title: '',
    subtitle: '',
    description: '',
    category: 'career',
    icon: 'briefcase',
    color: '#0066FF',
    tags: []
  }),
  sortItems: (items) => items.sort((a, b) => 
    new Date(b.date).getTime() - new Date(a.date).getTime()
  )
};

// Skills Configuration (for future implementation)
export const skillsConfig: SectionEditorConfig = {
  sectionName: 'skills',
  displayName: 'Skills',
  apiPath: 'skills',
  itemName: 'skill',
  itemNamePlural: 'skills',
  fields: [
    {
      name: 'name',
      label: 'Skill Name',
      type: 'text',
      required: true,
      placeholder: 'e.g., Python, Leadership...'
    },
    {
      name: 'category',
      label: 'Category',
      type: 'select',
      options: [
        { value: 'technical', label: 'Technical' },
        { value: 'soft', label: 'Soft Skills' },
        { value: 'language', label: 'Language' },
        { value: 'tool', label: 'Tools & Platforms' }
      ]
    },
    {
      name: 'proficiency',
      label: 'Proficiency Level',
      type: 'select',
      options: [
        { value: 'beginner', label: 'Beginner' },
        { value: 'intermediate', label: 'Intermediate' },
        { value: 'advanced', label: 'Advanced' },
        { value: 'expert', label: 'Expert' }
      ]
    }
  ],
  getItemTitle: (item) => item.name || item,
  getItemBadge: (item) => ({
    text: typeof item === 'string' ? 'Skill' : (item.category || 'Skill'),
    color: '#00d4ff'
  }),
  createEmptyItem: () => ({
    id: '',
    name: '',
    category: 'technical',
    proficiency: 'intermediate'
  })
};

// Professional Experience Configuration
export const experiencesConfig: SectionEditorConfig = {
  sectionName: 'experiences',
  displayName: 'Professional Experience',
  apiPath: 'experiences',
  itemName: 'experience',
  itemNamePlural: 'experiences',
  fields: [
    {
      name: 'title',
      label: 'Job Title / Role',
      type: 'text',
      required: true,
      placeholder: 'e.g., Senior Software Engineer'
    },
    {
      name: 'company',
      label: 'Company / Organization',
      type: 'text',
      required: true,
      placeholder: 'e.g., Tech Corp Inc.'
    },
    {
      name: 'start_date',
      label: 'Start Date',
      type: 'text',
      required: true,
      placeholder: 'e.g., 2020-01 or Jan 2020'
    },
    {
      name: 'end_date',
      label: 'End Date',
      type: 'text',
      placeholder: 'e.g., Present, 2023-12, or Dec 2023'
    },
    {
      name: 'duration',
      label: 'Duration Display',
      type: 'text',
      placeholder: 'e.g., Jan 2020 - Present (auto-generated if empty)'
    },
    {
      name: 'description',
      label: 'Description / Summary',
      type: 'textarea',
      placeholder: 'Describe your role and responsibilities...',
      rows: 4
    },
    {
      name: 'highlights',
      label: 'Key Highlights',
      type: 'tags',
      placeholder: 'Press Enter or comma to add highlights...',
      defaultValue: []
    }
  ],
  getItemTitle: (item) => item.title || item.role || 'Untitled Position',
  getItemSubtitle: (item) => `${item.company || item.organization || ''} ${item.duration || ''}`.trim(),
  getItemDescription: (item) => item.description || item.summary,
  getItemBadge: (item) => ({
    text: item.company || item.organization || 'Experience',
    color: '#0066FF'
  }),
  createEmptyItem: () => ({
    id: '',
    title: '',
    company: '',
    start_date: '',
    end_date: '',
    duration: '',
    description: '',
    highlights: []
  }),
  sortItems: (items) => items.sort((a, b) => {
    // Parse duration to sort by most recent first
    const getYear = (exp: any) => {
      const endDate = exp.end_date || '';
      // Check if it's current (contains "Present" or "Current")
      if (endDate.toLowerCase().includes('present') || endDate.toLowerCase().includes('current')) {
        return 9999; // Put current positions first
      }
      // Extract year from end_date or start_date
      const dateStr = endDate || exp.start_date || exp.duration || '';
      const years = dateStr.match(/\d{4}/g);
      return years && years.length > 0 ? parseInt(years[years.length - 1]) : 0;
    };
    return getYear(b) - getYear(a);
  })
};

// Projects Configuration
export const projectsConfig: SectionEditorConfig = {
  sectionName: 'projects',
  displayName: 'Projects & Achievements',
  apiPath: 'projects',
  itemName: 'project',
  itemNamePlural: 'projects',
  fields: [
    {
      name: 'name',
      label: 'Project Name',
      type: 'text',
      required: true,
      placeholder: 'e.g., E-commerce Platform'
    },
    {
      name: 'category',
      label: 'Category / Type',
      type: 'select',
      options: [
        { value: 'web', label: 'Web Application' },
        { value: 'mobile', label: 'Mobile Application' },
        { value: 'api', label: 'API / Backend' },
        { value: 'opensource', label: 'Open Source' },
        { value: 'research', label: 'Research' },
        { value: 'enterprise', label: 'Enterprise Solution' },
        { value: 'other', label: 'Other' }
      ],
      defaultValue: 'web'
    },
    {
      name: 'description',
      label: 'Description',
      type: 'textarea',
      required: true,
      placeholder: 'Describe the project, its purpose, and your contributions...',
      rows: 4
    },
    {
      name: 'technologies',
      label: 'Technologies Used',
      type: 'tags',
      placeholder: 'Press Enter or comma to add technologies...',
      defaultValue: []
    },
    {
      name: 'highlights',
      label: 'Key Highlights',
      type: 'tags',
      placeholder: 'Press Enter or comma to add highlights...',
      defaultValue: []
    },
    {
      name: 'impact',
      label: 'Impact / Results',
      type: 'textarea',
      placeholder: 'Describe the impact, metrics, or results achieved...',
      rows: 3
    },
    {
      name: 'link',
      label: 'Project Link',
      type: 'text',
      placeholder: 'https://...'
    },
    {
      name: 'github',
      label: 'GitHub Repository',
      type: 'text',
      placeholder: 'https://github.com/...'
    },
    {
      name: 'demo',
      label: 'Demo Link',
      type: 'text',
      placeholder: 'https://...'
    },
    {
      name: 'image',
      label: 'Image URL',
      type: 'text',
      placeholder: 'https://...'
    },
    {
      name: 'date',
      label: 'Date / Year',
      type: 'text',
      placeholder: 'e.g., 2023 or 2023-06'
    }
  ],
  getItemTitle: (item) => item.name || item.title || 'Untitled Project',
  getItemSubtitle: (item) => item.date || '',
  getItemDescription: (item) => item.description,
  getItemBadge: (item) => ({
    text: item.category || item.type || 'project',
    color: '#9933FF'
  }),
  createEmptyItem: () => ({
    id: '',
    name: '',
    category: 'web',
    type: 'web',
    description: '',
    technologies: [],
    highlights: [],
    impact: '',
    link: '',
    github: '',
    demo: '',
    image: '',
    date: new Date().getFullYear().toString()
  }),
  sortItems: (items) => items.sort((a, b) => {
    // Sort by date (most recent first)
    const dateA = a.date || '0';
    const dateB = b.date || '0';
    return dateB.localeCompare(dateA);
  })
};

// Export all configurations
export const sectionConfigs = {
  chronicles: chroniclesConfig,
  skills: skillsConfig,
  experiences: experiencesConfig,
  projects: projectsConfig
  // Add more as we implement them
};
