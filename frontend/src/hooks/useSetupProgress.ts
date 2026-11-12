// SPDX-License-Identifier: AGPL-3.0-or-later
import { useEffect, useState } from 'react';
import { api } from '@/lib/api-client';

export interface SetupProgressStep {
  id: string;
  title: string;
  description: string;
  action: string;
  icon: string;
  completed: boolean;
  count?: number;
}

export interface SetupProgress {
  library_system_id: number;
  completed_count: number;
  total: number;
  all_complete: boolean;
  steps: SetupProgressStep[];
}

export function useSetupProgress(): { data: SetupProgress | null; loading: boolean } {
  const [data, setData] = useState<SetupProgress | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const result = await api.get<SetupProgress>('/setup/progress');
        if (active) setData(result);
      } catch {
        if (active) setData(null);
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return { data, loading };
}
