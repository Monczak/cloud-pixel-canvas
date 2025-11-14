<script lang="ts">
  import Modal from "./Modal.svelte";
  import { isAuthModalOpen, authModalMode, currentUser, pendingVerificationEmail } from "$lib/auth-stores";
  import { authApi, AuthAPIError } from "$lib/api/auth";

  let email = "";
  let username = "";
  let password = "";
  let confirmPassword = "";
  let verificationCode = "";
  
  let error = "";
  let loading = false;

  function closeModal() {
    isAuthModalOpen.set(false);
    error = "";

    email = "";
    username = "";
    password = "";
    confirmPassword = "";
    verificationCode = "";
  }

  async function handleLogin() {
    if (!email || !password) {
      error = "Please fill in all fields";
      return;
    }

    loading = true;
    error = "";

    try {
      const res = await authApi.login(email, password);
      currentUser.set(res.user);
      closeModal();
    } catch (err) {
      if (err instanceof AuthAPIError) {
        error = err.message;
      } else {
        error = "Login failed";
      }
    } finally {
      loading = false;
    }
  }

  async function handleRegister() {
    if (!email || !username || !password || !confirmPassword) {
      error = "Please fill in all fields";
      return;
    }

    if (password !== confirmPassword) {
      error = "Passwords do not match";
      return;
    }

    if (password.length < 8) {
      error = "Password must be at least 8 characters";
      return;
    }

    if (username.length < 3) {
      error = "Username must be at least 3 characters";
      return;
    }

    loading = true;
    error = "";

    try {
      await authApi.register(email, username, password);
      pendingVerificationEmail.set(email);
      switchToVerify();
    } catch (err) {
      if (err instanceof AuthAPIError) {
        error = err.message;
      } else {
        error = "Registration failed";
      }
    } finally {
      loading = false;
    }
  }

  async function handleVerify() {
    if (!verificationCode) {
      error = "Please enter the verification code";
      return;
    }

    loading = true;
    error = "";

    try {
      await authApi.verify($pendingVerificationEmail, verificationCode);

      switchToLogin();
      email = $pendingVerificationEmail;
    } catch (err) {
      if (err instanceof AuthAPIError) {
        error = err.message;
      } else {
        error = "Registration failed";
      }
    } finally {
      loading = false;
    }
  }

  function switchToLogin() {
    authModalMode.set("login");
    error = "";
  }

  function switchToRegister() {
    authModalMode.set("register");
    error = "";
  }

  function switchToVerify() {
    authModalMode.set("verify");
    error = "";
  }

  $: modalTitle = $authModalMode === "login" ? "Log In" : 
                  $authModalMode === "register" ? "Register" : 
                  "Verify Email";
</script>

<Modal isOpen={$isAuthModalOpen} onClose={closeModal} title={modalTitle}>
  {#if $authModalMode === "login"}
    <form
      on:submit={(e) => {
        e.preventDefault();
        handleLogin();
      }}
    >
      <div class="form-group">
        <label for="email">Email</label>
        <input
          id="email"
          type="email"
          bind:value={email}
          placeholder="your@email.com"
          disabled={loading}
        />
      </div>

      <div class="form-group">
        <label for="password">Password</label>
        <input
          id="password"
          type="password"
          bind:value={password}
          placeholder="••••••••"
          disabled={loading}
        />
      </div>

      {#if error}
        <div class="error">{error}</div>
      {/if}

      <button type="submit" class="submit-button" disabled={loading}>
        {loading ? "Logging in..." : "Log In"}
      </button>

      <div class="switch-mode">
        Don't have an account?
        <button type="button" class="link-button" on:click={switchToRegister}>
          Register
        </button>
      </div>
    </form>
  {:else if $authModalMode === "register"}
    <form
      on:submit={(e) => {
        e.preventDefault();
        handleRegister();
      }}
    >
      <div class="form-group">
        <label for="reg-email">Email</label>
        <input
          id="reg-email"
          type="email"
          bind:value={email}
          placeholder="your@email.com"
          disabled={loading}
        />
      </div>

      <div class="form-group">
        <label for="username">Username</label>
        <input
          id="username"
          type="text"
          bind:value={username}
          placeholder="username"
          minlength="3"
          maxlength="20"
          disabled={loading}
        />
      </div>

      <div class="form-group">
        <label for="reg-password">Password</label>
        <input
          id="reg-password"
          type="password"
          bind:value={password}
          placeholder="••••••••"
          minlength="8"
          disabled={loading}
        />
      </div>

      <div class="form-group">
        <label for="confirm-password">Confirm Password</label>
        <input
          id="confirm-password"
          type="password"
          bind:value={confirmPassword}
          placeholder="••••••••"
          disabled={loading}
        />
      </div>

      {#if error}
        <div class="error">{error}</div>
      {/if}

      <button type="submit" class="submit-button" disabled={loading}>
        {loading ? "Registering..." : "Register"}
      </button>

      <div class="switch-mode">
        Already have an account?
        <button type="button" class="link-button" on:click={switchToLogin}>
          Log In
        </button>
      </div>
    </form>
  {:else if $authModalMode === "verify"}
    <p class="verify-info">
      We've sent a verification code to <strong>{$pendingVerificationEmail}</strong>.
      Enter it below to complete registration.
    </p>
    <form
      on:submit={(e) => {
        e.preventDefault();
        handleVerify();
      }}
    >
      <div class="form-group">
        <label for="code">Verification Code</label>
        <input
          id="code"
          type="text"
          bind:value={verificationCode}
          placeholder="123456"
          disabled={loading}
        />
      </div>

      {#if error}
        <div class="error">{error}</div>
      {/if}

      <button type="submit" class="submit-button" disabled={loading}>
        {loading ? "Verifying..." : "Verify"}
      </button>

      <div class="switch-mode">
        <button type="button" class="link-button" on:click={switchToLogin}>
          Back to Login
        </button>
      </div>
    </form>
  {/if}
</Modal>

<style>
  .form-group {
    margin-bottom: 20px;
  }

  label {
    display: block;
    margin-bottom: 8px;
    font-weight: 600;
    font-size: 14px;
  }

  input {
    width: 100%;
    padding: 10px 12px;
    border: 2px solid rgba(0, 0, 0, 0.1);
    border-radius: 8px;
    font-size: 14px;
    transition: border-color 0.15s;
    box-sizing: border-box;
  }

  input:focus {
    outline: none;
    border-color: #2563eb;
  }

  input:disabled {
    background: rgba(0, 0, 0, 0.05);
    cursor: not-allowed;
  }

  .submit-button {
    width: 100%;
    padding: 12px;
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
  }

  .submit-button:hover:not(:disabled) {
    background: #1d4ed8;
  }

  .submit-button:disabled {
    background: rgba(0, 0, 0, 0.2);
    cursor: not-allowed;
  }

  .error {
    background: #fef2f2;
    color: #dc2626;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 16px;
    font-size: 14px;
    border: 1px solid #fecaca;
  }

  .switch-mode {
    text-align: center;
    margin-top: 16px;
    font-size: 14px;
    color: rgba(0, 0, 0, 0.7);
  }

  .link-button {
    background: none;
    border: none;
    color: #2563eb;
    font-weight: 600;
    cursor: pointer;
    padding: 0;
    text-decoration: underline;
  }

  .link-button:hover {
    color: #1d4ed8;
  }

  .verify-info {
    margin-bottom: 24px;
    font-size: 14px;
    line-height: 1.6;
    color: rgba(0, 0, 0, 0.7);
  }
</style>