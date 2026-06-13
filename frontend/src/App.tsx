const metrics = [
  { label: 'Candidats inscrits', value: '1 250' },
  { label: 'Centres agrees', value: '18' },
  { label: 'Sessions organisees', value: '96' },
  { label: 'Taux de reussite', value: '72%' },
];

const modules = [
  'Inscription candidat',
  'Reservation examen',
  'Convocation QR code',
  'Examen en centre agree',
  'Correction automatique',
  'Audit anti-fraude',
];

export default function App() {
  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">Produit national pour la Guinee</p>
        <h1>CodeRoute Guinee</h1>
        <p>
          Plateforme nationale de digitalisation, securisation et tracabilite des examens du code de la route.
        </p>
        <div className="actions">
          <a href="http://localhost:8000/docs" target="_blank">Voir l'API</a>
          <a href="#modules" className="secondary">Modules MVP</a>
        </div>
      </section>

      <section className="metrics">
        {metrics.map((metric) => (
          <article key={metric.label}>
            <strong>{metric.value}</strong>
            <span>{metric.label}</span>
          </article>
        ))}
      </section>

      <section id="modules" className="panel">
        <h2>Socle fonctionnel national</h2>
        <div className="grid">
          {modules.map((module) => (
            <div className="card" key={module}>{module}</div>
          ))}
        </div>
      </section>
    </main>
  );
}
