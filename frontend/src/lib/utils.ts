import { recentColors } from "$lib/stores";

export function pushRecentColor(color: string) {
  recentColors.update((list) => [
    color,
    ...list.filter((c) => c !== color)
  ].slice(0, 8));
}
