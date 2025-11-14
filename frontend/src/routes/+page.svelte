<script lang="ts">
  import Canvas from "$lib/components/Canvas.svelte";
  import { onMount } from "svelte";

  let { setRefetchCanvas } = $props<{ setRefetchCanvas?: (fn: () => Promise<void>) => void }>();
  let refetchCanvas: (() => Promise<void>) | undefined = $state(undefined);

  onMount(() => {
    if (setRefetchCanvas && refetchCanvas) {
      setRefetchCanvas(refetchCanvas);
    }
  });
</script>

<Canvas>
  {#snippet children({ refetchCanvas: refetch }: { refetchCanvas: () => Promise<void> })}
    {@const _ = (refetchCanvas = refetch)}
  {/snippet}
</Canvas>
