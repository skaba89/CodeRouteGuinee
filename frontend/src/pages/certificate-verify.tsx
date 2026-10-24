// Vérification publique d'une attestation (cible du QR code imprimé).
// Accessible sans compte : un employeur ou un agent de contrôle scanne le QR
// et lit le verdict d'authenticité délivré par le serveur.
import { useEffect, useState } from 'react';
import { verifyExamCertificate, type ExamCertificateVerification } from '../api';

function fmtDate(value?: string) {
  if (!value) return '—';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? '—' : parsed.toLocaleDateString('fr-FR');
}

export function CertificateVerifyPage({ attemptId }: { attemptId: string }) {
  const [cert, setCert] = useState<ExamCertificateVerification | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    verifyExamCertificate(attemptId)
      .then(setCert)
      .catch(() => setError('Vérification impossible pour le moment. Réessayez plus tard.'));
  }, [attemptId]);

  const authentic = Boolean(cert?.valid);
  return (
    <main className="screen" style={{ maxWidth: 560, margin: '40px auto', padding: '0 16px' }}>
      <div className="card" style={{ display: 'grid', gap: 14 }}>
        <div>
          <span className="eyebrow">CodeRoute Guinée — DNTT</span>
          <h1 style={{ fontSize: 22, margin: '6px 0 0' }}>Vérification d'attestation</h1>
        </div>
        {!cert && !error && <p style={{ color: 'var(--muted)' }}>Vérification en cours…</p>}
        {error && <div className="alert ae" role="alert">{error}</div>}
        {cert && (
          <>
            <div className={`alert ${authentic ? 'as' : 'ae'}`} role="status">
              {authentic
                ? <strong>Attestation authentique — {cert.passed ? 'ADMIS(E)' : 'NON ADMIS(E)'}</strong>
                : <strong>Attestation non reconnue{cert.reason ? ` : ${cert.reason}` : ''}</strong>}
            </div>
            {authentic && (
              <table>
                <tbody>
                  <tr><th style={{ textAlign: 'left' }}>Candidat</th><td>{cert.candidate_name}</td></tr>
                  <tr><th style={{ textAlign: 'left' }}>Référence</th><td>{cert.candidate_reference}</td></tr>
                  <tr><th style={{ textAlign: 'left' }}>Catégorie</th><td>{cert.permit_category}</td></tr>
                  <tr><th style={{ textAlign: 'left' }}>Centre</th><td>{cert.center_name} ({cert.center_city})</td></tr>
                  <tr><th style={{ textAlign: 'left' }}>Date</th><td>{fmtDate(cert.submitted_at)}</td></tr>
                  <tr><th style={{ textAlign: 'left' }}>Score</th><td>{cert.score} / 40</td></tr>
                </tbody>
              </table>
            )}
            <p style={{ fontSize: 12, color: 'var(--muted)', margin: 0 }}>
              Référence de vérification : {cert.attempt_id}. Chaque vérification est enregistrée au journal d'audit.
            </p>
          </>
        )}
      </div>
    </main>
  );
}
