/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Download, Upload } from "lucide-react";

interface Props {
  plan: { id?: number } | null;
  importJson: string;
  setImportJson: (v: string) => void;
  onExport: () => void;
  onImport: () => void;
}

export default function ImportExportTab({ plan, importJson, setImportJson, onExport, onImport }: Props) {
  return (
    <div className="space-y-6">
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
        <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Download className="h-5 w-5" />
          Export Plan
        </h2>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          Download the current strategic plan as a JSON file for backup or transfer.
        </p>
        <button
          onClick={onExport}
          disabled={!plan?.id}
          className="flex items-center gap-2 px-4 py-2 bg-status-success-600 text-white rounded-xl hover:bg-status-success-700 disabled:opacity-50"
        >
          <Download className="h-4 w-4" /> Export Current Plan
        </button>
      </div>

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6">
        <h2 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Upload className="h-5 w-5" />
          Import Plan
        </h2>
        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
          Import a strategic plan from a JSON file. This will create a new plan.
        </p>
        <textarea
          value={importJson}
          onChange={(e) => setImportJson(e.target.value)}
          rows={10}
          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream font-mono text-sm mb-4"
          placeholder='Paste your JSON here...\n{\n  "title": "2025-2028 Strategic Plan",\n  "period_start": "2025-01-01",\n  "period_end": "2028-12-31",\n  ...\n}'
        />
        <button
          onClick={onImport}
          disabled={!importJson.trim()}
          className="flex items-center gap-2 px-4 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose/90 disabled:opacity-50"
        >
          <Upload className="h-4 w-4" /> Import Plan
        </button>
      </div>
    </div>
  );
}
