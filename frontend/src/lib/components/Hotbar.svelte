<script lang="ts">
  import { selectedColor, recentColors } from "$lib/stores";
  import { pushRecentColor } from "$lib/utils";

  function pick(color: string) {
    selectedColor.set(color);
    pushRecentColor(color);
  }
</script>

<div class="color-hotbar">
  <div class="controls" role="toolbar" aria-label="colors">
    {#each $recentColors as c}
      <button
        class="swatch { $selectedColor === c ? 'active' : '' }"
        title={c}
        style="background: {c}"
        on:click={() => pick(c)}
        aria-label={"color " + c}
      ></button>
    {/each}
  </div>
</div>

<style>
  .color-hotbar {
    position: fixed;
    left: 50%;
    bottom: 16px;
    transform: translateX(-50%);
    z-index: 400;
    display: flex;
    gap: 10px;
    align-items: center;
  }

  .swatch {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.18);
    border: 2px solid rgba(255, 255, 255, 0.6);
    cursor: pointer;
  }

  .swatch.active {
    width: 48px;
    height: 48px;
  }

  .controls {
    display: flex;
    gap: 8px;
    align-items: center;
    padding: 8px;
    background: rgba(255, 255, 255, 0.85);
    backdrop-filter: blur(6px);
    border-radius: 12px;
  }
</style>
