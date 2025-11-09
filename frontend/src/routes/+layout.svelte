<script lang="ts">
  import favicon from "$lib/assets/favicon.svg";
  import Status from "$lib/components/Status.svelte";
  import ColorHotbar from "$lib/components/Hotbar.svelte";

  let { children } = $props();
</script>

<svelte:head>
  <link rel="icon" href={favicon} />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous">
  <link href="https://fonts.googleapis.com/css2?family=Cabin:ital,wght@0,400..700;1,400..700&display=swap" rel="stylesheet">
</svelte:head>

{@render children()}

<Status />
<ColorHotbar />

<style>
  :global(html, body, #svelte) {
    height: 100%;
    margin: 0;
    padding: 0;
    font-family: 'Cabin', sans-serif;
  }
</style>
