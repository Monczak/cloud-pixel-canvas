<script lang="ts">
  import SnapshotGallery from "./SnapshotGallery.svelte";
  import { CameraSolid } from "svelte-awesome-icons";

  let gallery: SnapshotGallery;

  function openGallery() {
    gallery?.open();
  }
</script>

<button
  class="glass-panel icon-btn snapshot-button"
  on:click={openGallery}
  title="Open Snapshots"
>
  <CameraSolid />
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
