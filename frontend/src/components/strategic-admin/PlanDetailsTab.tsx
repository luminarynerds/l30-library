/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Eye, Image, FileText, Building2, Sparkles, X, Save } from "lucide-react";
import { useTranslation } from '@/i18n';
import { Plan, statusOptions } from "./strategic-types";

interface Props {
  planForm: Plan;
  setPlanForm: React.Dispatch<React.SetStateAction<Plan>>;
  newValue: string;
  setNewValue: (v: string) => void;
  saving: boolean;
  onSave: () => void;
}

export default function PlanDetailsTab({ planForm, setPlanForm, newValue, setNewValue, saving, onSave }: Props) {
  const { t } = useTranslation();

  const addValue = () => {
    if (newValue.trim()) {
      setPlanForm({ ...planForm, values: [...planForm.values, newValue.trim()] });
      setNewValue("");
    }
  };

  const removeValue = (index: number) => {
    setPlanForm({ ...planForm, values: planForm.values.filter((_, i) => i !== index) });
  };

  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow p-6 space-y-6">
      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">
            Plan Title *
          </label>
          <input
            type="text"
            value={planForm.title}
            onChange={(e) => setPlanForm({ ...planForm, title: e.target.value })}
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
            placeholder={t('placeholder.strategicAdmin.20252028StrategicPlan')}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">
            Status
          </label>
          <select
            value={planForm.status}
            onChange={(e) => setPlanForm({ ...planForm, status: e.target.value })}
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
          >
            {statusOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">
            Period Start *
          </label>
          <input
            type="date"
            value={planForm.period_start}
            onChange={(e) => setPlanForm({ ...planForm, period_start: e.target.value })}
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">
            Period End *
          </label>
          <input
            type="date"
            value={planForm.period_end}
            onChange={(e) => setPlanForm({ ...planForm, period_end: e.target.value })}
            className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
          />
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">
          Description
        </label>
        <textarea
          value={planForm.description || ""}
          onChange={(e) => setPlanForm({ ...planForm, description: e.target.value })}
          rows={2}
          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
          placeholder={t('strategicAdmin.briefDescriptionOfThisStrategic')}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">
          <Building2 className="h-4 w-4 inline mr-1" />
          Mission Statement
        </label>
        <textarea
          value={planForm.mission || ""}
          onChange={(e) => setPlanForm({ ...planForm, mission: e.target.value })}
          rows={3}
          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
          placeholder={t('strategicAdmin.theLibrarySPurposeAnd')}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">
          <Sparkles className="h-4 w-4 inline mr-1" />
          Vision Statement
        </label>
        <textarea
          value={planForm.vision || ""}
          onChange={(e) => setPlanForm({ ...planForm, vision: e.target.value })}
          rows={3}
          className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
          placeholder={t('strategicAdmin.whereTheLibraryIsHeading')}
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-2">
          Core Values
        </label>
        <div className="flex flex-wrap gap-2 mb-2">
          {planForm.values.map((value, i) => (
            <span
              key={i}
              className="px-3 py-1 bg-lsc-cream dark:bg-lsc-dark/30 text-lsc-dark dark:text-lsc-rose-light/50 rounded-full flex items-center gap-2"
            >
              {value}
              <button onClick={() => removeValue(i)} className="text-lsc-rose hover:text-brand-700">
                <X className="h-4 w-4" />
              </button>
            </span>
          ))}
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={newValue}
            onChange={(e) => setNewValue(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addValue()}
            placeholder={t('placeholder.strategicAdmin.addAValue')}
            className="flex-1 px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
          />
          <button
            onClick={addValue}
            className="px-4 py-2 bg-lsc-cream dark:bg-lsc-brown rounded-xl hover:bg-lsc-border dark:hover:bg-earth-600"
          >
            Add
          </button>
        </div>
      </div>

      <div className="border-t border-lsc-border dark:border-earth-700 pt-6">
        <h3 className="text-lg font-medium text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
          <Eye className="h-5 w-5" />
          Public Display Settings
        </h3>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">
              <Image className="h-4 w-4 inline mr-1" />
              Hero Image URL
            </label>
            <input
              type="text"
              value={planForm.hero_image_url || ""}
              onChange={(e) => setPlanForm({ ...planForm, hero_image_url: e.target.value })}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
              placeholder={t('placeholder.strategicAdmin.imageshistorylibrarymodernjpg')}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-lsc-dark dark:text-lsc-cream/80 mb-1">
              <FileText className="h-4 w-4 inline mr-1" />
              Story Introduction
            </label>
            <textarea
              value={planForm.story_intro || ""}
              onChange={(e) => setPlanForm({ ...planForm, story_intro: e.target.value })}
              rows={4}
              className="w-full px-3 py-2 border border-lsc-border dark:border-earth-700 rounded-xl bg-lsc-white dark:bg-lsc-brown text-lsc-dark dark:text-lsc-cream"
              placeholder={t('strategicAdmin.tellTheStoryOfYour')}
            />
          </div>
        </div>
      </div>

      <div className="flex justify-end gap-2 pt-4">
        <button
          onClick={onSave}
          disabled={saving || !planForm.title || !planForm.period_start || !planForm.period_end}
          className="flex items-center gap-2 px-6 py-2 bg-lsc-rose text-white rounded-xl hover:bg-lsc-rose disabled:opacity-50"
        >
          <Save className="h-5 w-5" />
          {saving ? "Saving..." : "Save Plan"}
        </button>
      </div>
    </div>
  );
}
