<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import { hovered, view, selectedColor } from "$lib/stores";
  import { get as storeGet } from "svelte/store";
  import { pushRecentColor } from "$lib/utils";

  import { canvasApi, CanvasAPIError, type PixelData } from "$lib/api/canvas";
  import { authApi } from "$lib/api/auth";
  import { currentUser, isAuthModalOpen } from "$lib/auth-stores";

  export let onloaded: (() => void) | undefined = undefined;

  const panThreshold = 10;

  let containerEl: HTMLDivElement;
  let canvasEl: HTMLCanvasElement;
  let overlayEl: HTMLCanvasElement;

  let logicalWidth = 100;
  let logicalHeight = 100;
  let pixels: Record<string, PixelData> = {};

  let scale = 1;
  let tx = 0;
  let ty = 0;

  let dragging = false;
  let dragStart = { x: 0, y: 0 };
  let txStart = 0;
  let tyStart = 0;

  let hasPanned = false;
  let initialTx = 0;
  let initialTy = 0;

  let dpr = 1;
  let addedWindowListeners = false;
  let ws: WebSocket | null = null;

  let hoveredUsername: string | null = null;

  const canvasBackgroundColor = "#ffffff";
  const voidBackgroundColor = "#181a1c";

  function formatTimestamp(unix?: number) {
    if (!unix) return "Just now";
    try {
      return new Date(unix * 1000).toLocaleString();
    } catch {
      return String(unix);
    }
  }

  async function fetchCanvas() {
    try {
      const canvasState = await canvasApi.getCanvas();

      logicalWidth = canvasState.canvas_width;
      logicalHeight = canvasState.canvas_height;
      pixels = canvasState.pixels ?? {};

      draw();
      autoCenterAndFit();
      
      onloaded?.();
    } catch (err) {
      console.error("Canvas fetch error:", err);
    }
  }

  function resizeCanvases() {
    if (!containerEl) return;
    dpr = typeof window !== "undefined" ? window.devicePixelRatio || 1 : 1;

    const cssW = Math.max(1, containerEl.clientWidth);
    const cssH = Math.max(1, containerEl.clientHeight);

    for (const el of [canvasEl, overlayEl]) {
      el.width = Math.round(cssW * dpr);
      el.height = Math.round(cssH * dpr);
      el.style.width = cssW + "px";
      el.style.height = cssH + "px";
    }
  }

  function computeScaleLimits() {
    if (!containerEl) return { min: 1, max: 1000 };
    const cssW = containerEl.clientWidth;
    const cssH = containerEl.clientHeight;
    const longer = Math.max(cssW, cssH);
    return {
      min: 1,
      max: Math.max(1, Math.floor(longer * 0.1))
    };
  }

  function clampScale(s: number) {
    const { min, max } = computeScaleLimits();
    return Math.min(max, Math.max(min, s));
  }

  function clampPan() {
    if (!containerEl) return;
    const cssW = containerEl.clientWidth;
    const cssH = containerEl.clientHeight;
    const worldW = logicalWidth * scale;
    const worldH = logicalHeight * scale;

    const slack = 30;

    const limit = (world: number, css: number) =>
      world >= css
        ? [css - world, 0]
        : [0, css - world];

    const [minTx, maxTx] = limit(worldW, cssW);
    const [minTy, maxTy] = limit(worldH, cssH);

    tx = Math.min(maxTx + slack, Math.max(minTx - slack, tx));
    ty = Math.min(maxTy + slack, Math.max(minTy - slack, ty));

    view.set({ scale, tx, ty });
  }

  function drawBase(ctx: CanvasRenderingContext2D) {
    ctx.fillStyle = canvasBackgroundColor;
    ctx.fillRect(0, 0, logicalWidth, logicalHeight);

    for (const p of Object.values(pixels)) {
      ctx.fillStyle = p.color;
      ctx.fillRect(p.x, p.y, 1, 1);
    }
  }

  function draw() {
    resizeCanvases();
    const ctx = canvasEl?.getContext("2d");
    if (!ctx) return;

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = voidBackgroundColor;
    ctx.fillRect(0, 0, canvasEl.width, canvasEl.height);

    ctx.setTransform(scale * dpr, 0, 0, scale * dpr, tx * dpr, ty * dpr);
    ctx.imageSmoothingEnabled = false;

    drawBase(ctx);
    paintOverlay();
  }

  function paintOverlay() {
    const ctx = overlayEl?.getContext("2d");
    if (!ctx) return;

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, overlayEl.width, overlayEl.height);

    const hov = storeGet(hovered);
    if (!hov) return;

    const sx = hov.x * scale + tx;
    const sy = hov.y * scale + ty;
    const sw = Math.max(1, scale);

    const psx = sx * dpr;
    const psy = sy * dpr;
    const psw = sw * dpr;

    ctx.lineWidth = Math.max(1, Math.floor(psw * 0.08));
    ctx.strokeStyle = "rgba(0,0,0,0.9)";
    ctx.strokeRect(psx + 0.5, psy + 0.5, psw - 1, psw - 1);

    ctx.lineWidth = Math.max(1, Math.floor(psw * 0.04));
    ctx.strokeStyle = "rgba(255,255,255,0.95)";
    ctx.strokeRect(psx + 1.5, psy + 1.5, psw - 3, psw - 3);
  }

  function screenToLogical(clientX: number, clientY: number) {
    const rect = containerEl.getBoundingClientRect();
    const cssX = clientX - rect.left;
    const cssY = clientY - rect.top;
    return {
      x: (cssX - tx) / scale,
      y: (cssY - ty) / scale,
      cssX,
      cssY
    };
  }

  function handlePointerDown(e: PointerEvent) {
    containerEl.setPointerCapture?.(e.pointerId);
    hasPanned = false;
    dragging = true;
    dragStart = { x: e.clientX, y: e.clientY };
    txStart = tx;
    tyStart = ty;
  }

  async function handlePointerMove(e: PointerEvent) {
    const logical = screenToLogical(e.clientX, e.clientY);
    const lx = Math.floor(logical.x);
    const ly = Math.floor(logical.y);

    if (lx >= 0 && lx < logicalWidth && ly >= 0 && ly < logicalHeight) {
      const key = `${lx}_${ly}`;
      const pixelData = pixels[key];
      hovered.set({
        x: lx,
        y: ly,
        data: pixelData,
        clientX: e.clientX,
        clientY: e.clientY
      });

      if (pixelData?.userId) {
        hoveredUsername = await authApi.getUsernameById(pixelData.userId);
      }
      else {
        hoveredUsername = null;
      }
    } else {
      hovered.set(null);
      hoveredUsername = null;
    }
    paintOverlay();

    if (!dragging) return;

    const dx = e.clientX - dragStart.x;
    const dy = e.clientY - dragStart.y;
    tx = txStart + dx;
    ty = tyStart + dy;

    if (Math.abs(dx) >= panThreshold || Math.abs(dy) >= panThreshold) {
      hasPanned = true;
    }

    clampPan();
    draw();
  }

  function handlePointerUp(e: PointerEvent) {
    containerEl.releasePointerCapture?.(e.pointerId);
    dragging = false;
  }

  function handlePointerLeave() {
    hovered.set(null);
    hoveredUsername = null;
    paintOverlay();
  }

  function handleWheel(e: WheelEvent) {
    e.preventDefault();
    const rect = containerEl.getBoundingClientRect();
    const cssCx = e.clientX - rect.left;
    const cssCy = e.clientY - rect.top;

    const zoomFactor = Math.exp(-e.deltaY * 0.0012);
    const prevScale = scale;
    const newScale = clampScale(prevScale * zoomFactor);

    const lx = (cssCx - tx) / prevScale;
    const ly = (cssCy - ty) / prevScale;
    tx = cssCx - lx * newScale;
    ty = cssCy - ly * newScale;

    scale = newScale;
    clampPan();
    draw();
  }

  function autoCenterAndFit() {
    const cssW = containerEl.clientWidth;
    const cssH = containerEl.clientHeight;
    const fitScale = Math.min(cssW / logicalWidth, cssH / logicalHeight);

    scale = clampScale(Math.max(1, fitScale * 0.95));
    tx = (cssW - logicalWidth * scale) / 2;
    ty = (cssH - logicalHeight * scale) / 2;

    initialTx = tx;
    initialTy = ty;
    hasPanned = false;
    clampPan();
    view.set({ scale, tx, ty });
    draw();
  }

  async function handleClick(e: MouseEvent) {
    if (e.button !== 0) return;
    if (hasPanned) return;

    const l = screenToLogical(e.clientX, e.clientY);
    const lx = Math.floor(l.x);
    const ly = Math.floor(l.y);
    if (lx < 0 || lx >= logicalWidth || ly < 0 || ly >= logicalHeight) return;

    const user = storeGet(currentUser);
    if (!user) {
      isAuthModalOpen.set(true);
      return;
    }

    const color = storeGet(selectedColor) ?? "#0000FF";
    const key = `${lx}_${ly}`;
    const previousPixel = pixels[key]; // Backup for optimistic rollback

    // Optimistic UI update
    pixels[key] = {
      x: lx,
      y: ly,
      color: color,
      userId: user.user_id,
      timestamp: 0 // 0 indicates "Just now" / pending
    };
    draw();
    pushRecentColor(color);

    try {
      const pixelData = await canvasApi.placePixel(lx, ly, color);
      // Confirm update with server data
      pixels[key] = pixelData;
      draw();
    } catch (err) {
      // Revert on failure
      if (previousPixel) {
        pixels[key] = previousPixel;
      } else {
        delete pixels[key];
      }
      draw();

      if (err instanceof CanvasAPIError && err.statusCode === 401) {  
        currentUser.set(null);
        isAuthModalOpen.set(true);
      } else {
        console.error("Couldn't place pixel:", err);
      } 
    }
  }

  function setupWebSocket() {
    try {
      ws = canvasApi.createWebSocket();

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          
          if (msg.intent === "pixel") {
            const p = msg.payload as PixelData;
            pixels[`${p.x}_${p.y}`] = p;
            draw();
          } else if (msg.intent === "bulk_update") {
            const bulkPixels = msg.payload.pixels;
            for (const [key, pixelData] of Object.entries(bulkPixels)) {
              pixels[key] = pixelData as PixelData;
            }
            draw();
          } else if (msg.intent === "bulk_overwrite") {
            const bulkPixels = msg.payload.pixels;
            pixels = {};
            for (const [key, pixelData] of Object.entries(bulkPixels)) {
              pixels[key] = pixelData as PixelData;
            }
            draw();
          } 
        } catch (err) {
          console.error("WebSocket message error:", err);
        }
      };

      ws.onclose = () => ws = null;
      ws.onerror = (e) => console.error("WebSocket error:", e);
    } catch (err) {
      console.error("Couldn't setup WebSocket:", err);
    }
  }

  let resizeObserver: ResizeObserver | null = null;

  onMount(() => {
    if (typeof window === "undefined") return;

    resizeCanvases();
    
    fetchCanvas();
    setupWebSocket();

    resizeObserver = new ResizeObserver(() => {
      resizeCanvases();
      draw();
    });
    resizeObserver.observe(containerEl);

    containerEl.addEventListener("pointerdown", handlePointerDown);
    containerEl.addEventListener("pointermove", handlePointerMove);
    containerEl.addEventListener("pointerleave", handlePointerLeave);
    containerEl.addEventListener("click", handleClick);
    containerEl.addEventListener("wheel", handleWheel, { passive: false });

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    addedWindowListeners = true;
  });

  onDestroy(() => {
    resizeObserver?.disconnect();

    containerEl?.removeEventListener("pointerdown", handlePointerDown);
    containerEl?.removeEventListener("pointermove", handlePointerMove);
    containerEl?.removeEventListener("pointerleave", handlePointerLeave);
    containerEl?.removeEventListener("click", handleClick);
    containerEl?.removeEventListener("wheel", handleWheel);

    hovered.set(null);

    if (ws) ws.close();

    if (typeof window !== "undefined" && addedWindowListeners) {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
    }
  });
</script>

<div bind:this={containerEl} class="container">
  <canvas bind:this={canvasEl} style="z-index:1; position:absolute; left:0; top:0;"></canvas>
  <canvas bind:this={overlayEl} style="z-index:2; position:absolute; left:0; top:0; pointer-events:none;"></canvas>

  <div class="overlay-slot" style="z-index:3">
    <slot />
  </div>

  {#if $hovered && $hovered.data}
    {#key $hovered.clientX + "-" + $hovered.clientY}
      <div class="tooltip" style="left: {$hovered.clientX}px; top: {$hovered.clientY}px">
        <div><strong>Pixel</strong> {$hovered.x}, {$hovered.y}</div>
        {#if $hovered.data.timestamp === 0}
           <!-- Optimistic Pixel -->
           <div><strong>Placed by</strong> {$currentUser?.username || 'You'}</div>
           <div>Just now</div>
        {:else}
           {#if hoveredUsername}
             <div><strong>Placed by</strong> {hoveredUsername}</div>
           {/if}
           <div>{formatTimestamp($hovered.data.timestamp)}</div>
        {/if}
      </div>
    {/key}
  {/if}
</div>

<style>
  .container {
    position: fixed;
    inset: 0;
    overflow: hidden;
    touch-action: none;
    background: #181a1c;
  }
  canvas {
    image-rendering: pixelated;
    display: block;
    background: transparent;
    width: 100%;
    height: 100%;
  }
  .overlay-slot {
    pointer-events: none;
    position: absolute;
    inset: 0;
  }
  .tooltip {
    position: fixed;
    pointer-events: none;
    background: rgba(255, 255, 255, 0.85);
    color: black;
    font-size: 13px;
    padding: 6px 8px;
    border-radius: 8px;
    white-space: nowrap;
    transform: translate(12px, 12px);
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.18);
    backdrop-filter: blur(6px);
    z-index: 100;
  }
</style>
