import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],

  server: {
    port: 5173,
  },

  build: {
    // Seuil d'avertissement chunk (kB)
    chunkSizeWarningLimit: 200,

    rollupOptions: {
      output: {
        // ── Chunking manuel par domaine ──────────────────────────
        // Objectif : bundle initial < 100 kB, reste chargé à la demande
        manualChunks(id) {
          // Vendor React — chargé une fois, très stable
          if (id.includes('node_modules/react') ||
              id.includes('node_modules/react-dom') ||
              id.includes('node_modules/scheduler')) {
            return 'vendor-react';
          }

          // Pages lourdes — chargées uniquement si l'utilisateur y accède
          if (id.includes('pages.tsx')) {
            // Toutes les pages dans un chunk séparé du code d'init
            return 'pages';
          }

          // API client — partagé entre pages
          if (id.includes('api.ts')) {
            return 'api-client';
          }

          // i18n — chargé au démarrage mais séparable
          if (id.includes('i18n')) {
            return 'i18n';
          }
        },

        // Nommage des chunks pour cache long terme
        chunkFileNames:  'assets/[name]-[hash].js',
        entryFileNames:  'assets/[name]-[hash].js',
        assetFileNames:  'assets/[name]-[hash][extname]',
      },
    },

    // Source maps en prod (pour Sentry — désactiver si pas de Sentry)
    sourcemap: false,

    // Cibler les navigateurs modernes (pas IE)
    target: ['es2020', 'chrome80', 'firefox78', 'safari14'],
  },

  // Optimisation des dépendances en dev
  optimizeDeps: {
    include: ['react', 'react-dom'],
  },
});
