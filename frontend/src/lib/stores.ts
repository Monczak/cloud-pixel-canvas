import { writable } from "svelte/store";

export type Hover = {
  x: number;
  y: number;
  data?: any;
  clientX: number;
  clientY: number;
} | null;

export const hovered = writable<Hover>(null);
export const view = writable<{ scale: number; tx: number; ty: number }>({
  scale: 1,
  tx: 0,
  ty: 0,
});

export const selectedColor = writable<string>("#0000FF");
export const recentColors = writable<string[]>([
  "#000000",
  "#FFFFFF",
  "#FF0000",
  "#00FF00",
  "#0000FF",
  "#FFFF00",
  "#FF00FF",
  "#00FFFF",
]);
