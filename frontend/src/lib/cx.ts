/** Class-name joiner usable from server components (the one in components/ui.tsx is client-only). */
export function cx(...parts: (string | false | null | undefined)[]) {
  return parts.filter(Boolean).join(" ");
}
