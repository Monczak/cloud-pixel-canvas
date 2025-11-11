<script lang="ts">
  import { currentUser, isAuthModalOpen } from "$lib/auth-stores";
  import { authApi } from "$lib/api/auth";
  import { onDestroy, onMount } from "svelte";

  let showMenu = false;

  async function fetchCurrentUser() {
    const user = await authApi.getCurrentUser();
    currentUser.set(user);
  }

  async function handleLogout() {
    try {
      await authApi.logout();
      currentUser.set(null);
      showMenu = false;
    } catch (err) {
      console.error("Logout failed:", err);
    }
  }

  function handleWidgetClick() {
    if ($currentUser) {
      showMenu = !showMenu;
    } else {
      isAuthModalOpen.set(true);
    }
  }

  function handleClickOutside(event: MouseEvent) {
    const target = event.target as HTMLElement;
    if (!target.closest(".auth-widget")) {
      showMenu = false;
    }
  }

  onMount(async () => {
    await fetchCurrentUser();
    window.addEventListener("click", handleClickOutside);
  });

  onDestroy(() => {
    if (typeof window === "undefined") return;

    window.removeEventListener("click", handleClickOutside);
  });
</script>

<div class="auth-widget">
  <button class="auth-button" on:click={handleWidgetClick}>
    {#if $currentUser}
      <span class="username">{$currentUser?.username}</span>
    {:else}
      <span>Login</span>
    {/if}
  </button>

  {#if showMenu && $currentUser}
    <div class="menu">
      <div class="menu-item user-info">
        <div class="username-display">{$currentUser.username}</div>
        <div class="email-display">{$currentUser.email}</div>
      </div>
      <button class="menu-item logout-button" on:click={handleLogout}>
        Log Out
      </button>
    </div>
  {/if}
</div>

<style>
  .auth-widget {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 500;
  }

  .auth-button {
    background: rgba(255, 255, 255, 0.9);
    backdrop-filter: blur(6px);
    border: none;
    padding: 10px 20px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    transition: all 0.2s;
    color: black;
  }

  .auth-button:hover {
    background: rgba(255, 255, 255, 1);
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.15);
  }

  .username {
    color: #2563eb;
  }

  .menu {
    position: absolute;
    top: calc(100% + 8px);
    right: 0;
    background: white;
    border-radius: 8px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
    min-width: 200px;
    overflow: hidden;
  }

  .menu-item {
    padding: 12px 16px;
    border: none;
    background: none;
    width: 100%;
    text-align: left;
    cursor: pointer;
    font-size: 14px;
    transition: background 0.15s;
    color: black;
  }

  .menu-item:hover {
    background: rgba(0, 0, 0, 0.05);
  }

  .user-info {
    cursor: default;
    border-bottom: 1px solid rgba(0, 0, 0, 0.1);
  }

  .user-info:hover {
    background: none;
  }

  .username-display {
    font-weight: 600;
    margin-bottom: 4px;
  }

  .email-display {
    font-size: 12px;
    opacity: 0.7;
  }

  .logout-button {
    color: #dc2626;
    font-weight: 600;
  }
</style>