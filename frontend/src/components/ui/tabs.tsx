/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import React, { createContext, useContext, useMemo, useState, useCallback, useId } from 'react';
import { cn } from '@/lib/utils';

interface TabsContextValue {
  value: string;
  setValue: (v: string) => void;
  idPrefix: string;
}

const TabsContext = createContext<TabsContextValue | null>(null);

function useTabsContext(component: string): TabsContextValue {
  const ctx = useContext(TabsContext);
  if (!ctx) {
    throw new Error(`${component} must be used within <Tabs>`);
  }
  return ctx;
}

interface TabsProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
}

export function Tabs({
  value: controlledValue,
  defaultValue,
  onValueChange,
  children,
  className,
  ...props
}: TabsProps) {
  const [uncontrolledValue, setUncontrolledValue] = useState<string>(
    defaultValue ?? ''
  );
  const idPrefix = useId();
  const isControlled = controlledValue !== undefined;
  const value = isControlled ? controlledValue : uncontrolledValue;

  const setValue = useCallback(
    (next: string) => {
      if (!isControlled) setUncontrolledValue(next);
      onValueChange?.(next);
    },
    [isControlled, onValueChange]
  );

  const ctx = useMemo(() => ({ value, setValue, idPrefix }), [value, setValue, idPrefix]);

  return (
    <TabsContext.Provider value={ctx}>
      <div className={className} {...props}>
        {children}
      </div>
    </TabsContext.Provider>
  );
}

export function TabsList({
  children,
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  // Roving focus per the APG tabs pattern: arrows move between tabs and
  // activate them; Home/End jump to the ends.
  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const keys = ['ArrowLeft', 'ArrowRight', 'Home', 'End'];
    if (!keys.includes(e.key)) return;
    const list = e.currentTarget;
    const tabs = Array.from(
      list.querySelectorAll<HTMLButtonElement>('[role="tab"]:not([disabled])')
    );
    const current = tabs.indexOf(document.activeElement as HTMLButtonElement);
    if (current === -1) return;
    e.preventDefault();
    let next = current;
    if (e.key === 'ArrowRight') next = (current + 1) % tabs.length;
    if (e.key === 'ArrowLeft') next = (current - 1 + tabs.length) % tabs.length;
    if (e.key === 'Home') next = 0;
    if (e.key === 'End') next = tabs.length - 1;
    tabs[next]?.focus();
    tabs[next]?.click();
  };

  return (
    <div
      role="tablist"
      onKeyDown={handleKeyDown}
      className={cn(
        'flex w-full flex-wrap items-end gap-1 border-b border-lsc-border dark:border-earth-700',
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

interface TabsTriggerProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string;
}

export function TabsTrigger({
  value,
  children,
  className,
  onClick,
  ...props
}: TabsTriggerProps) {
  const ctx = useTabsContext('TabsTrigger');
  const isActive = ctx.value === value;
  return (
    <button
      type="button"
      role="tab"
      id={`${ctx.idPrefix}-tab-${value}`}
      aria-selected={isActive}
      aria-controls={`${ctx.idPrefix}-panel-${value}`}
      tabIndex={isActive ? 0 : -1}
      data-state={isActive ? 'active' : 'inactive'}
      data-value={value}
      className={cn(
        '-mb-px whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-medium transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-accent focus-visible:ring-offset-2 rounded-t-sm',
        isActive
          ? 'border-lsc-accent text-lsc-dark dark:text-lsc-cream'
          : 'border-transparent text-lsc-dark/70 dark:text-lsc-cream/60 hover:text-lsc-dark dark:hover:text-lsc-cream hover:border-lsc-border dark:hover:border-earth-700',
        className
      )}
      onClick={(e) => {
        ctx.setValue(value);
        onClick?.(e);
      }}
      {...props}
    >
      {children}
    </button>
  );
}

interface TabsContentProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
}

export function TabsContent({
  value,
  children,
  className,
  ...props
}: TabsContentProps) {
  const ctx = useTabsContext('TabsContent');
  if (ctx.value !== value) return null;
  return (
    <div
      role="tabpanel"
      id={`${ctx.idPrefix}-panel-${value}`}
      aria-labelledby={`${ctx.idPrefix}-tab-${value}`}
      data-state="active"
      data-value={value}
      className={cn('mt-6 focus-visible:outline-none', className)}
      {...props}
    >
      {children}
    </div>
  );
}
