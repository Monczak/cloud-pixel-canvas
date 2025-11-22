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

  let canvasComponent: Canvas;
  let canvasReady = false;
  
  let gallery: SnapshotGallery;
  
  let loading = true;

  async function handleCanvasRefresh() {
    await canvasComponent?.refresh();
  }

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

{#if loading}
  <div class="loading-screen" transition:fade={{ duration: 400 }}>
    <div class="loader-content">
      <p>Getting ready... Sit tight!</p>
    </div>
  </div>
{/if}

<Canvas bind:this={canvasComponent} onloaded={() => canvasReady = true}>
  <div class="ui-layer">
    <div class="top-bar">
      <div class="spacer"></div>
      <div class="pointer-auto">
        <AuthWidget />
      </div>
    </div>

    <div class="bottom-bar">
      <div class="left-slot pointer-auto">
        <Status />
      </div>
      <div class="center-slot pointer-auto">
        <Hotbar onCanvasUpdate={handleCanvasRefresh} />
      </div>
      <div class="right-slot pointer-auto">
        <SnapshotButton on:click={openGallery} />
      </div>
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

  .pointer-auto {
    pointer-events: auto;
  }

  .top-bar {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }

  .bottom-bar {
    display: grid;
    grid-template-columns: 1fr auto 1fr;
    align-items: end;
    width: 100%;
  }

  .left-slot {
    display: flex;
    justify-content: flex-start;
  }

  .center-slot {
    display: flex;
    justify-content: center;
  }

  .right-slot {
    display: flex;
    justify-content: flex-end;
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
</style>
