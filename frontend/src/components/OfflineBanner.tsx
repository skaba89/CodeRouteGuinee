import { useEffect, useState } from 'react';

/**
 * Suit l'état de la connexion réseau (en ligne / hors ligne), réactif.
 * Utile en Guinée où la connectivité est intermittente hors des grandes
 * villes : l'utilisateur sait toujours s'il est connecté.
 */
export function useOnlineStatus(): boolean {
  const [online, setOnline] = useState<boolean>(() =>
    typeof navigator !== 'undefined' ? navigator.onLine : true,
  );
  useEffect(() => {
    const goOnline = () => setOnline(true);
    const goOffline = () => setOnline(false);
    window.addEventListener('online', goOnline);
    window.addEventListener('offline', goOffline);
    return () => {
      window.removeEventListener('online', goOnline);
      window.removeEventListener('offline', goOffline);
    };
  }, []);
  return online;
}

/**
 * Bannière discrète affichée uniquement quand l'utilisateur est hors ligne.
 * Rassure sur ce qui reste possible (entraînement) sans alarmer.
 */
export function OfflineBanner() {
  const online = useOnlineStatus();
  if (online) return null;
  return (
    <div
      role="status"
      style={{
        position: 'sticky', top: 0, zIndex: 900,
        background: '#B8860B', color: '#fff',
        padding: '8px 14px', fontSize: 13, textAlign: 'center',
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
      }}
    >
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M1 1l22 22M16.72 11.06A10.94 10.94 0 0 1 19 12.55M5 12.55a10.94 10.94 0 0 1 5.17-2.39M10.71 5.05A16 16 0 0 1 22.58 9M1.42 9a15.91 15.91 0 0 1 4.7-2.88M8.53 16.11a6 6 0 0 1 6.95 0M12 20h.01" />
      </svg>
      Hors ligne — l'entraînement reste disponible. Réservation et examen
      nécessitent une connexion.
    </div>
  );
}
