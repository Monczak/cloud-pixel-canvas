<script lang="ts">
  import { hovered, view } from "$lib/stores";
  import { derived } from "svelte/store";

  const current = derived([hovered, view], ([$hovered, $view]) => ({
    x: $hovered?.x ?? null,
    y: $hovered?.y ?? null,
    zoom: $view.scale
  }));
</script>

<div class="status">
  <div>
    <div class="label">Cursor</div>
    <div class="value">
      {$current.x !== null ? `${$current.x}, ${$current.y}` : "-"}
    </div>
  </div>
  <div>
    <div class="label">Zoom</div>
    <div class="value">{$current.zoom.toFixed(2)}x</div>
  </div>
</div>

<style>
  .status {
    position: fixed;
    left: 12px;
    bottom: 12px;
    z-index: 300;
    color: black;
    background: rgba(255, 255, 255, 0.85);
    padding: 8px 10px;
    border-radius: 8px;
    font-size: 13px;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.18);
    backdrop-filter: blur(6px);
    display: flex;
    gap: 12px;
    align-items: center;
    min-width: 120px;
  }
  .label {
    opacity: 0.85;
    font-weight: 600;
  }
  .value {
    font-feature-settings: "tnum";
    font-variant-numeric: tabular-nums;
  }
</style>
