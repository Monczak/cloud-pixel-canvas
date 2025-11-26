<script lang="ts">
  import { pipetteMode } from "$lib/stores";
  import { 
    selectedColor, 
    fixedColors, 
    customColors, 
    activeSlot, 
    selectSlot, 
    updateFromColorPicker 
  } from "$lib/palette";
  import { clickOutside } from "$lib/utils";
  import { PaletteSolid, EyeDropperSolid, UploadSolid, Hourglass1Solid } from 'svelte-awesome-icons';
  
  import { currentUser, isAuthModalOpen } from "$lib/auth-stores";
  import { canvasApi, CanvasAPIError } from "$lib/api/canvas";
  import ColorPicker from 'svelte-awesome-color-picker';

  export let onCanvasUpdate: (() => Promise<void>) | undefined = undefined;

  let fileInput: HTMLInputElement;
  let uploading = false;
  let uploadError = "";

  let showColorPicker = false;

  function togglePipette() {
    pipetteMode.update(v => !v);
  }
  
  function toggleColorPicker() {
    showColorPicker = !showColorPicker;
  }
  
  function closeColorPicker() {
    showColorPicker = false;
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

<div class="hotbar-container">
  <div class="glass-panel controls">
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
      
      <div class="relative-tool" use:clickOutside={closeColorPicker}>
        <button 
          class="icon-btn tool-btn"
          class:active-tool={showColorPicker}
          on:click={toggleColorPicker}
          title="Color Picker"
        >
          <PaletteSolid size=16/>
        </button>

        {#if showColorPicker}
          <div class="picker-popover glass-panel">
            <ColorPicker
              hex={$selectedColor}
              onInput={event => updateFromColorPicker(event.hex!)}
              label=""
              isAlpha={false}
              isDialog={false} 
            />
          </div>
        {/if}
      </div>

      <button 
        class="icon-btn tool-btn"
        class:active-tool={$pipetteMode}
        on:click={togglePipette}
        title="Pipette Tool"
      >
        <EyeDropperSolid size=16/>
      </button>

      <button
        class="icon-btn tool-btn"
        on:click={handleUploadClick}
        disabled={uploading}
        title="Upload Image"
      >
        {#if uploading}
          <span class="spinner"><Hourglass1Solid size=16/></span>
        {:else}
          <UploadSolid size=16/>
        {/if}
      </button>
    </div>
  </div>
  
  {#if uploadError}
    <div class="upload-error glass-panel">{uploadError}</div>
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
  .hotbar-container {
    display: flex;
    flex-direction: column;
    gap: 8px;
    align-items: center;
  }

  .controls {
    display: flex;
    gap: 12px;
    padding: 12px;
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
    border: 2px solid var(--color-text);
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

  .relative-tool {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .picker-popover {
    position: absolute;
    bottom: calc(100% + 24px);
    left: 50%;
    transform: translateX(-50%);
    padding: 8px;
    z-index: 1000;

    --cp-bg-color: transparent;
    --cp-border-color: transparent;
    --cp-input-color: #f3f4f6;
    --cp-text-color: #333333;
    
    color: #333333;
  }

  :global(.picker-popover input) {
    color: #333333 !important;
    background: #f3f4f6 !important;
  }

  .tool-btn {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    border: 1px solid rgba(0, 0, 0, 0.1);
    background: white;
    font-size: 16px;
  }

  .tool-btn:hover:not(:disabled) {
    background: #f0f0f0;
  }

  .tool-btn.active-tool {
    background: var(--color-primary);
    color: white;
    border-color: var(--color-primary);
  }

  .tool-btn.active-tool:hover {
    background: var(--color-primary-hover);
    border-color: var(--color-primary-hover);
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
    color: var(--color-danger);
    padding: 8px 12px;
    font-size: 13px;
    border: 1px solid #fecaca;
  }
</style>
