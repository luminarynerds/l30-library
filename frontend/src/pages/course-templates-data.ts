/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import {
  FileText, Video, HelpCircle, Beaker, FlaskConical,
  Users, Clock, Award,
} from "lucide-react";
import { createElement } from "react";

export interface CourseTemplate {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  estimatedMinutes: number;
  accessLevel: 'patron' | 'staff' | 'admin';
  modules: {
    title: string;
    description: string;
    lessons: {
      title: string;
      type: 'article' | 'video' | 'quiz' | 'sandbox' | 'lab';
      estimatedMinutes: number;
    }[];
  }[];
}

export const COURSE_TEMPLATES: CourseTemplate[] = [
  {
    id: 'digital-literacy',
    name: 'Digital Literacy Basics',
    description: 'A foundational course template for teaching digital skills to patrons',
    icon: createElement(FileText, { className: "w-8 h-8" }),
    difficulty: 'beginner',
    estimatedMinutes: 90,
    accessLevel: 'patron',
    modules: [
      {
        title: 'Getting Started',
        description: 'Introduction and basic concepts',
        lessons: [
          { title: 'Welcome & Overview', type: 'article', estimatedMinutes: 5 },
          { title: 'Understanding the Basics', type: 'article', estimatedMinutes: 10 },
          { title: 'Knowledge Check', type: 'quiz', estimatedMinutes: 5 },
        ]
      },
      {
        title: 'Core Skills',
        description: 'Essential skills and techniques',
        lessons: [
          { title: 'Key Concepts', type: 'article', estimatedMinutes: 15 },
          { title: 'Step-by-Step Tutorial', type: 'video', estimatedMinutes: 10 },
          { title: 'Hands-On Practice', type: 'sandbox', estimatedMinutes: 20 },
          { title: 'Skills Assessment', type: 'quiz', estimatedMinutes: 10 },
        ]
      },
      {
        title: 'Putting It Together',
        description: 'Application and review',
        lessons: [
          { title: 'Real-World Applications', type: 'article', estimatedMinutes: 10 },
          { title: 'Final Project', type: 'lab', estimatedMinutes: 20 },
          { title: 'Course Summary', type: 'article', estimatedMinutes: 5 },
        ]
      }
    ]
  },
  {
    id: 'staff-training',
    name: 'Staff Training Module',
    description: 'Standard template for staff onboarding and training courses',
    icon: createElement(Users, { className: "w-8 h-8" }),
    difficulty: 'intermediate',
    estimatedMinutes: 120,
    accessLevel: 'staff',
    modules: [
      {
        title: 'Introduction',
        description: 'Course overview and objectives',
        lessons: [
          { title: 'Course Overview', type: 'article', estimatedMinutes: 5 },
          { title: 'Learning Objectives', type: 'article', estimatedMinutes: 5 },
          { title: 'Pre-Assessment', type: 'quiz', estimatedMinutes: 10 },
        ]
      },
      {
        title: 'Core Content',
        description: 'Main training content',
        lessons: [
          { title: 'Key Policies & Procedures', type: 'article', estimatedMinutes: 20 },
          { title: 'Video Walkthrough', type: 'video', estimatedMinutes: 15 },
          { title: 'Case Studies', type: 'article', estimatedMinutes: 15 },
          { title: 'Practice Scenarios', type: 'sandbox', estimatedMinutes: 20 },
        ]
      },
      {
        title: 'Assessment & Certification',
        description: 'Final evaluation',
        lessons: [
          { title: 'Review Session', type: 'article', estimatedMinutes: 10 },
          { title: 'Practical Exercise', type: 'lab', estimatedMinutes: 25 },
          { title: 'Final Assessment', type: 'quiz', estimatedMinutes: 15 },
        ]
      }
    ]
  },
  {
    id: 'ai-literacy',
    name: 'AI Literacy Course',
    description: 'Template for teaching AI concepts and responsible usage',
    icon: createElement(Beaker, { className: "w-8 h-8" }),
    difficulty: 'intermediate',
    estimatedMinutes: 150,
    accessLevel: 'patron',
    modules: [
      {
        title: 'What is AI?',
        description: 'Understanding artificial intelligence basics',
        lessons: [
          { title: 'Introduction to AI', type: 'article', estimatedMinutes: 10 },
          { title: 'How AI Works', type: 'video', estimatedMinutes: 15 },
          { title: 'AI in Everyday Life', type: 'article', estimatedMinutes: 10 },
          { title: 'Knowledge Check', type: 'quiz', estimatedMinutes: 5 },
        ]
      },
      {
        title: 'Using AI Tools',
        description: 'Practical AI applications',
        lessons: [
          { title: 'AI Assistants Overview', type: 'article', estimatedMinutes: 10 },
          { title: 'Writing Effective Prompts', type: 'article', estimatedMinutes: 15 },
          { title: 'Prompt Practice Lab', type: 'sandbox', estimatedMinutes: 20 },
          { title: 'AI Image & Media Tools', type: 'video', estimatedMinutes: 10 },
        ]
      },
      {
        title: 'Critical Thinking with AI',
        description: 'Evaluating AI outputs and responsible usage',
        lessons: [
          { title: 'Spotting AI Limitations', type: 'article', estimatedMinutes: 10 },
          { title: 'Fact-Checking AI Content', type: 'lab', estimatedMinutes: 15 },
          { title: 'Ethical Considerations', type: 'article', estimatedMinutes: 10 },
          { title: 'Final Assessment', type: 'quiz', estimatedMinutes: 15 },
        ]
      }
    ]
  },
  {
    id: 'quick-guide',
    name: 'Quick Guide',
    description: 'Short, focused tutorial for a single topic or skill',
    icon: createElement(Clock, { className: "w-8 h-8" }),
    difficulty: 'beginner',
    estimatedMinutes: 30,
    accessLevel: 'patron',
    modules: [
      {
        title: 'Quick Guide',
        description: 'Complete guide in one module',
        lessons: [
          { title: 'Introduction', type: 'article', estimatedMinutes: 5 },
          { title: 'Step-by-Step Guide', type: 'article', estimatedMinutes: 10 },
          { title: 'Try It Yourself', type: 'sandbox', estimatedMinutes: 10 },
          { title: 'Quick Quiz', type: 'quiz', estimatedMinutes: 5 },
        ]
      }
    ]
  },
  {
    id: 'workshop',
    name: 'Workshop Series',
    description: 'Multi-session workshop with hands-on activities',
    icon: createElement(FlaskConical, { className: "w-8 h-8" }),
    difficulty: 'intermediate',
    estimatedMinutes: 180,
    accessLevel: 'patron',
    modules: [
      {
        title: 'Session 1: Foundation',
        description: 'Building the basics',
        lessons: [
          { title: 'Welcome & Introductions', type: 'article', estimatedMinutes: 5 },
          { title: 'Core Concepts', type: 'article', estimatedMinutes: 15 },
          { title: 'Hands-On Activity 1', type: 'lab', estimatedMinutes: 25 },
          { title: 'Session Review', type: 'quiz', estimatedMinutes: 5 },
        ]
      },
      {
        title: 'Session 2: Building Skills',
        description: 'Developing proficiency',
        lessons: [
          { title: 'Review & Warm-Up', type: 'article', estimatedMinutes: 10 },
          { title: 'Advanced Concepts', type: 'video', estimatedMinutes: 15 },
          { title: 'Hands-On Activity 2', type: 'lab', estimatedMinutes: 30 },
          { title: 'Progress Check', type: 'quiz', estimatedMinutes: 5 },
        ]
      },
      {
        title: 'Session 3: Mastery Project',
        description: 'Applying all skills',
        lessons: [
          { title: 'Project Introduction', type: 'article', estimatedMinutes: 10 },
          { title: 'Capstone Project', type: 'lab', estimatedMinutes: 45 },
          { title: 'Showcase & Feedback', type: 'article', estimatedMinutes: 10 },
          { title: 'Final Assessment', type: 'quiz', estimatedMinutes: 10 },
        ]
      }
    ]
  },
  {
    id: 'certification',
    name: 'Certification Course',
    description: 'Comprehensive course with certification upon completion',
    icon: createElement(Award, { className: "w-8 h-8" }),
    difficulty: 'advanced',
    estimatedMinutes: 240,
    accessLevel: 'staff',
    modules: [
      {
        title: 'Module 1: Foundations',
        description: 'Core knowledge and concepts',
        lessons: [
          { title: 'Course Overview', type: 'article', estimatedMinutes: 10 },
          { title: 'Foundational Concepts', type: 'article', estimatedMinutes: 20 },
          { title: 'Video Lecture 1', type: 'video', estimatedMinutes: 20 },
          { title: 'Module 1 Quiz', type: 'quiz', estimatedMinutes: 15 },
        ]
      },
      {
        title: 'Module 2: Intermediate Skills',
        description: 'Building on the basics',
        lessons: [
          { title: 'Intermediate Concepts', type: 'article', estimatedMinutes: 20 },
          { title: 'Video Lecture 2', type: 'video', estimatedMinutes: 20 },
          { title: 'Practice Lab', type: 'lab', estimatedMinutes: 30 },
          { title: 'Module 2 Quiz', type: 'quiz', estimatedMinutes: 15 },
        ]
      },
      {
        title: 'Module 3: Advanced Application',
        description: 'Advanced topics and real-world application',
        lessons: [
          { title: 'Advanced Topics', type: 'article', estimatedMinutes: 25 },
          { title: 'Case Study Analysis', type: 'article', estimatedMinutes: 20 },
          { title: 'Advanced Lab', type: 'lab', estimatedMinutes: 30 },
          { title: 'Module 3 Quiz', type: 'quiz', estimatedMinutes: 15 },
        ]
      },
      {
        title: 'Final Certification',
        description: 'Comprehensive assessment',
        lessons: [
          { title: 'Review Session', type: 'article', estimatedMinutes: 15 },
          { title: 'Certification Exam', type: 'quiz', estimatedMinutes: 30 },
        ]
      }
    ]
  },
];

export const LESSON_TYPE_ICONS: Record<string, React.ReactNode> = {
  article: createElement(FileText, { className: "w-4 h-4" }),
  video: createElement(Video, { className: "w-4 h-4" }),
  quiz: createElement(HelpCircle, { className: "w-4 h-4" }),
  sandbox: createElement(Beaker, { className: "w-4 h-4" }),
  lab: createElement(FlaskConical, { className: "w-4 h-4" }),
};

export function getDifficultyColor(difficulty: string): string {
  switch (difficulty) {
    case 'beginner': return 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400';
    case 'intermediate': return 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400';
    case 'advanced': return 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400';
    default: return 'bg-earth-100 text-earth-800 dark:bg-earth-700 dark:text-earth-300';
  }
}
