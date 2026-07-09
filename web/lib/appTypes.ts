export interface NowTask {
  id: string;
  title: string;
  status: string;
  estimated_minutes: number | null;
  priority: number;
  due_at: string | null;
}

export interface NowContextCards {
  next_event_title: string | null;
  next_event_at: string | null;
  next_event_in_minutes: number | null;
  tasks_due_today: number;
  tasks_completed_today: number;
  energy_level: string | null;
  sleep_hours: number | null;
  current_place: string | null;
  steps: number | null;
  steps_goal: number;
}

export interface NowResponse {
  greeting: string;
  usable_minutes: number;
  best_task: NowTask | null;
  confidence: number | null;
  moment: string | null;
  alternatives: NowTask[];
  context: NowContextCards | null;
}

export interface TaskResponse {
  id: string;
  title: string;
  status: string;
  priority: number;
  estimated_minutes: number | null;
  scheduled_start: string | null;
  scheduled_end: string | null;
  due_at: string | null;
}

/** A task's domain accent — mirrors the native app's colour system. */
export function accentFor(title: string): { color: string; label: string; icon: string } {
  const t = ` ${title.toLowerCase()} `;
  const has = (arr: string[]) => arr.some((w) => t.includes(w));
  if (has(["walk", "run", "gym", "exercise", "workout", "stretch", "break"]))
    return { color: "var(--green)", label: "Health break", icon: "🏃" };
  if (has(["buy", "shop", "store", "grocery", "errand", "mall", "walmart", "target"]))
    return { color: "var(--cyan)", label: "Errand", icon: "🛒" };
  if (has(["meeting", "standup", "sync", "1:1", "appointment", "doctor", "dentist", "acupuncture"]))
    return { color: "var(--violet)", label: "Appointment", icon: "📅" };
  if (has(["email", "reply", "message", "slack", "inbox"]))
    return { color: "var(--cyan)", label: "Low focus", icon: "✉️" };
  if (has(["call", "phone"]))
    return { color: "var(--green)", label: "Quick task", icon: "📞" };
  return { color: "var(--blue)", label: "Focus task", icon: "📄" };
}

export function priorityLabel(p: number): string {
  return p <= 2 ? "High priority" : p === 3 ? "Medium priority" : "Low priority";
}
