import { writable } from "svelte/store";

export type AuthUser = {
    user_id: string;
    email: string;
    username: string;
} | null;

export const currentUser = writable<AuthUser>(null);
export const isAuthModalOpen = writable<boolean>(false);
export const authModalMode = writable<"login" | "register" | "verify">("login");
export const pendingVerificationEmail = writable<string>("");
