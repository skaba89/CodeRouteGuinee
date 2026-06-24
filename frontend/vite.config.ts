import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'icons/*.png'],
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        navigateFallback: '/offline.html',
        navigateFallbackDenylist: [/^\/api/, /\/docs/, /\/openapi/],
        runtimeCaching: [
          {
            // Cache les appels API GET pendant 5 minutes (offline partiel)
            urlPattern: /^\/api\/v1\/(training|questions|sessions|centres)/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'api-cache',
              expiration: { maxEntries: 50, maxAgeSeconds: 300 },
            },
          },
        ],
      },
      manifest: {
        name: 'CodeRoute Guinée',
        short_name: 'CodeRoute',
        description: 'Examen du code de la route — République de Guinée',
        theme_color: '#006B3F',
        background_color: '#ffffff',
        display: 'standalone',
        orientation: 'portrait',
        scope: '/',
        start_url: '/',
        lang: 'fr',
        icons: [
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' },
        ],
        categories: ['education', 'government'],
        shortcuts: [
          {
            name: 'Passer un examen blanc',
            short_name: 'Examen blanc',
            description: "Commencer un examen d'entraînement",
            url: '/?mode=training',
            icons: [{ src: '/icons/icon-192.png', sizes: '192x192' }],
          },
        ],
      },
    }),
  ],

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
