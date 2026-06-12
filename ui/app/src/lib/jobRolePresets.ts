export type JobRolePresetKey = 'Software Engineer' | 'Data Scientist' | 'Frontend Developer'

export interface JobRolePreset {
  title: JobRolePresetKey
  description: string
  skills: string[]
}

export const JOB_ROLE_PRESETS: Record<JobRolePresetKey, JobRolePreset> = {
  'Software Engineer': {
    title: 'Software Engineer',
    description: `Role: Software Engineer

We are hiring a Software Engineer to design, build, and maintain scalable backend services and APIs.

Requirements:
- Strong proficiency in Python and REST API development
- Solid understanding of data structures and algorithms
- Experience with system design and distributed systems
- Familiarity with databases, caching, and observability

Nice to have: Docker, CI/CD, cloud platforms (AWS/GCP).`,
    skills: ['Python', 'REST APIs', 'Data Structures', 'System Design', 'SQL', 'Docker'],
  },
  'Data Scientist': {
    title: 'Data Scientist',
    description: `Role: Data Scientist

We are hiring a Data Scientist to build predictive models and deliver actionable insights from complex datasets.

Requirements:
- Strong Python skills with ML libraries (scikit-learn, PyTorch, or TensorFlow)
- Statistical modelling and experiment design
- Data wrangling with Pandas / NumPy and SQL
- Ability to communicate findings to non-technical stakeholders

Nice to have: NLP, feature stores, MLOps pipelines.`,
    skills: ['Python', 'Machine Learning', 'Pandas', 'Statistics', 'SQL', 'Experiment Design'],
  },
  'Frontend Developer': {
    title: 'Frontend Developer',
    description: `Role: Frontend Developer

We are hiring a Frontend Developer to craft responsive, accessible web experiences for our hiring and compliance products.

Requirements:
- Expert-level React and TypeScript
- Modern CSS, responsive layout, and component libraries
- Web accessibility (WCAG) and performance best practices
- REST API integration and client-side state management

Nice to have: design systems, Storybook, automated UI testing.`,
    skills: ['React', 'TypeScript', 'JavaScript', 'CSS', 'UI/UX', 'Accessibility'],
  },
}

export type JobRoleOption = 'Custom' | JobRolePresetKey

export const JOB_ROLE_OPTIONS: JobRoleOption[] = [
  'Custom',
  ...(Object.keys(JOB_ROLE_PRESETS) as JobRolePresetKey[]),
]

export function presetSkills(option: JobRoleOption): string[] {
  if (option === 'Custom') return []
  return JOB_ROLE_PRESETS[option].skills
}
