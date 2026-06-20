/**
 * Synchronisation hors-ligne — 200 questions en SQLite
 * Permet l'entraînement sans connexion internet (préfectures isolées).
 */
import { create } from 'zustand';
import * as SQLite from 'expo-sqlite';
import * as Network from 'expo-network';

interface Question {
  id: string;
  category: string;
  category_label: string;
  text: string;
  options: string[];
  correct_answer: string;
  explanation: string;
}

interface OfflineState {
  questionsCount: number;
  lastSync: string | null;
  syncing: boolean;
  isOnline: boolean;

  syncQuestions: (token: string) => Promise<void>;
  getQuestions: (category?: string, limit?: number) => Promise<Question[]>;
  checkNetwork: () => Promise<void>;
}

const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

export const useOfflineStore = create<OfflineState>((set, get) => ({
  questionsCount: 0,
  lastSync: null,
  syncing: false,
  isOnline: true,

  checkNetwork: async () => {
    const status = await Network.getNetworkStateAsync();
    set({ isOnline: status.isConnected ?? false });
  },

  syncQuestions: async (token: string) => {
    const { isOnline } = get();
    if (!isOnline) return;

    set({ syncing: true });
    try {
      const db = await SQLite.openDatabaseAsync('coderoute_offline.db');
      await db.execAsync(`
        CREATE TABLE IF NOT EXISTS questions (
          id TEXT PRIMARY KEY,
          category TEXT NOT NULL,
          category_label TEXT,
          text TEXT NOT NULL,
          options TEXT NOT NULL,
          correct_answer TEXT NOT NULL,
          explanation TEXT,
          synced_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_questions_category ON questions(category);
      `);

      // Charger depuis l'API
      const resp = await fetch(`${API_URL}/training/questions?limit=200&shuffle=false`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resp.ok) throw new Error('API indisponible');
      const questions: Question[] = await resp.json();

      // Insérer en batch
      await db.withTransactionAsync(async () => {
        for (const q of questions) {
          await db.runAsync(
            `INSERT OR REPLACE INTO questions (id, category, category_label, text, options, correct_answer, explanation)
             VALUES (?, ?, ?, ?, ?, ?, ?)`,
            [q.id, q.category, q.category_label, q.text, JSON.stringify(q.options), q.correct_answer, q.explanation ?? '']
          );
        }
      });

      set({ questionsCount: questions.length, lastSync: new Date().toISOString() });
    } finally {
      set({ syncing: false });
    }
  },

  getQuestions: async (category?: string, limit = 20): Promise<Question[]> => {
    const db = await SQLite.openDatabaseAsync('coderoute_offline.db');
    const rows = await db.getAllAsync<{id:string;category:string;category_label:string;text:string;options:string;correct_answer:string;explanation:string}>(
      category
        ? `SELECT * FROM questions WHERE category = ? ORDER BY RANDOM() LIMIT ?`
        : `SELECT * FROM questions ORDER BY RANDOM() LIMIT ?`,
      category ? [category, limit] : [limit]
    );
    return rows.map(r => ({ ...r, options: JSON.parse(r.options) }));
  },
}));
