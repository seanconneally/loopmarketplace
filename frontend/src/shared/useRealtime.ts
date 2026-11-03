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
    let delay = 1000;
    async function connect() {
      try {
        const { ticket } = await request<{ ticket: string }>('/auth/ws-ticket', mutation({}));
        if (stopped) return;
        socket = new WebSocket(
          `${location.protocol === 'https:' ? 'wss:' : 'ws:'}//${location.host}/ws`,
        );
        socket.onopen = () => {
          delay = 1000;
          socket?.send(JSON.stringify({ ticket }));
        };
        socket.onmessage = (message: MessageEvent<string>) => {
          const event = JSON.parse(message.data) as {
            type: string;
            data: { conversation_id?: string; viewing?: { conversation_id: string } };
          };
          if (event.type === 'heartbeat') return;
          const conversation = event.data.conversation_id || event.data.viewing?.conversation_id;
          if (conversation) {
            void queryClient.invalidateQueries({ queryKey: ['messages', conversation] });
            void queryClient.invalidateQueries({ queryKey: ['viewings', conversation] });
            void queryClient.invalidateQueries({ queryKey: ['conversations'] });
          }
          if (['listing.status', 'block.changed'].includes(event.type))
            void queryClient.invalidateQueries({ queryKey: ['feed'] });
          if (event.type === 'listing.status') {
            void queryClient.invalidateQueries({ queryKey: ['seller-listings'] });
            void queryClient.invalidateQueries({ queryKey: ['saved'] });
          }
        };
        socket.onclose = retry;
      } catch {
        retry();
      }
    }
    function retry() {
      if (!stopped) {
        timer = window.setTimeout(() => void connect(), delay);
        delay = Math.min(30000, delay * 2);
      }
    }
    void connect();
    return () => {
      stopped = true;
      window.clearTimeout(timer);
      socket?.close();
    };
  }, [queryClient, userId]);
}
