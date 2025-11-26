<script lang="ts">
  import { hovered, view } from "$lib/stores";
  import { derived } from "svelte/store";

  const current = derived([hovered, view], ([$hovered, $view]) => ({
    x: $hovered?.x ?? null,
    y: $hovered?.y ?? null,
    zoom: $view.scale,
  }));
</script>

<div class="glass-panel status">
  <div class="item">
    <span class="label">Cursor</span>
    <span class="value">
      {$current.x !== null ? `${$current.x}, ${$current.y}` : "-"}
    </span>
  </div>
  <div class="item">
    <span class="label">Zoom</span>
    <span class="value">{$current.zoom.toFixed(2)}x</span>
  </div>
</div>

<style>
  .status {
    padding: 8px 12px;
    display: flex;
    gap: 16px;
    align-items: center;
    font-size: 13px;
    min-width: 140px;
  }

  .item {
    display: flex;
    flex-direction: column;
  }

  .label {
    font-size: 10px;
    text-transform: uppercase;
    opacity: 0.6;
    font-weight: 700;
    letter-spacing: 0.5px;
  }

  .value {
    font-weight: 600;
    font-feature-settings: "tnum";
    font-variant-numeric: tabular-nums;
  }
</style>
