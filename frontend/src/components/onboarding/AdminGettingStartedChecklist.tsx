// SPDX-FileCopyrightText: 2026 Luminary Nerds
// SPDX-License-Identifier: AGPL-3.0-or-later
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircle, Circle, X,
  Users, Scale, Book, Layers, UserPlus,
} from 'lucide-react';
import { useSetupProgress, type SetupProgress } from '@/hooks/useSetupProgress';

const ICON_MAP: Record<string, React.ReactNode> = {
  users: <Users className="w-5 h-5" />,
  scale: <Scale className="w-5 h-5" />,
  book: <Book className="w-5 h-5" />,
  layers: <Layers className="w-5 h-5" />,
  'user-plus': <UserPlus className="w-5 h-5" />,
  'check-circle': <CheckCircle className="w-5 h-5" />,
};

const dismissKey = (lsid: number) => `l30.adminSetupChecklist.dismissed.${lsid}`;

export default function AdminGettingStartedChecklist(): React.ReactElement | null {
  const { data, loading } = useSetupProgress();
  const [hidden, setHidden] = useState(false);

  if (loading || !data || data.all_complete) return null;

  const key = dismissKey(data.library_system_id);
  const dismissed = hidden || localStorage.getItem(key) === '1';

  if (dismissed) {
    return (
      <button
        type="button"
        className="text-sm underline text-earth-600 dark:text-earth-400"
        onClick={() => {
          localStorage.removeItem(key);
          setHidden(false);
        }}
      >
        Show setup checklist
      </button>
    );
  }

  return (
    <Checklist
      data={data}
      onHide={() => {
        localStorage.setItem(key, '1');
        setHidden(true);
      }}
    />
  );
}

function Checklist({ data, onHide }: { data: SetupProgress; onHide: () => void }) {
  const navigate = useNavigate();
  return (
    <section className="border border-lsc-border p-4" aria-label="Library setup checklist">
      <header className="flex items-center justify-between mb-3">
        <div>
          <h2 className="text-sm font-semibold">Library setup</h2>
          <p className="text-xs text-earth-600 dark:text-earth-400">
            {data.completed_count} of {data.total} complete
          </p>
        </div>
        <button type="button" aria-label="Hide setup checklist" onClick={onHide}>
          <X className="w-4 h-4" />
        </button>
      </header>
      <div className="h-1 bg-earth-100 dark:bg-earth-800 mb-3">
        <div
          className="h-1 bg-lsc-rose"
          style={{ width: `${(data.completed_count / data.total) * 100}%` }}
        />
      </div>
      <ul className="space-y-1">
        {data.steps.map((step) => (
          <li key={step.id}>
            <button
              type="button"
              className="flex items-center gap-3 w-full text-left py-2"
              onClick={() => navigate(step.action)}
            >
              <span className={step.completed ? 'text-green-600' : 'text-earth-600 dark:text-earth-400'}>
                {step.completed ? <CheckCircle className="w-5 h-5" /> : <Circle className="w-5 h-5" />}
              </span>
              <span className="text-earth-600 dark:text-earth-400">{ICON_MAP[step.icon]}</span>
              <span className="text-sm">{step.title}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
