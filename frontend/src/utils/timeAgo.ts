/** "12 min ago", "3 hours ago", "yesterday": how long ago a conversation was last active. */
export function describeGap(minutes?: number | null, lastActive?: string | null): string {
  let mins = typeof minutes === "number" ? minutes : null;
  if (mins === null && lastActive) {
    const t = new Date(lastActive).getTime();
    if (!Number.isNaN(t)) mins = Math.max(0, (Date.now() - t) / 60000);
  }
  if (mins === null) return "earlier";
  if (mins < 60) return `${Math.max(1, Math.round(mins))} min ago`;
  const hours = mins / 60;
  if (hours < 24) return `${Math.round(hours)} hour${Math.round(hours) === 1 ? "" : "s"} ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "yesterday";
  if (days < 7) return `${days} days ago`;
  return "over a week ago";
}
