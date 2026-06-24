/**
 * Page E-Learning — CodeRoute Guinée
 * Liste des cours → détail du cours → lecteur de leçon (+ vidéo)
 */
import { useState, useEffect } from 'react';
import { getPrivateJson, postJson } from '../api';
import { useAuthSession } from '../authSession';

interface CourseItem {
  id: string; title: string; description: string;
  category: string; order: number; cover_url: string | null; lesson_count: number;
}
interface Lesson {
  id: string; title: string; content: string; order: number;
  video_url: string | null; video_duration_seconds: number | null; duration_minutes: number;
}
interface CourseDetail extends CourseItem { lessons: Lesson[]; }

const CATEGORY_LABELS: Record<string, string> = {
  general:        '🚗 Général',
  signalisation:  '🚦 Signalisation',
  priorite:       '⚠️ Priorité',
  vitesse:        '💨 Vitesse',
  securite:       '🛡 Sécurité',
  environnement:  '🌿 Environnement',
};

export function ELearningPage() {
  const { currentUser } = useAuthSession();
  const isAuth = !!currentUser;
  const [view, setView]             = useState<'list' | 'course' | 'lesson'>('list');
  const [courses, setCourses]       = useState<CourseItem[]>([]);
  const [course, setCourse]         = useState<CourseDetail | null>(null);
  const [lesson, setLesson]         = useState<Lesson | null>(null);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState('');
  const [progress, setProgress]     = useState<Record<string, number>>({});

  // Charger la liste des cours
  useEffect(() => {
    if (!isAuth) return;
    setLoading(true);
    getPrivateJson<CourseItem[]>('/api/v1/courses')
      .then(setCourses)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [isAuth]);

  async function openCourse(id: string) {
    setLoading(true);
    try {
      const d = await getPrivateJson<CourseDetail>(`/api/v1/courses/${id}`);
      setCourse(d); setView('course');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erreur');
    } finally { setLoading(false); }
  }

  async function openLesson(l: Lesson) {
    setLesson(l); setView('lesson');
    // Marquer comme commencé
    if (course) {
      try {
        await postJson(`/api/v1/courses/${course.id}/lessons/${l.id}/progress`,
          { progress_pct: 10, completed: false });
        setProgress(p => ({ ...p, [l.id]: Math.max(p[l.id] || 0, 10) }));
      } catch { /* silencieux */ }
    }
  }

  async function markComplete(lessonId: string) {
    if (!course) return;
    try {
      await postJson(`/api/v1/courses/${course.id}/lessons/${lessonId}/progress`,
        { progress_pct: 100, completed: true });
      setProgress(p => ({ ...p, [lessonId]: 100 }));
    } catch { /* silencieux */ }
  }

  if (!isAuth) return (
    <div className="card"><p>🔐 Connectez-vous pour accéder aux cours.</p></div>
  );

  if (loading) return <div className="card"><p style={{ color: '#888' }}>Chargement…</p></div>;

  // ── Vue leçon ──────────────────────────────────────────────────────────────
  if (view === 'lesson' && lesson && course) return (
    <div className="card" style={{ maxWidth: 720 }}>
      <div className="card-header">
        <button onClick={() => setView('course')} style={{ background: 'none', border: 'none',
          cursor: 'pointer', fontSize: 14, color: 'var(--primary)' }}>
          ← {course.title}
        </button>
      </div>
      <div style={{ padding: '20px 0' }}>
        <h2 style={{ marginBottom: 16, fontSize: 20 }}>{lesson.title}</h2>

        {/* Vidéo */}
        {lesson.video_url && (
          <div style={{ marginBottom: 20, borderRadius: 10, overflow: 'hidden',
            background: '#000', aspectRatio: '16/9' }}>
            <video
              src={lesson.video_url}
              controls
              style={{ width: '100%', height: '100%' }}
              onTimeUpdate={(e) => {
                const el = e.currentTarget;
                const pct = Math.round((el.currentTime / el.duration) * 100);
                if (pct > (progress[lesson.id] || 0)) {
                  setProgress(p => ({ ...p, [lesson.id]: pct }));
                }
              }}
              onEnded={() => markComplete(lesson.id)}
            />
          </div>
        )}

        {/* Contenu texte */}
        <div style={{ lineHeight: 1.7, fontSize: 15, color: 'var(--ink)' }}>
          {lesson.content.split('\n').map((line, i) => (
            <p key={i} style={{ marginBottom: 8 }}>{line}</p>
          ))}
        </div>

        {/* Progression */}
        <div style={{ marginTop: 24, display: 'flex', gap: 12, alignItems: 'center' }}>
          <div style={{ flex: 1, height: 8, background: '#e5e7eb', borderRadius: 4 }}>
            <div style={{
              width: `${progress[lesson.id] || 0}%`, height: '100%',
              background: 'var(--primary)', borderRadius: 4, transition: 'width 0.3s',
            }} />
          </div>
          <span style={{ fontSize: 13, color: '#888' }}>{progress[lesson.id] || 0}%</span>
          <button
            onClick={() => markComplete(lesson.id)}
            style={{
              padding: '8px 16px', borderRadius: 8, border: 'none', cursor: 'pointer',
              background: progress[lesson.id] >= 100 ? '#e5e7eb' : 'var(--primary)',
              color: progress[lesson.id] >= 100 ? '#555' : '#fff', fontWeight: 600, fontSize: 13,
            }}
            disabled={progress[lesson.id] >= 100}
          >
            {progress[lesson.id] >= 100 ? '✅ Terminé' : 'Marquer comme terminé'}
          </button>
        </div>
      </div>
    </div>
  );

  // ── Vue cours ──────────────────────────────────────────────────────────────
  if (view === 'course' && course) return (
    <div className="card" style={{ maxWidth: 720 }}>
      <div className="card-header">
        <button onClick={() => setView('list')} style={{ background: 'none', border: 'none',
          cursor: 'pointer', fontSize: 14, color: 'var(--primary)' }}>
          ← Tous les cours
        </button>
      </div>
      <div style={{ padding: '16px 0' }}>
        <h2 style={{ fontSize: 22, marginBottom: 6 }}>{course.title}</h2>
        <p style={{ color: '#888', fontSize: 14, marginBottom: 20 }}>{course.description}</p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {course.lessons.map((ls, idx) => {
            const pct = progress[ls.id] || 0;
            return (
              <div
                key={ls.id}
                onClick={() => openLesson(ls)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '12px 16px', borderRadius: 10, cursor: 'pointer',
                  background: pct >= 100 ? '#f0fdf4' : '#f8faf9',
                  border: `1px solid ${pct >= 100 ? '#bbf7d0' : '#e5e7eb'}`,
                  transition: 'all 0.15s',
                }}
              >
                <div style={{
                  width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
                  background: pct >= 100 ? '#22c55e' : 'var(--primary)',
                  color: '#fff', display: 'flex', alignItems: 'center',
                  justifyContent: 'center', fontSize: 13, fontWeight: 700,
                }}>
                  {pct >= 100 ? '✓' : idx + 1}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: 14 }}>{ls.title}</div>
                  <div style={{ fontSize: 12, color: '#888', marginTop: 2 }}>
                    {ls.video_url && '🎬 Vidéo · '}
                    {ls.duration_minutes} min
                  </div>
                </div>
                {pct > 0 && pct < 100 && (
                  <div style={{ fontSize: 12, color: 'var(--primary)', fontWeight: 600 }}>
                    {pct}%
                  </div>
                )}
                <span style={{ color: '#ccc' }}>›</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );

  // ── Liste des cours ────────────────────────────────────────────────────────
  return (
    <div>
      <h2 style={{ fontSize: 22, marginBottom: 4 }}>📚 Cours en ligne</h2>
      <p style={{ color: '#888', fontSize: 14, marginBottom: 20 }}>
        Préparez-vous avec nos modules de formation officiels DNTT
      </p>

      {error && <p style={{ color: '#c00' }}>⚠ {error}</p>}

      {courses.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <div style={{ fontSize: 40, marginBottom: 12 }}>📖</div>
          <p style={{ color: '#888' }}>Aucun cours disponible pour le moment.</p>
          <p style={{ fontSize: 13, color: '#aaa' }}>
            Les modules de cours seront publiés prochainement.
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
          {courses.map(c => (
            <div
              key={c.id}
              onClick={() => openCourse(c.id)}
              className="card"
              style={{ cursor: 'pointer', transition: 'transform 0.15s, box-shadow 0.15s' }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)';
                (e.currentTarget as HTMLElement).style.boxShadow = '0 8px 24px rgba(0,0,0,0.1)';
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLElement).style.transform = '';
                (e.currentTarget as HTMLElement).style.boxShadow = '';
              }}
            >
              {/* Couverture */}
              <div style={{
                height: 120, borderRadius: '8px 8px 0 0', marginBottom: 16,
                background: c.cover_url ? `url(${c.cover_url}) center/cover` : 'linear-gradient(135deg, #006B3F 0%, #009460 100%)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                {!c.cover_url && <span style={{ fontSize: 40 }}>🚗</span>}
              </div>

              <div style={{ padding: '0 4px 4px' }}>
                <span style={{
                  fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 10,
                  background: '#e8f5e9', color: '#2e7d32', display: 'inline-block', marginBottom: 8,
                }}>
                  {CATEGORY_LABELS[c.category] ?? c.category}
                </span>
                <h3 style={{ fontSize: 16, marginBottom: 6, lineHeight: 1.3 }}>{c.title}</h3>
                <p style={{ fontSize: 13, color: '#666', marginBottom: 12, lineHeight: 1.5 }}>
                  {c.description.slice(0, 80)}{c.description.length > 80 ? '…' : ''}
                </p>
                <div style={{ fontSize: 12, color: '#888' }}>
                  📝 {c.lesson_count} leçon{c.lesson_count > 1 ? 's' : ''}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
