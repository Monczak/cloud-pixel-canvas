import { writable } from "svelte/store";

export type Hover = {
  x: number;
  y: number;
  data?: any;
  color: string;
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
