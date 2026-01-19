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

// Export all configurations
export const sectionConfigs = {
  chronicles: chroniclesConfig,
  skills: skillsConfig
  // Add more as we implement them
};
