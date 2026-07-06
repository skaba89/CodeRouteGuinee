/**
 * Page d'accueil publique — visible sans connexion.
 * Présente la plateforme nationale, le parcours candidat, les catégories,
 * avec accès Connexion / Inscription.
 */

const GuineaFlag = () => (
  <svg width="34" height="23" viewBox="0 0 3 2" style={{ borderRadius: 3, boxShadow: '0 1px 4px rgba(0,0,0,.25)' }}>
    <rect width="1" height="2" x="0" fill="#CE1126" />
    <rect width="1" height="2" x="1" fill="#FCD116" />
    <rect width="1" height="2" x="2" fill="#009460" />
  </svg>
);

const STEPS = [
  {
    n: '1', t: 'Créez votre compte',
    d: "Inscription gratuite en ligne avec votre numéro d'identité (NNI ou passeport). Vous recevez immédiatement votre référence officielle GN-CODE.",
  },
  {
    n: '2', t: 'Réservez votre créneau',
    d: "Choisissez votre centre d'examen parmi les 135 centres agréés et sélectionnez un créneau selon les places disponibles.",
  },
  {
    n: '3', t: 'Présentez-vous au centre',
    d: "Le jour J, présentez votre référence et votre code de vérification à l'agent DNTT. Le paiement s'effectue au centre (phase pilote).",
  },
  {
    n: '4', t: "Passez l'examen",
    d: "40 questions officielles sur ordinateur ou tablette. Résultat immédiat et certificat vérifiable en ligne.",
  },
];

const CATEGORIES = [
  { c: 'A', l: 'Moto' },
  { c: 'B', l: 'Voiture' },
  { c: 'C', l: 'Poids lourd' },
  { c: 'D', l: 'Transport en commun' },
  { c: 'E', l: 'Remorque' },
];

const STATS = [
  { v: '135', l: "Centres d'examen agréés" },
  { v: '200', l: 'Questions officielles DNTT' },
  { v: '40', l: 'Questions par épreuve' },
  { v: '35', l: 'Candidats max par session' },
];

export function LandingPage() {
  const go = (hash: string) => () => { window.location.hash = hash; };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      {/* ── Topbar publique ── */}
      <header style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '14px 28px', background: 'var(--navy)',
        borderBottom: '3px solid transparent',
        borderImage: 'linear-gradient(90deg, #CE1126 33%, #FCD116 33% 66%, #009460 66%) 1',
        position: 'sticky', top: 0, zIndex: 50,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div className="brand-logo" style={{ width: 40, height: 40, fontSize: 15 }}>CR</div>
          <div>
            <div style={{ color: '#fff', fontWeight: 700, fontSize: 15, letterSpacing: '-.01em' }}>CodeRoute Guinée</div>
            <div style={{ color: 'rgba(255,255,255,.55)', fontSize: 10, letterSpacing: '.12em', textTransform: 'uppercase' }}>Plateforme DNTT</div>
          </div>
        </div>
        <nav style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button onClick={go('#/login')} style={{
            background: 'transparent', border: '1.5px solid rgba(255,255,255,.35)',
            color: '#fff', padding: '9px 18px', borderRadius: 10, fontSize: 13,
            fontWeight: 600, cursor: 'pointer', fontFamily: 'var(--font-ui)',
          }}>
            Connexion
          </button>
          <button onClick={go('#/register')} style={{
            background: 'var(--guinea-green)', border: 'none', color: '#fff',
            padding: '9px 18px', borderRadius: 10, fontSize: 13, fontWeight: 700,
            cursor: 'pointer', fontFamily: 'var(--font-ui)',
          }}>
            Créer un compte
          </button>
        </nav>
      </header>

      <main style={{ maxWidth: 1080, margin: '0 auto', padding: '28px 22px 60px' }}>
        {/* ── Hero ── */}
        <section className="dash-hero" style={{ padding: '44px 40px', marginBottom: 26 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 24, flexWrap: 'wrap' }}>
            <div style={{ maxWidth: 620 }}>
              <span className="eyebrow">République de Guinée — Ministère des Transports</span>
              <h1 style={{ fontSize: 'clamp(26px, 4vw, 38px)', lineHeight: 1.15 }}>
                L'examen officiel du code de la route, désormais en ligne
              </h1>
              <p style={{ marginTop: 12, fontSize: 15, maxWidth: 540 }}>
                Inscrivez-vous, réservez votre créneau dans l'un des 135 centres agréés
                et passez l'épreuve théorique dans des conditions transparentes et équitables,
                partout sur le territoire national.
              </p>
              <div style={{ display: 'flex', gap: 12, marginTop: 24, flexWrap: 'wrap' }}>
                <button className="btn-success" style={{ minHeight: 46, padding: '0 26px', fontSize: 14 }}
                  onClick={go('#/register')}>
                  Créer mon compte candidat →
                </button>
                <button onClick={go('#/login')} style={{
                  background: 'rgba(255,255,255,.1)', border: '1.5px solid rgba(255,255,255,.3)',
                  color: '#fff', padding: '0 22px', minHeight: 46, borderRadius: 10,
                  fontSize: 14, fontWeight: 600, cursor: 'pointer', fontFamily: 'var(--font-ui)',
                }}>
                  J'ai déjà un compte
                </button>
              </div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <GuineaFlag />
              <div className="dash-hero-label" style={{ marginTop: 8 }}>République<br/>de Guinée</div>
            </div>
          </div>
        </section>

        {/* ── Chiffres ── */}
        <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 14, marginBottom: 34 }}>
          {STATS.map(s => (
            <div key={s.l} className="card" style={{ textAlign: 'center', padding: '22px 14px' }}>
              <div style={{ fontSize: 32, fontWeight: 800, color: 'var(--guinea-green)', fontFamily: 'var(--font-serif)' }}>{s.v}</div>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 4 }}>{s.l}</div>
            </div>
          ))}
        </section>

        {/* ── Comment ça marche ── */}
        <section style={{ marginBottom: 36 }}>
          <span className="eyebrow dark" style={{ color: 'var(--guinea-green)' }}>Parcours candidat</span>
          <h2 style={{ fontSize: 24, marginTop: 4, marginBottom: 18 }}>Comment ça marche</h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(230px, 1fr))', gap: 14 }}>
            {STEPS.map(s => (
              <div key={s.n} className="card" style={{ padding: '20px 18px' }}>
                <div style={{
                  width: 34, height: 34, borderRadius: 10, background: 'var(--navy)',
                  color: 'var(--guinea-gold)', display: 'flex', alignItems: 'center',
                  justifyContent: 'center', fontWeight: 800, fontSize: 15, marginBottom: 12,
                }}>{s.n}</div>
                <h3 style={{ fontSize: 15, marginBottom: 6 }}>{s.t}</h3>
                <p style={{ fontSize: 13, color: 'var(--muted)', lineHeight: 1.55 }}>{s.d}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── Catégories ── */}
        <section style={{ marginBottom: 36 }}>
          <span className="eyebrow dark" style={{ color: 'var(--guinea-green)' }}>Permis de conduire</span>
          <h2 style={{ fontSize: 24, marginTop: 4, marginBottom: 18 }}>Catégories disponibles</h2>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {CATEGORIES.map(cat => (
              <div key={cat.c} className="card" style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '14px 20px', flex: '1 1 160px',
              }}>
                <div style={{
                  width: 40, height: 40, borderRadius: 10, background: 'var(--guinea-green)',
                  color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontWeight: 800, fontSize: 17, fontFamily: 'var(--font-serif)',
                }}>{cat.c}</div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>{cat.l}</div>
              </div>
            ))}
          </div>
        </section>

        {/* ── Auto-écoles + entraînement ── */}
        <section className="g2" style={{ gap: 14, marginBottom: 36 }}>
          <div className="card" style={{ padding: '24px 22px' }}>
            <h3 style={{ fontSize: 17, marginBottom: 8 }}>Vous êtes une auto-école ?</h3>
            <p style={{ fontSize: 13, color: 'var(--muted)', lineHeight: 1.6, marginBottom: 14 }}>
              Inscrivez vos élèves en quelques clics, suivez leurs références officielles
              et leurs résultats depuis votre portail dédié. Contactez la DNTT pour
              l'ouverture de votre compte partenaire.
            </p>
            <button className="secondary-button btn-sm" onClick={go('#/login')}>
              Accès partenaires →
            </button>
          </div>
          <div className="card" style={{ padding: '24px 22px' }}>
            <h3 style={{ fontSize: 17, marginBottom: 8 }}>Entraînez-vous avant l'examen</h3>
            <p style={{ fontSize: 13, color: 'var(--muted)', lineHeight: 1.6, marginBottom: 14 }}>
              Une fois votre compte créé, accédez gratuitement au module d'entraînement :
              questions officielles illustrées, cours par thème et examens blancs
              dans les conditions réelles de l'épreuve.
            </p>
            <button className="btn-primary btn-sm" onClick={go('#/register')}>
              Commencer gratuitement →
            </button>
          </div>
        </section>

        {/* ── Bandeau final ── */}
        <section className="dash-hero" style={{ padding: '34px 36px', textAlign: 'center' }}>
          <h2 style={{ fontSize: 22, color: '#fff' }}>Prêt à passer votre code ?</h2>
          <p style={{ marginTop: 8, fontSize: 14 }}>
            L'inscription prend moins de deux minutes. Munissez-vous de votre NNI ou passeport.
          </p>
          <button className="btn-success" style={{ minHeight: 46, padding: '0 30px', fontSize: 14, marginTop: 18 }}
            onClick={go('#/register')}>
            Créer mon compte candidat →
          </button>
        </section>
      </main>

      {/* ── Footer ── */}
      <footer style={{
        background: 'var(--navy)', color: 'rgba(255,255,255,.6)', padding: '26px 28px',
        fontSize: 12, textAlign: 'center',
      }}>
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <GuineaFlag />
          <strong style={{ color: '#fff', fontSize: 13 }}>CodeRoute Guinée</strong>
        </div>
        Direction Nationale des Transports Terrestres — République de Guinée
        <br />Plateforme officielle de l'examen théorique du permis de conduire
      </footer>
    </div>
  );
}
