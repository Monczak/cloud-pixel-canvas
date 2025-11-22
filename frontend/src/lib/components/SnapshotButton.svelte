<script lang="ts">
  import SnapshotGallery from "./SnapshotGallery.svelte";

  let gallery: SnapshotGallery;

  function openGallery() {
    gallery?.open();
  }
</script>

<button class="glass-panel icon-btn snapshot-button" on:click={openGallery} title="Open Snapshots">
  <span class="icon">📷</span>
</button>

<SnapshotGallery bind:this={gallery} />

<style>
  .snapshot-button {
    width: 56px;
    height: 56px;
    font-size: 24px;
  }

  .snapshot-button:hover {
    background: rgba(255, 255, 255, 1);
  }
</style>
