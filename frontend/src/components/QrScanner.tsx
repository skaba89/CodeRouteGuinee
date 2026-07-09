import { useEffect, useRef, useState, useCallback } from 'react';

/**
 * Scanner de QR code par caméra — CodeRoute Guinée.
 *
 * Utilise l'API navigateur native BarcodeDetector (Chrome, Edge, Android),
 * sans dépendance externe. Si la caméra ou l'API n'est pas disponible
 * (ex. Safari/iOS anciens, ordinateur sans webcam), le composant l'indique
 * clairement — la saisie manuelle reste alors le moyen de validation.
 *
 * Le QR de convocation a le format :
 *   CODEROUTE-GN|REF={reference}|VERIFY={verification_code}
 * onScan reçoit (reference, verificationCode) une fois décodé.
 */

type BarcodeDetectorLike = {
  detect: (source: CanvasImageSource) => Promise<{ rawValue: string }[]>;
};

function parseConvocationQr(raw: string): { reference: string; code: string } | null {
  // Format attendu : CODEROUTE-GN|REF=...|VERIFY=...
  if (!raw.includes('REF=') || !raw.includes('VERIFY=')) return null;
  const refMatch = raw.match(/REF=([^|]+)/);
  const verifMatch = raw.match(/VERIFY=([^|]+)/);
  if (!refMatch || !verifMatch) return null;
  return { reference: refMatch[1].trim(), code: verifMatch[1].trim() };
}

export function QrScanner({ onScan, onClose }: {
  onScan: (reference: string, verificationCode: string) => void;
  onClose: () => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number | null>(null);
  const [status, setStatus] = useState<'starting' | 'scanning' | 'unsupported' | 'denied'>('starting');
  const [message, setMessage] = useState<string | null>(null);

  const stop = useCallback(() => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    const BarcodeDetectorCtor = (window as unknown as {
      BarcodeDetector?: new (o?: { formats: string[] }) => BarcodeDetectorLike;
    }).BarcodeDetector;

    if (!BarcodeDetectorCtor || !navigator.mediaDevices?.getUserMedia) {
      setStatus('unsupported');
      return;
    }

    const detector = new BarcodeDetectorCtor({ formats: ['qr_code'] });

    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment' },  // caméra arrière sur mobile
        });
        if (cancelled) { stream.getTracks().forEach(t => t.stop()); return; }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
        setStatus('scanning');

        const tick = async () => {
          if (cancelled || !videoRef.current) return;
          try {
            const codes = await detector.detect(videoRef.current);
            for (const c of codes) {
              const parsed = parseConvocationQr(c.rawValue);
              if (parsed) {
                stop();
                onScan(parsed.reference, parsed.code);
                return;
              }
              setMessage('QR code lu, mais ce n\'est pas une convocation CodeRoute valide.');
            }
          } catch {
            /* frame illisible, on continue */
          }
          rafRef.current = requestAnimationFrame(tick);
        };
        rafRef.current = requestAnimationFrame(tick);
      } catch (err) {
        if (cancelled) return;
        const name = (err as { name?: string })?.name;
        setStatus(name === 'NotAllowedError' ? 'denied' : 'unsupported');
      }
    })();

    return () => { cancelled = true; stop(); };
  }, [onScan, stop]);

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(10,37,64,.85)', zIndex: 1100,
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
    }} onClick={() => { stop(); onClose(); }}>
      <div style={{ background: '#fff', borderRadius: 16, padding: 18, maxWidth: 420, width: '100%' }}
        onClick={e => e.stopPropagation()}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <strong style={{ fontSize: 15 }}>Scanner la convocation</strong>
          <button className="btn-sm btn-outline" onClick={() => { stop(); onClose(); }}>Fermer</button>
        </div>

        {status === 'scanning' && (
          <p style={{ fontSize: 12.5, color: 'var(--muted)', marginBottom: 10 }}>
            Présentez le QR code de la convocation devant la caméra.
          </p>
        )}

        {(status === 'starting' || status === 'scanning') && (
          <div style={{ position: 'relative', borderRadius: 12, overflow: 'hidden', background: '#000' }}>
            <video ref={videoRef} playsInline muted
              style={{ width: '100%', display: 'block', maxHeight: 340, objectFit: 'cover' }} />
            {/* Cadre de visée */}
            <div style={{
              position: 'absolute', inset: '50% 50%', width: 180, height: 180,
              transform: 'translate(-50%, -50%)',
              border: '3px solid rgba(255,255,255,.9)', borderRadius: 14,
              boxShadow: '0 0 0 9999px rgba(0,0,0,.25)',
            }} />
          </div>
        )}

        {status === 'starting' && (
          <p style={{ fontSize: 13, color: 'var(--muted)', textAlign: 'center', padding: '12px 0' }}>
            Démarrage de la caméra…
          </p>
        )}

        {status === 'denied' && (
          <div className="alert aw" style={{ fontSize: 13 }}>
            Accès à la caméra refusé. Autorisez la caméra dans les réglages du navigateur,
            ou utilisez la saisie manuelle ci-dessous.
          </div>
        )}

        {status === 'unsupported' && (
          <div className="alert ai" style={{ fontSize: 13 }}>
            Le scan par caméra n'est pas disponible sur ce navigateur.
            Utilisez la saisie manuelle de la référence et du code.
          </div>
        )}

        {message && (
          <p style={{ fontSize: 12, color: 'var(--red)', marginTop: 10 }}>{message}</p>
        )}
      </div>
    </div>
  );
}
