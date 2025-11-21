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

export const pipetteMode = writable<boolean>(false);
export const selectedColor = writable<string>("#000000");

export const fixedColors = [
  "#000000", // Black
  "#808080", // Gray
  "#FFFFFF", // White
  "#FF0000", // Red
  "#FFA500", // Orange
  "#FFFF00", // Yellow
  "#008000", // Green
  "#00FFFF", // Cyan
  "#0000FF", // Blue
  "#800080", // Purple
];

export const customColors = writable<string[]>(Array(10).fill("#222222")); // Dark gray as placeholder
