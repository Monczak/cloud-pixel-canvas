<script lang="ts">
  import favicon from "$lib/assets/favicon.svg";
  import Status from "$lib/components/Status.svelte";
  import ColorHotbar from "$lib/components/Hotbar.svelte";
  import AuthWidget from "$lib/components/AuthWidget.svelte";
  import AuthModal from "$lib/components/AuthModal.svelte";
  import SnapshotButton from "$lib/components/SnapshotButton.svelte";

  let { children } = $props();
  let refetchCanvas: (() => Promise<void>) | undefined = $state(undefined);
</script>

<svelte:head>
  <link rel="icon" href={favicon} />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous">
  <link href="https://fonts.googleapis.com/css2?family=Cabin:ital,wght@0,400..700;1,400..700&display=swap" rel="stylesheet">
</svelte:head>

{@render children()}

<Status />
<ColorHotbar onCanvasUpdate={refetchCanvas} />
<AuthWidget />
<AuthModal />
<SnapshotButton />

<style>
  :global(html, body, #svelte) {
    height: 100%;
    margin: 0;
    padding: 0;
    font-family: 'Cabin', sans-serif;
  }
</style>
