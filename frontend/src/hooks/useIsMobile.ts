import { useEffect, useState } from 'react';

/**
 * Retourne true quand la largeur de l'écran est <= breakpoint (760px par
 * défaut). Réactif : se met à jour au redimensionnement et à la rotation.
 * Utilisé pour adapter les mises en page en style inline (que les media
 * queries CSS ne peuvent pas atteindre).
 */
export function useIsMobile(breakpoint = 760): boolean {
  const [isMobile, setIsMobile] = useState<boolean>(() =>
    typeof window !== 'undefined' ? window.innerWidth <= breakpoint : false,
  );

  useEffect(() => {
    const mq = window.matchMedia(`(max-width: ${breakpoint}px)`);
    const handler = () => setIsMobile(mq.matches);
    handler();
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [breakpoint]);

  return isMobile;
}
