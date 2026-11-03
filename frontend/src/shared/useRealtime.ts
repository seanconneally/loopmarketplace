import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { mutation, request } from '../api/client';

export function useRealtime(userId: string | undefined) {
  const queryClient = useQueryClient();
  useEffect(() => {
    if (!userId) return;
    let stopped = false;
    let socket: WebSocket | null = null;
    let timer = 0;
    let watchdog = 0;
    let delay = 1000;
    async function connect() {
      try {
        const { ticket } = await request<{ ticket: string }>('/auth/ws-ticket', mutation({}));
        if (stopped) return;
        socket = new WebSocket(
          `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws`,
        );
        socket.onopen = () => {
          socket?.send(JSON.stringify({ ticket }));
          // Redis pub/sub is ephemeral: restore state from durable API data.
          for (const key of [
            'messages',
            'viewings',
            'conversations',
            'feed',
            'feed-options',
            'seller-listings',
            'saved',
          ])
            void queryClient.invalidateQueries({ queryKey: [key] });
          armWatchdog();
        };
        socket.onmessage = (message: MessageEvent<string>) => {
          delay = 1000;
          armWatchdog();
          const event = JSON.parse(message.data) as {
            type: string;
            data: {
              conversation_id?: string;
              listing_id?: string;
              viewing?: { conversation_id: string };
            };
          };
          if (event.type === 'heartbeat') return;
          const conversation = event.data.conversation_id || event.data.viewing?.conversation_id;
          if (conversation) {
            void queryClient.invalidateQueries({ queryKey: ['messages', conversation] });
            void queryClient.invalidateQueries({ queryKey: ['viewings', conversation] });
            void queryClient.invalidateQueries({ queryKey: ['conversations'] });
          }
          if (event.type === 'block.changed') {
            for (const key of ['messages', 'viewings', 'conversations', 'saved'])
              void queryClient.invalidateQueries({ queryKey: [key] });
          }
          if (['listing.status', 'block.changed'].includes(event.type))
            void queryClient.invalidateQueries({ queryKey: ['feed'] });
          if (event.type === 'listing.status') {
            void queryClient.invalidateQueries({ queryKey: ['listing', event.data.listing_id] });
            void queryClient.invalidateQueries({ queryKey: ['feed-options'] });
            void queryClient.invalidateQueries({ queryKey: ['seller-listings'] });
            void queryClient.invalidateQueries({ queryKey: ['saved'] });
          }
        };
        socket.onclose = retry;
      } catch {
        retry();
      }
    }
    function armWatchdog() {
      window.clearTimeout(watchdog);
      watchdog = window.setTimeout(() => socket?.close(), 45000);
    }
    function retry() {
      window.clearTimeout(watchdog);
      window.clearTimeout(timer);
      if (!stopped) {
        timer = window.setTimeout(() => void connect(), delay * (0.8 + Math.random() * 0.4));
        delay = Math.min(30000, delay * 2);
      }
    }
    void connect();
    return () => {
      stopped = true;
      window.clearTimeout(timer);
      window.clearTimeout(watchdog);
      socket?.close();
    };
  }, [queryClient, userId]);
}
