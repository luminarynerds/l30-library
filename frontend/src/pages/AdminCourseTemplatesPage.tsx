/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation} from '@/i18n';
import toast from "react-hot-toast";
import api from "../api/api";
import { BookOpen, ArrowRight, Loader2, LayoutTemplate } from "lucide-react";
import { AdminShell } from '../components/shells';
import {
  COURSE_TEMPLATES,
  LESSON_TYPE_ICONS,
  getDifficultyColor,
  type CourseTemplate,
} from "./course-templates-data";
import { ModalBackdrop } from '@/components/ui/ModalBackdrop'

export default function AdminCourseTemplatesPage() {
  const { t } = useTranslation()
  const navigate = useNavigate();
  const [creating, setCreating] = useState<string | null>(null);
  const [selectedTemplate, setSelectedTemplate] = useState<CourseTemplate | null>(null);
  const [courseTitle, setCourseTitle] = useState("");

  const handleCreateFromTemplate = async (template: CourseTemplate) => {
    if (!courseTitle.trim()) {
      toast.error(t('admin.adminCourseTemplates.pleaseEnterACourseTitle'));
      return;
    }

    setCreating(template.id);
    try {
      // Create the course
      const courseResponse = await api.post("/learning/courses", {
        title: courseTitle,
        description: `Created from "${template.name}" template`,
        access_level: template.accessLevel,
        difficulty: template.difficulty,
        estimated_minutes: template.estimatedMinutes,
        xp_reward: Math.round(template.estimatedMinutes * 1.5),
      });

      const courseId = courseResponse.data?.id ?? courseResponse.id;

      // Create modules and lessons
      for (let i = 0; i < template.modules.length; i++) {
        const moduleTemplate = template.modules[i]!;

        const moduleResponse = await api.post(`/learning/courses/${courseId}/modules`, {
          title: moduleTemplate.title,
          description: moduleTemplate.description,
          sort_order: i,
        });

        const moduleId = moduleResponse.data.id;

        // Create lessons
        for (let j = 0; j < moduleTemplate.lessons.length; j++) {
          const lessonTemplate = moduleTemplate.lessons[j]!;

          await api.post(`/learning/modules/${moduleId}/lessons`, {
            title: lessonTemplate.title,
            lesson_type: lessonTemplate.type,
            content: { body: `# ${lessonTemplate.title}\n\nAdd your content here...` },
            estimated_minutes: lessonTemplate.estimatedMinutes,
            xp_reward: Math.round(lessonTemplate.estimatedMinutes * 0.5),
            sort_order: j,
          });
        }
      }

      toast.success(t('admin.adminCourseTemplates.courseCreatedFromTemplate'));
      navigate(`/staff/admin/courses/${courseId}/edit`);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      toast.error(error.response?.data?.detail || t('toast.adminCourseTemplates.failedToCreateCourse'));
    } finally {
      setCreating(null);
      setSelectedTemplate(null);
      setCourseTitle("");
    }
  };

  return (
    <AdminShell
      title="Course Templates"
      subtitle="Start with a pre-built structure and customize to your needs"
      icon={<LayoutTemplate className="w-8 h-8" />}
      maxWidth="max-w-6xl"
    >
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {COURSE_TEMPLATES.map((template) => (
          <div
            key={template.id}
            className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 overflow-hidden hover:shadow-lg transition-shadow"
          >
            <div className="p-6">
              <div className="flex items-start gap-4 mb-4">
                <div className="p-3 bg-lsc-cream dark:bg-earth-700 rounded-lg text-lsc-rose">
                  {template.icon}
                </div>
                <div className="flex-1">
                  <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                    {template.name}
                  </h3>
                  <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                    {template.description}
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap gap-2 mb-4">
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getDifficultyColor(template.difficulty)}`}>
                  {template.difficulty}
                </span>
                <span className="px-2 py-1 rounded-full text-xs font-medium bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light">
                  {template.accessLevel}
                </span>
                <span className="px-2 py-1 rounded-full text-xs font-medium bg-earth-100 text-earth-800 dark:bg-earth-700 dark:text-earth-300">
                  ~{template.estimatedMinutes} min
                </span>
              </div>

              <div className="space-y-2 mb-4">
                <p className="text-xs font-medium text-lsc-dark/70 dark:text-lsc-cream/70 uppercase tracking-wider">
                  Structure
                </p>
                {template.modules.map((module, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-sm">
                    <BookOpen className="w-4 h-4 text-lsc-rose mt-0.5 flex-shrink-0" />
                    <div>
                      <span className="text-lsc-dark dark:text-lsc-cream">{module.title}</span>
                      <div className="flex gap-1 mt-1">
                        {module.lessons.map((lesson, lIdx) => (
                          <span
                            key={lIdx}
                            className="p-1 bg-lsc-cream dark:bg-earth-700 rounded"
                            title={`${lesson.title} (${lesson.type})`}
                          >
                            {LESSON_TYPE_ICONS[lesson.type]}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <button
                onClick={() => setSelectedTemplate(template)}
                className="w-full flex items-center justify-center gap-2 bg-lsc-rose text-white px-4 py-2 rounded-lg hover:bg-lsc-rose/90 transition-colors"
              >
                Use Template
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
      </div>

      {selectedTemplate && (
        <ModalBackdrop onClose={() => setSelectedTemplate(null)} title="Dialog">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg shadow-lg max-w-md w-full p-6">
            <h2 className="font-serif text-xl font-bold text-lsc-dark dark:text-lsc-cream mb-4">
              Create from "{selectedTemplate.name}"
            </h2>

            <div className="mb-6">
              <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream mb-2">
                Course Title *
              </label>
              <input
                type="text"
                value={courseTitle}
                onChange={(e) => setCourseTitle(e.target.value)}
                placeholder={t('admin.adminCourseTemplates.enterYourCourseTitle')}
                className="w-full border border-lsc-border dark:border-earth-700 rounded-lg px-4 py-2 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent"
                autoFocus
              />
            </div>

            <div className="bg-lsc-cream/50 dark:bg-earth-700/50 rounded-lg p-4 mb-6">
              <p className="text-sm text-lsc-dark dark:text-lsc-cream mb-2">
                This will create:
              </p>
              <ul className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 space-y-1">
                <li>• {selectedTemplate.modules.length} modules</li>
                <li>• {selectedTemplate.modules.reduce((acc, m) => acc + m.lessons.length, 0)} lessons</li>
                <li>• ~{selectedTemplate.estimatedMinutes} minutes of content structure</li>
              </ul>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => {
                  setSelectedTemplate(null);
                  setCourseTitle("");
                }}
                className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => handleCreateFromTemplate(selectedTemplate)}
                disabled={creating === selectedTemplate.id || !courseTitle.trim()}
                className="flex-1 flex items-center justify-center gap-2 bg-lsc-rose text-white px-4 py-2 rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors"
              >
                {creating === selectedTemplate.id ? (
                  <>
                    <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    Create Course
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </div>
        </ModalBackdrop>
      )}
    </AdminShell>
  );
}
