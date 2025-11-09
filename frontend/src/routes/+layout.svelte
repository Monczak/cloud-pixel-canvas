<script lang="ts">
  import favicon from "$lib/assets/favicon.svg";
  import Status from "$lib/components/Status.svelte";
  import ColorHotbar from "$lib/components/Hotbar.svelte";

  let { children } = $props();
</script>

<svelte:head>
  <link rel="icon" href={favicon} />
</svelte:head>

{@render children()}

<Status />
<ColorHotbar />

<style>
  :global(html, body, #svelte) {
    height: 100%;
    margin: 0;
    padding: 0;
  }
</style>
