"use client";
import { create } from "zustand";
import type { NotificationItem } from "@/types";

interface NotificationState {
  items: NotificationItem[];
  unreadCount: () => number;
  markAllRead: () => void;
  markRead: (id: string) => void;
  push: (item: NotificationItem) => void;
}

/** Notification center state. Starts empty: items arrive through `push` (from a server-sent event source)
 *  and are never invented client-side. */
export const useNotificationStore = create<NotificationState>((set, get) => ({
  items: [],
  unreadCount: () => get().items.filter((n) => !n.read).length,
  markAllRead: () => set((s) => ({ items: s.items.map((n) => ({ ...n, read: true })) })),
  markRead: (id) => set((s) => ({ items: s.items.map((n) => (n.id === id ? { ...n, read: true } : n)) })),
  push: (item) => set((s) => ({ items: [item, ...s.items] })),
}));
