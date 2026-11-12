/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface OllamaModel {
  name: string;
  size?: number;
  modified_at?: string;
}

export interface OllamaStatus {
  connected: boolean;
  base_url: string;
  models: OllamaModel[];
  error?: string;
}

export interface AIConfig {
  id: number;
  config_key: string;
  config_value: Record<string, unknown>;
  description?: string;
  updated_at?: string;
}

export interface AIStats {
  total_generations: number;
  completed: number;
  failed: number;
  generating: number;
  success_rate: number;
  average_generation_time_ms: number;
  models_used: Record<string, number>;
}

export interface TestResult {
  success: boolean;
  response?: string;
  model?: string;
  generation_time_ms?: number;
  error?: string;
}

export type GuardrailMinorAudience = "all" | "minors_only" | "adults_only";

export interface Guardrail {
  id: number;
  name: string;
  description?: string;
  rule_type: string;
  rule_config: Record<string, unknown>;
  applies_to_tools: string[];
  audience_minor: GuardrailMinorAudience;
  audience_patron_types: string[];
  priority: number;
  enabled: boolean;
}

export interface AllowedModel {
  id: number;
  model_name: string;
  display_name?: string;
  description?: string;
  max_tokens_limit: number;
  allowed_temperature_min: number;
  allowed_temperature_max: number;
  enabled: boolean;
}

export interface UsageLimit {
  id: number;
  role: string;
  daily_limit: number;
  hourly_limit: number;
  max_tokens_per_request: number;
  enabled: boolean;
}

export interface AITool {
  id: number;
  tool_id: string;
  name: string;
  description?: string;
  system_prompt: string;
  temperature: number;
  max_tokens: number;
  model: string;
  icon?: string;
  category?: string;
  enabled: boolean;
  in_library_only: boolean;
  requires_auth: boolean;
  block_for_minors: boolean;
  requires_parental_consent: boolean;
  block_for_patron_types: string[];
  sort_order: number;
  usage_count: number;
}

export interface UsageLogEntry {
  id: number;
  user_id?: number;
  tool_id?: string;
  model_used?: string;
  prompt_preview?: string;
  response_preview?: string;
  generation_time_ms?: number;
  guardrails_triggered: number[];
  was_blocked: boolean;
  block_reason?: string;
  success: boolean;
  created_at?: string;
}

export interface UsageSummary {
  period_days: number;
  total_requests: number;
  successful: number;
  blocked: number;
  failed: number;
  block_rate: number;
  avg_generation_time_ms: number;
  tool_usage: Record<string, { total: number; blocked: number; tokens: number }>;
  guardrail_hits: Record<string, number>;
}

export type TabId = "status" | "tools" | "guardrails" | "models" | "limits" | "config" | "test" | "audit";
