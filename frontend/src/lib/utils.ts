import { customColors, fixedColors } from "$lib/stores";
import { get } from "svelte/store";

export function pushToCustomPalette(newColor: string) {
  const currentCustom = get(customColors);
  
  if (fixedColors.includes(newColor)) return;

  if (!currentCustom.includes(newColor)) {
      customColors.update(colors => {
          return [newColor, ...colors.slice(0, 9)];
      });
  }
}