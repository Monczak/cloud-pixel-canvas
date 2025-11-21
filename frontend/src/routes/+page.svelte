<script lang="ts">
  import { onMount } from "svelte";
  import { fade } from "svelte/transition";
  import Canvas from "$lib/components/Canvas.svelte";
  import Hotbar from "$lib/components/Hotbar.svelte";
  import AuthWidget from "$lib/components/AuthWidget.svelte";
  import SnapshotGallery from "$lib/components/SnapshotGallery.svelte";
  import SnapshotButton from "$lib/components/SnapshotButton.svelte";
  import AuthModal from "$lib/components/AuthModal.svelte";
  import Status from "$lib/components/Status.svelte";
  
  import { authApi } from "$lib/api/auth";
  import { currentUser } from "$lib/auth-stores";

  let gallery: SnapshotGallery;
  let loading = true;
  let canvasReady = false;

  onMount(async () => {
    // Start minimum timer for aesthetic purposes
    const minLoadTime = new Promise(resolve => setTimeout(resolve, 800));

    try {
      const user = await authApi.getCurrentUser();
      currentUser.set(user);
    } catch (e) {
      console.log("Not logged in");
    }

    await minLoadTime;
    
    if (canvasReady) {
        loading = false;
    }
  });
  
  let minTimerDone = false;

  onMount(() => {
      setTimeout(() => {
          minTimerDone = true;
          if (canvasReady) loading = false;
      }, 800);

      authApi.getCurrentUser().then(u => currentUser.set(u)).catch(() => {});
  });

  $: if (minTimerDone && canvasReady) {
      loading = false;
  }

  function openGallery() {
    gallery.open();
  }
</script>

<!-- Loading Overlay -->
{#if loading}
  <div class="loading-screen" transition:fade={{ duration: 400 }}>
    <div class="loader-content">
      <p>Getting ready... Sit tight!</p>
    </div>
  </div>
{/if}

<Canvas onloaded={() => canvasReady = true}>
  <!-- UI Overlay Layer passed into Canvas slot -->
  <div class="ui-layer">
    <div class="top-bar">
      <div class="left-controls">
        <Status />
        <SnapshotButton on:click={openGallery} />
      </div>
      <div class="right-controls">
        <AuthWidget />
      </div>
    </div>

    <div class="bottom-bar">
      <Hotbar />
    </div>
  </div>
</Canvas>

<SnapshotGallery bind:this={gallery} />
<AuthModal />

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    background: #181a1c;
    color: white;
    overflow: hidden;
  }

  .ui-layer {
    position: absolute;
    inset: 0;
    pointer-events: none; 
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 16px;
  }

  .top-bar {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }

  .left-controls {
    display: flex;
    flex-direction: column;
    gap: 12px;
    pointer-events: auto;
  }

  .right-controls {
    pointer-events: auto;
  }

  .bottom-bar {
    display: flex;
    justify-content: center;
    padding-bottom: 16px;
    pointer-events: auto;
  }

  .loading-screen {
    position: fixed;
    inset: 0;
    background-color: #181a1c;
    z-index: 9999;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
  }

  .loader-content {
    text-align: center;
  }

  .loader-content p {
    margin-top: 16px;
    font-size: 14px;
    opacity: 0.7;
    font-weight: 500;
  }

  @keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-10px); }
  }
</style>
