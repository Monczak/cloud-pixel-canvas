<script lang="ts">
  import Modal from "./Modal.svelte";
  import { canvasApi, type Snapshot } from "$lib/api/canvas";

  let isOpen = $state(false);
  let snapshots: Snapshot[] = $state([]);
  let total = $state(0);
  let currentPage = $state(0);
  let loading = $state(false);
  let error = $state("");

  let lastFetchTime = 0;

  const cacheDuration = 60 * 1000;
  const perPage = 12;

  export function open() {
    isOpen = true;
    const now = Date.now();

    if (snapshots.length === 0 || now - lastFetchTime > cacheDuration) {
      currentPage = 0;
      loadSnapshots(0);
    }
  }

  function close() {
    isOpen = false;
  }

  async function loadSnapshots(page: number) {
    loading = true;
    error = "";
    try {
      const response = await canvasApi.getSnapshots(perPage, page * perPage);
      snapshots = response.snapshots;
      total = response.total;
      currentPage = page;

      if (page === 0) {
        lastFetchTime = Date.now();
      }
    } catch (err) {
      error = "Failed to load snapshots";
      console.error(err);
    } finally {
      loading = false;
    }
  }

  async function handleDownload(snapshot: Snapshot) {
    try {
      const response = await fetch(snapshot.image_url);
      if (!response.ok) throw new Error("Download failed");

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = url;
      link.download = `snapshot_${snapshot.snapshot_id}.png`;
      document.body.appendChild(link);
      link.click();

      window.URL.revokeObjectURL(url);
      link.remove();
    } catch (err) {
      console.error("Download failed:", err);
      // Fallback to opening in new tab
      window.open(snapshot.image_url, "_blank");
    }
  }

  function nextPage() {
    const maxPage = Math.ceil(total / perPage) - 1;
    if (currentPage < maxPage) {
      loadSnapshots(currentPage + 1);
    }
  }

  function prevPage() {
    if (currentPage > 0) {
      loadSnapshots(currentPage - 1);
    }
  }

  function formatDate(dateStr: string): string {
    try {
      const date = new Date(dateStr);
      return date.toLocaleString();
    } catch {
      return dateStr;
    }
  }
</script>

<Modal {isOpen} onClose={close} title="Snapshot Gallery" maxWidth="900px">
  {#if loading}
    <div class="loading">Loading snapshots...</div>
  {:else if error}
    <div class="error">{error}</div>
  {:else if snapshots.length === 0}
    <div class="empty">No snapshots yet</div>
  {:else}
    <div class="gallery">
      {#each snapshots as snapshot}
        <div class="snapshot-card">
          <div
            class="thumbnail-container"
            onclick={() => handleDownload(snapshot)}
          >
            <img
              src={snapshot.thumbnail_url}
              alt="Snapshot from {formatDate(snapshot.created_at)}"
              class="thumbnail"
            />
            <div class="overlay">
              <span class="download-icon">⬇</span>
            </div>
          </div>
          <div class="snapshot-info">
            <div class="date">{formatDate(snapshot.created_at)}</div>
            <div class="size">
              {snapshot.canvas_width}×{snapshot.canvas_height}
            </div>
          </div>
        </div>
      {/each}
    </div>

    <div class="pagination">
      <button
        class="page-button"
        disabled={currentPage === 0}
        onclick={prevPage}
      >
        Previous
      </button>
      <span class="page-info">
        Page {currentPage + 1} of {Math.ceil(total / perPage)}
      </span>
      <button
        class="page-button"
        disabled={currentPage >= Math.ceil(total / perPage) - 1}
        onclick={nextPage}
      >
        Next
      </button>
    </div>
  {/if}
</Modal>

<style>
  .loading,
  .error,
  .empty {
    text-align: center;
    padding: 40px;
    font-size: 16px;
  }
  .error {
    color: #dc2626;
  }
  .gallery {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }
  .snapshot-card {
    display: flex;
    flex-direction: column;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid rgba(0, 0, 0, 0.1);
    transition:
      transform 0.15s,
      box-shadow 0.15s;
  }
  .snapshot-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
  }
  .thumbnail-container {
    position: relative;
    width: 100%;
    padding-bottom: 100%;
    background: #f5f5f5;
    cursor: pointer;
    overflow: hidden;
  }
  .thumbnail {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    image-rendering: pixelated;
  }
  .overlay {
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.15s;
  }
  .thumbnail-container:hover .overlay {
    opacity: 1;
  }
  .download-icon {
    font-size: 32px;
    color: white;
  }
  .snapshot-info {
    padding: 12px;
    background: white;
  }
  .date {
    font-size: 13px;
    font-weight: 600;
    margin-bottom: 4px;
  }
  .size {
    font-size: 12px;
    color: rgba(0, 0, 0, 0.6);
  }
  .pagination {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 16px;
    margin-top: 24px;
  }
  .page-button {
    padding: 8px 16px;
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 6px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
  }
  .page-button:hover:not(:disabled) {
    background: #1d4ed8;
  }
  .page-button:disabled {
    background: rgba(0, 0, 0, 0.2);
    cursor: not-allowed;
  }
  .page-info {
    font-size: 14px;
    font-weight: 600;
  }
</style>
