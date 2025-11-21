<script lang="ts">
  import { 
    selectedColor, 
    fixedColors, 
    customColors, 
    pipetteMode, 
    activeSlot,
    selectSlot,
    updateFromColorPicker
  } from "$lib/stores";
  
  import { currentUser, isAuthModalOpen } from "$lib/auth-stores";
  import { canvasApi, CanvasAPIError } from "$lib/api/canvas";
  import ColorPicker from 'svelte-awesome-color-picker';

  export let onCanvasUpdate: (() => Promise<void>) | undefined = undefined;

  let fileInput: HTMLInputElement;
  let uploading = false;
  let uploadError = "";

  function togglePipette() {
    pipetteMode.update(v => !v);
  }

  function handleUploadClick() {
    if (!$currentUser) {
      isAuthModalOpen.set(true);
      return;
    }
    fileInput.click();
  }

  async function handleFileChange(event: Event) {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      uploadError = "Please select an image file";
      setTimeout(() => uploadError = "", 3000);
      return;
    }

    uploading = true;
    uploadError = "";
    try {
      await canvasApi.overwriteWithImage(file);
      if (onCanvasUpdate) {
        await onCanvasUpdate();
      }
    } catch (err) {
      if (err instanceof CanvasAPIError && err.statusCode === 401) {
          currentUser.set(null);
          isAuthModalOpen.set(true);
      } else {
        uploadError = "Upload failed";
      }
      setTimeout(() => uploadError = "", 3000);
    } finally {
      uploading = false;
      target.value = "";
    }
  }
</script>

<div class="color-hotbar">
  <div class="controls-container">
    <div class="palette-area">
      <div class="swatch-row">
        {#each fixedColors as c, i}
          <button
            class="swatch"
            class:active={$activeSlot.type === 'fixed' && $activeSlot.index === i}
            style="background: {c}"
            on:click={() => selectSlot('fixed', i)}
            aria-label={"fixed color " + c}
            title={c}
          ></button>
        {/each}
      </div>

      <div class="swatch-row">
        {#each $customColors as c, i}
          <button
            class="swatch custom-swatch"
            class:active={$activeSlot.type === 'custom' && $activeSlot.index === i}
            class:empty={c === null}
            style:background={c ?? 'transparent'}
            on:click={() => selectSlot('custom', i)}
            aria-label={c ? "custom color " + c : "empty slot"}
            title={c ?? "Empty slot"}
          ></button>
        {/each}
      </div>
    </div>

    <div class="divider"></div>

    <div class="tools-area">
      <div class="tool-wrapper">
        <ColorPicker
          hex={$selectedColor}
          onInput={event => updateFromColorPicker(event.hex!)}
          label=""
          isAlpha={false}
        />
      </div>

      <button 
        class="tool-button"
        class:active-tool={$pipetteMode}
        on:click={togglePipette}
        title="Pipette Tool"
      >
        🧪
      </button>

      <button
        class="tool-button"
        on:click={handleUploadClick}
        disabled={uploading}
        title="Upload Image"
      >
        {#if uploading}
          <span class="spinner">⏳</span>
        {:else}
          <span>📤</span>
        {/if}
      </button>
    </div>
  </div>
  
  {#if uploadError}
    <div class="upload-error">{uploadError}</div>
  {/if}
</div>

<input
  type="file"
  bind:this={fileInput}
  on:change={handleFileChange}
  accept="image/*"
  style="display: none;"
/>

<style>
  .color-hotbar {
    position: fixed;
    left: 50%;
    bottom: 16px;
    transform: translateX(-50%);
    z-index: 400;
    display: flex;
    flex-direction: column;
    gap: 8px;
    align-items: center;
  }

  .controls-container {
    display: flex;
    gap: 12px;
    padding: 12px;
    background: rgba(255, 255, 255, 0.9);
    backdrop-filter: blur(10px);
    border-radius: 16px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.4);
    align-items: center;
  }

  .palette-area {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .swatch-row {
    display: flex;
    gap: 6px;
  }

  .swatch {
    width: 24px;
    height: 24px;
    border-radius: 6px;
    border: 1px solid rgba(0, 0, 0, 0.15);
    cursor: pointer;
    transition: transform 0.1s, border-color 0.1s;
    padding: 0;
  }

  .swatch.custom-swatch.empty {
    background:
      linear-gradient(45deg, #ccc 25%, transparent 25%), 
      linear-gradient(-45deg, #ccc 25%, transparent 25%), 
      linear-gradient(45deg, transparent 75%, #ccc 75%), 
      linear-gradient(-45deg, transparent 75%, #ccc 75%);
    background-size: 8px 8px;
    background-position: 0 0, 0 4px, 4px -4px, -4px 0px;
    background-color: #eee;
    box-shadow: inset 0 0 4px rgba(0,0,0,0.1);
  }

  .swatch:hover {
    transform: scale(1.1);
    z-index: 1;
  }

  .swatch.active {
    border: 2px solid black;
    transform: scale(1.15);
    z-index: 2;
    box-shadow: 0 2px 6px rgba(0,0,0,0.2);
  }

  .divider {
    width: 1px;
    background: rgba(0, 0, 0, 0.1);
    margin: 0 4px;
    align-self: stretch;
  }

  .tools-area {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 8px;
  }

  .tool-wrapper {
    display: flex;
    justify-content: center;
    align-items: center;
    /* Force readable colors for the library */
    --cp-bg-color: #ffffff;
    --cp-text-color: #333333;
    --cp-input-bg-color: #f3f4f6;
    --cp-border-color: #d1d5db;
    color: #333;
  }

  /* Specific overrides for svelte-awesome-color-picker internals */
  :global(.color-picker-wrapper) {
    display: flex !important;
  }
  
  :global(.vacp-color-picker) {
    background: white !important;
    color: #333 !important;
    font-family: inherit;
  }
  
  :global(.vacp-color-input) {
    color: #333 !important;
    background: #f3f4f6 !important;
    border: 1px solid #ccc !important;
  }

  .tool-button {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    border: 1px solid rgba(0, 0, 0, 0.1);
    background: white;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s;
    color: #444;
  }

  .tool-button:hover:not(:disabled) {
    background: #f0f0f0;
    transform: translateY(-1px);
  }

  .tool-button.active-tool {
    background: #2563eb;
    color: white;
    border-color: #2563eb;
  }

  .tool-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .spinner {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  .upload-error {
    background: #fef2f2;
    color: #dc2626;
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 13px;
    border: 1px solid #fecaca;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }
</style>
