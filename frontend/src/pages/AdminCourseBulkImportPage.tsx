/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";
import api from "../api/api";
import {
  Upload, FileJson, ArrowLeft, Loader2, Check, X,
  BookOpen, FileText, AlertCircle, Download
} from "lucide-react";
import { useTranslation} from '@/i18n'
import { AdminShell } from '@/components/shells'

interface ImportLesson {
  title: string;
  lesson_type: string;
  content?: Record<string, unknown>;
  estimated_minutes?: number;
}

interface ImportModule {
  title: string;
  description?: string;
  lessons: ImportLesson[];
}

interface ImportCourse {
  title: string;
  description?: string;
  access_level?: string;
  difficulty?: string;
  estimated_minutes?: number;
  modules: ImportModule[];
}

interface ImportResult {
  success: boolean;
  courseTitle: string;
  courseId?: number;
  error?: string;
}

const SAMPLE_JSON = `[
  {
    "title": "Introduction to Library Services",
    "description": "A comprehensive guide to library services for new patrons",
    "access_level": "patron",
    "difficulty": "beginner",
    "estimated_minutes": 60,
    "modules": [
      {
        "title": "Getting Started",
        "description": "Welcome to the library",
        "lessons": [
          {
            "title": "Welcome to the Library",
            "lesson_type": "article",
            "estimated_minutes": 5,
            "content": { "body": "Welcome! This lesson introduces..." }
          },
          {
            "title": "Library Card Basics",
            "lesson_type": "video",
            "estimated_minutes": 10
          },
          {
            "title": "Knowledge Check",
            "lesson_type": "quiz",
            "estimated_minutes": 5
          }
        ]
      }
    ]
  }
]`;

export default function AdminCourseBulkImportPage() {
  const { t } = useTranslation()
  const navigate = useNavigate();
  const [jsonInput, setJsonInput] = useState("");
  const [parsedCourses, setParsedCourses] = useState<ImportCourse[] | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);
  const [importing, setImporting] = useState(false);
  const [results, setResults] = useState<ImportResult[] | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const handleParse = useCallback(() => {
    setParseError(null);
    setParsedCourses(null);

    if (!jsonInput.trim()) {
      setParseError("Please enter JSON data");
      return;
    }

    try {
      const parsed = JSON.parse(jsonInput);
      const courses = Array.isArray(parsed) ? parsed : [parsed];

      // Validate structure
      for (const course of courses) {
        if (!course.title) {
          throw new Error("Each course must have a 'title' field");
        }
        if (!course.modules || !Array.isArray(course.modules)) {
          throw new Error(`Course "${course.title}" must have a 'modules' array`);
        }
        for (const module of course.modules) {
          if (!module.title) {
            throw new Error(`Each module in "${course.title}" must have a 'title' field`);
          }
          if (!module.lessons || !Array.isArray(module.lessons)) {
            throw new Error(`Module "${module.title}" must have a 'lessons' array`);
          }
          for (const lesson of module.lessons) {
            if (!lesson.title) {
              throw new Error(`Each lesson in module "${module.title}" must have a 'title' field`);
            }
            if (!lesson.lesson_type) {
              throw new Error(`Lesson "${lesson.title}" must have a 'lesson_type' field`);
            }
          }
        }
      }

      setParsedCourses(courses);
      toast.success(t('toast.adminCourseBulkImport.validatedLengthCourses', { length: courses.length }));
    } catch (_err) {
      const error = _err as Error;
      setParseError(error.message);
    }
  }, [jsonInput, t]);

  const handleImport = async () => {
    if (!parsedCourses) return;

    setImporting(true);
    const importResults: ImportResult[] = [];

    for (const course of parsedCourses) {
      try {
        // Single transactional POST per course (Wave 1 / W1-D). The server
        // inserts the full {course, modules, lessons, quiz_questions} tree
        // in one transaction; any failure rolls back the whole course.
        const payload = {
          course: {
            title: course.title,
            description: course.description || null,
            access_level: course.access_level || "patron",
            difficulty: course.difficulty || "beginner",
            estimated_minutes: course.estimated_minutes || null,
          },
          modules: course.modules.map((moduleData, i) => ({
            title: moduleData.title,
            description: moduleData.description || null,
            sort_order: i,
            lessons: moduleData.lessons.map((lessonData, j) => ({
              title: lessonData.title,
              lesson_type: lessonData.lesson_type,
              sort_order: j,
              content: lessonData.content || { body: "" },
              quiz_questions: [],
            })),
          })),
          target_stage: "draft" as const,
        };

        const resp = await api.post("/learning/admin/courses/import", payload);
        const courseId = (resp.data?.id ?? resp.id);

        importResults.push({
          success: true,
          courseTitle: course.title,
          courseId,
        });
      } catch (_err) {
        // Structured error from /import: { detail: { error, path } } at 422,
        // or detail string at 409 (title collision). Fall back to message.
        const error = _err as {
          response?: { status?: number; data?: { detail?: string | { error?: string; path?: string } } };
          message?: string;
        };
        const detail = error.response?.data?.detail;
        let message: string;
        if (typeof detail === "string") {
          message = detail;
        } else if (detail && typeof detail === "object") {
          message = detail.path ? `${detail.error ?? "Import failed"} at ${detail.path}` : (detail.error ?? "Import failed");
        } else {
          message = error.message || "Import failed";
        }
        importResults.push({
          success: false,
          courseTitle: course.title,
          error: message,
        });
      }
    }

    setResults(importResults);
    setImporting(false);

    const successCount = importResults.filter(r => r.success).length;
    if (successCount === importResults.length) {
      toast.success(t('toast.adminCourseBulkImport.successfullyImportedSuccesscountCourses', { successCount: successCount }));
    } else if (successCount > 0) {
      toast.success(t('toast.adminCourseBulkImport.importedSuccesscountOfLengthCourses', { successCount: successCount, length: importResults.length }));
    } else {
      toast.error(t('toast.adminCourseBulkImport.importFailed'));
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);

    const file = e.dataTransfer.files[0];
    if (file && file.type === "application/json") {
      const reader = new FileReader();
      reader.onload = (event) => {
        setJsonInput(event.target?.result as string);
      };
      reader.readAsText(file);
    } else {
      toast.error(t('admin.adminCourseBulkImport.pleaseDropAJsonFile'));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        setJsonInput(event.target?.result as string);
      };
      reader.readAsText(file);
    }
  }, []);

  const downloadSample = useCallback(() => {
    const blob = new Blob([SAMPLE_JSON], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "course-import-sample.json";
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  return (
    <AdminShell
      title="Bulk Import Courses"
      subtitle="Import multiple courses from JSON"
      icon={<Upload className="w-7 h-7 text-lsc-rose" />}
      actions={
        <button
          onClick={() => navigate("/staff/admin/courses")}
          className="p-2 hover:bg-lsc-cream dark:hover:bg-earth-700 rounded-lg transition-colors flex items-center gap-2 text-sm text-lsc-dark dark:text-lsc-cream"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Courses
        </button>
      }
      maxWidth="max-w-4xl"
    >
      {/* Results View */}
      {results && (
        <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6 mb-6">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            Import Results
          </h2>
          <div className="space-y-3">
            {results.map((result, idx) => (
              <div
                key={idx}
                className={`flex items-center gap-3 p-3 rounded-lg ${
                  result.success
                    ? 'bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-800'
                    : 'bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800'
                }`}
              >
                {result.success ? (
                  <Check className="w-5 h-5 text-status-success-600 dark:text-status-success-400" />
                ) : (
                  <X className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400" />
                )}
                <div className="flex-1">
                  <p className={`font-medium ${
                    result.success
                      ? 'text-status-success-800 dark:text-status-success-300'
                      : 'text-status-danger-800 dark:text-status-danger-300'
                  }`}>
                    {result.courseTitle}
                  </p>
                  {result.error && (
                    <p className="text-sm text-status-danger-600 dark:text-status-danger-400">{result.error}</p>
                  )}
                </div>
                {result.success && result.courseId && (
                  <button
                    onClick={() => navigate(`/staff/admin/courses/${result.courseId}/edit`)}
                    className="text-sm text-lsc-rose hover:underline"
                  >
                    Edit
                  </button>
                )}
              </div>
            ))}
          </div>
          <div className="flex gap-3 mt-6">
            <button
              onClick={() => {
                setResults(null);
                setParsedCourses(null);
                setJsonInput("");
              }}
              className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors"
            >
              Import More
            </button>
            <button
              onClick={() => navigate("/staff/admin/courses")}
              className="flex-1 bg-lsc-rose text-white px-4 py-2 rounded-lg hover:bg-lsc-rose/90 transition-colors"
            >
              View All Courses
            </button>
          </div>
        </div>
      )}

      {/* Import Form */}
      {!results && (
        <>
          {/* File Drop Zone */}
          <div
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragLeave={() => setDragActive(false)}
            className={`border-2 border-dashed rounded-lg p-8 text-center mb-6 transition-colors ${
              dragActive
                ? 'border-lsc-rose bg-lsc-rose/10'
                : 'border-lsc-border dark:border-earth-700 hover:border-lsc-rose/50'
            }`}
          >
            <input
              type="file"
              accept=".json"
              onChange={handleFileSelect}
              className="hidden"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="cursor-pointer">
              <Upload className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-4" />
              <p className="text-lsc-dark dark:text-lsc-cream font-medium">
                Drop a JSON file here or click to upload
              </p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                Supports single course or array of courses
              </p>
            </label>
          </div>

          {/* JSON Input */}
          <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6 mb-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
                <FileJson className="w-5 h-5" />
                JSON Data
              </h2>
              <button
                onClick={downloadSample}
                className="text-sm text-lsc-rose hover:underline flex items-center gap-1"
              >
                <Download className="w-4 h-4" />
                Download Sample
              </button>
            </div>

            <textarea
              value={jsonInput}
              onChange={(e) => setJsonInput(e.target.value)}
              placeholder={SAMPLE_JSON}
              rows={15}
              className="w-full border border-lsc-border dark:border-earth-700 rounded-lg px-4 py-3 bg-lsc-white dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream focus:ring-2 focus:ring-lsc-rose focus:border-transparent font-mono text-sm"
            />

            {parseError && (
              <div className="flex items-start gap-2 mt-3 p-3 bg-status-danger-50 dark:bg-status-danger-900/20 rounded-lg text-status-danger-600 dark:text-status-danger-400">
                <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                <p className="text-sm">{parseError}</p>
              </div>
            )}

            <button
              onClick={handleParse}
              disabled={!jsonInput.trim()}
              className="mt-4 w-full px-4 py-2 bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-lsc-cream/80 dark:hover:bg-earth-600 disabled:opacity-50 transition-colors"
            >
              Validate JSON
            </button>
          </div>

          {/* Preview */}
          {parsedCourses && (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-lg border border-lsc-border dark:border-earth-700 p-6">
              <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                <Check className="w-5 h-5 text-status-success-600" />
                Ready to Import ({parsedCourses.length} course{parsedCourses.length !== 1 ? 's' : ''})
              </h2>

              <div className="space-y-4 mb-6">
                {parsedCourses.map((course, idx) => (
                  <div
                    key={idx}
                    className="p-4 bg-lsc-cream/30 dark:bg-earth-700/30 rounded-lg"
                  >
                    <div className="flex items-start gap-3">
                      <BookOpen className="w-5 h-5 text-lsc-rose mt-0.5" />
                      <div className="flex-1">
                        <h3 className="font-medium text-lsc-dark dark:text-lsc-cream">
                          {course.title}
                        </h3>
                        {course.description && (
                          <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                            {course.description}
                          </p>
                        )}
                        <div className="flex flex-wrap gap-2 mt-2">
                          <span className="text-xs px-2 py-1 bg-lsc-cream dark:bg-earth-600 rounded">
                            {course.access_level || 'patron'}
                          </span>
                          <span className="text-xs px-2 py-1 bg-lsc-cream dark:bg-earth-600 rounded">
                            {course.difficulty || 'beginner'}
                          </span>
                          <span className="text-xs px-2 py-1 bg-lsc-cream dark:bg-earth-600 rounded">
                            {course.modules.length} modules
                          </span>
                          <span className="text-xs px-2 py-1 bg-lsc-cream dark:bg-earth-600 rounded">
                            {course.modules.reduce((acc, m) => acc + m.lessons.length, 0)} lessons
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setParsedCourses(null)}
                  className="flex-1 px-4 py-2 border border-lsc-border dark:border-earth-700 rounded-lg text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleImport}
                  disabled={importing}
                  className="flex-1 flex items-center justify-center gap-2 bg-lsc-rose text-white px-4 py-2 rounded-lg hover:bg-lsc-rose/90 disabled:opacity-50 transition-colors"
                >
                  {importing ? (
                    <>
                      <Loader2 className="w-4 h-4 motion-safe:animate-spin" />
                      Importing...
                    </>
                  ) : (
                    <>
                      <FileText className="w-4 h-4" />
                      Import Courses
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </AdminShell>
  );
}
