<script lang="ts">
  import type { Snippet } from "svelte";

  let {
    isOpen = false,
    onClose,
    title = "",
    maxWidth = "400px",
    children,
  }: {
    isOpen: boolean;
    onClose: () => void;
    title?: string;
    maxWidth?: string;
    children: Snippet;
  } = $props();

  function handleBackdropClick(event: MouseEvent) {
    if ((event.target as HTMLElement).classList.contains("modal-backdrop")) {
      onClose();
    }
  }
</script>

{#if isOpen}
  <div class="modal-backdrop" onclick={handleBackdropClick}>
    <div class="modal" style="max-width: {maxWidth}">
      <div class="modal-header">
        {#if title}
          <h2>{title}</h2>
        {/if}
        <button class="close-button" onclick={onClose}>×</button>
      </div>

      <div class="modal-content">
        {@render children()}
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal {
    background: white;
    border-radius: 12px;
    padding: 32px;
    width: 90%;
    max-height: 85vh;
    overflow-y: auto;
    box-shadow: 0 24px 48px rgba(0, 0, 0, 0.2);
    position: relative;
    color: black;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
  }

  h2 {
    margin: 0;
    font-size: 24px;
    font-weight: 700;
  }

  .close-button {
    position: absolute;
    top: 16px;
    right: 16px;
    background: none;
    border: none;
    font-size: 28px;
    cursor: pointer;
    color: rgba(0, 0, 0, 0.5);
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: all 0.15s;
  }

  .close-button:hover {
    background: rgba(0, 0, 0, 0.1);
    color: rgba(0, 0, 0, 0.8);
  }
</style>
