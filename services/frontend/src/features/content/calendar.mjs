export function sortByDueDate(items) {
  return [...items].sort((a, b) => {
    const aTime = a.due_at ? new Date(a.due_at).getTime() : Number.POSITIVE_INFINITY;
    const bTime = b.due_at ? new Date(b.due_at).getTime() : Number.POSITIVE_INFINITY;
    if (aTime !== bTime) return aTime - bTime;
    return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
  });
}

export function calendarBucket(item, now = new Date()) {
  if (!item.due_at) return "Later";
  const due = new Date(item.due_at);
  const today = new Date(now);
  today.setHours(0, 0, 0, 0);
  const tomorrow = new Date(today);
  tomorrow.setDate(today.getDate() + 1);
  const dueDay = new Date(due);
  dueDay.setHours(0, 0, 0, 0);
  if (dueDay < today) return "Overdue";
  if (dueDay.getTime() === today.getTime()) return "Today";
  if (dueDay.getTime() === tomorrow.getTime()) return "Tomorrow";
  return "Later";
}
