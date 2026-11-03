import { useEffect, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Wifi, WifiOff, X } from 'lucide-react';
import { useOnlineStatus } from './useOnlineStatus';

export function ConnectionStatus() {
  const online = useOnlineStatus();
  const client = useQueryClient();
  const [recovered, setRecovered] = useState(false);
  useEffect(() => {
    let timer = 0;
    const reconnect = () => {
      setRecovered(true);
      window.clearTimeout(timer);
      timer = window.setTimeout(() => setRecovered(false), 6000);
      // Refresh reads; unfinished forms and messages are not submitted automatically.
      void client.invalidateQueries();
    };
    window.addEventListener('online', reconnect);
    return () => {
      window.removeEventListener('online', reconnect);
      window.clearTimeout(timer);
    };
  }, [client]);
  if (online && !recovered) return null;
  return (
    <div className={`connection-status ${online ? 'reconnected' : ''}`} role="status">
      {online ? <Wifi size={19} /> : <WifiOff size={19} />}
      <span>
        {online
          ? 'Back online. Refreshing your latest updates.'
          : 'You’re offline. Keep editing; reconnect before sending or uploading.'}
      </span>
      {online && (
        <button
          className="icon-button"
          aria-label="Dismiss connection update"
          onClick={() => setRecovered(false)}
        >
          <X size={16} />
        </button>
      )}
    </div>
  );
}
