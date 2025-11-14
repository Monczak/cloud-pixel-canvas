<script lang="ts">
  import { selectedColor, recentColors } from "$lib/stores";
  import { pushRecentColor } from "$lib/utils";
  import { currentUser, isAuthModalOpen } from "$lib/auth-stores";
  import { canvasApi, CanvasAPIError } from "$lib/api/canvas";

  export let onCanvasUpdate: (() => Promise<void>) | undefined = undefined;

  let fileInput: HTMLInputElement;
  let uploading = false;
  let uploadError = "";

  function pick(color: string) {
    selectedColor.set(color);
    pushRecentColor(color);
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
      
      // Fetch updated canvas state instead of reloading page
      if (onCanvasUpdate) {
        await onCanvasUpdate();
      }
    } catch (err) {
      if (err instanceof CanvasAPIError) {
        if (err.statusCode === 401) {
          currentUser.set(null);
          isAuthModalOpen.set(true);
        } else {
          uploadError = "Upload failed";
        }
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
    
    <div class="divider"></div>
    
    <button
      class="upload-button"
      on:click={handleUploadClick}
      disabled={uploading}
      title="Upload image to canvas"
      aria-label="Upload image"
    >
      {#if uploading}
        <span class="spinner">⏳</span>
      {:else}
        <span>📤</span>
      {/if}
    </button>
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

  .swatch {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.18);
    border: 2px solid rgba(255, 255, 255, 0.6);
    cursor: pointer;
    transition: all 0.15s;
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

  .divider {
    width: 2px;
    height: 32px;
    background: rgba(0, 0, 0, 0.15);
    margin: 0 4px;
  }

  .upload-button {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    border: 2px solid rgba(0, 0, 0, 0.1);
    background: white;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    transition: all 0.15s;
  }

  .upload-button:hover:not(:disabled) {
    background: #f5f5f5;
    transform: scale(1.05);
  }

  .upload-button:disabled {
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
