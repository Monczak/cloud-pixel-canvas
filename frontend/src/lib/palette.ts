import { writable, derived, get } from "svelte/store";

export type Slot = { type: 'fixed' | 'custom'; index: number };

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

export const customColors = writable<(string | null)[]>(Array(10).fill(null));
export const activeSlot = writable<Slot>({ type: 'fixed', index: 0 });

export const selectedColor = derived(
  [activeSlot, customColors],
  ([$slot, $custom]) => {
    if ($slot.type === 'fixed') {
      return fixedColors[$slot.index];
    }
    // Return custom color, or black if the slot is empty (fallback for painting)
    return $custom[$slot.index] ?? "#000000";
  }
);

export function selectSlot(type: 'fixed' | 'custom', index: number) {
  activeSlot.set({ type, index });
}

export function updateFromColorPicker(newColor: string) {
  const slot = get(activeSlot);
  const custom = get(customColors);
  const upperColor = newColor.toUpperCase();

  if (slot.type === 'fixed') {
    const currentFixed = fixedColors[slot.index].toUpperCase();
    if (currentFixed === upperColor) return;
  }

  if (slot.type === 'custom') {
    const currentCustom = custom[slot.index];
    // The derived store returns #000000 for null slots, so we ignore that specific echo
    if (currentCustom === null && upperColor === "#000000") return;
  }

  if (slot.type === 'custom') {
    customColors.update(colors => {
      colors[slot.index] = upperColor;
      return colors;
    });
  } else {
    let targetIndex = custom.indexOf(null);
    
    if (targetIndex === -1) {
      targetIndex = 0;
    }

    customColors.update(colors => {
      colors[targetIndex] = upperColor;
      return colors;
    });
    activeSlot.set({ type: 'custom', index: targetIndex });
  }
}

export function handlePipettePick(pickedColor: string) {
  const upperColor = pickedColor.toUpperCase();
  const custom = get(customColors);
  const slot = get(activeSlot);

  // If color exists in Fixed palette, select it
  const fixedIndex = fixedColors.findIndex(c => c.toUpperCase() === upperColor);
  if (fixedIndex !== -1) {
    selectSlot('fixed', fixedIndex);
    return;
  }

  // If color exists in Custom palette, select it
  const customIndex = custom.findIndex(c => c?.toUpperCase() === upperColor);
  if (customIndex !== -1) {
    selectSlot('custom', customIndex);
    return;
  }

  // Color not in palette: fill next empty slot
  const emptyIndex = custom.indexOf(null);
  if (emptyIndex !== -1) {
    customColors.update(colors => {
      colors[emptyIndex] = upperColor;
      return colors;
    });
    selectSlot('custom', emptyIndex);
    return;
  }

  // No empty slots: overwrite current swatch
  if (slot.type === 'custom') {
    customColors.update(colors => {
      colors[slot.index] = upperColor;
      return colors;
    });
  } else {
    customColors.update(colors => {
      colors[0] = upperColor;
      return colors;
    });
    selectSlot('custom', 0);
  }
}