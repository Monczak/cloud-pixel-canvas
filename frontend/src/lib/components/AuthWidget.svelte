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
  <button class="glass-panel auth-button icon-btn" on:click={handleWidgetClick}>
    {#if $currentUser}
      <span class="username">{$currentUser?.username}</span>
    {:else}
      <span>Login</span>
    {/if}
  </button>

  {#if showMenu && $currentUser}
    <div class="glass-panel menu">
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
    position: relative;
    z-index: 500;
  }

  .auth-button {
    padding: 8px 16px;
    font-size: 14px;
    font-weight: 600;
    height: 40px;
  }

  .auth-button:hover {
    background: rgba(255, 255, 255, 1);
  }

  .username {
    color: var(--color-primary);
  }

  .menu {
    position: absolute;
    top: calc(100% + 8px);
    right: 0;
    background: white; /* Override glass for menu readability */
    min-width: 200px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
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
    color: var(--color-text);
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
    margin-bottom: 2px;
  }

  .email-display {
    font-size: 12px;
    opacity: 0.7;
  }

  .logout-button {
    color: var(--color-danger);
    font-weight: 600;
  }
</style>
