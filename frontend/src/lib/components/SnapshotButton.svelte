<script lang="ts">
  import SnapshotGallery from "./SnapshotGallery.svelte";

  let gallery: SnapshotGallery;

  function openGallery() {
    gallery?.open();
  }
</script>

<button class="snapshot-button" on:click={openGallery}>
  <span class="icon">📷</span>
</button>

<SnapshotGallery bind:this={gallery} />

<style>
  .snapshot-button {
    position: fixed;
    right: 16px;
    bottom: 16px;
    z-index: 400;
    width: 56px;
    height: 56px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.9);
    backdrop-filter: blur(6px);
    border: none;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.18);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
  }

  .snapshot-button:hover {
    background: rgba(255, 255, 255, 1);
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.25);
    transform: scale(1.05);
  }

  .icon {
    font-size: 24px;
  }
</style>