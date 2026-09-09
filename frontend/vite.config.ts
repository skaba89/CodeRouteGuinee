import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: [
        'favicon.ico',
        'icons/*.png',
        'media/exam/guinea/manifest.json',
      ],
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,webp,woff2}'],
        // Les WebP d'examen Guinée doivent suivre UNE seule stratégie de cache.
        // Ils sont exclus du precache afin que NetworkFirst reste réellement
        // autoritatif après un redéploiement ou une corruption de cache mobile.
        globIgnores: ['media/exam/guinea/*.webp'],
        cleanupOutdatedCaches: true,
        navigateFallback: '/offline.html',
        navigateFallbackDenylist: [/\/api\//, /\/docs(?:\/|$)/, /\/openapi(?:\/|$)/],
        runtimeCaching: [
          {
            // Frontière de sécurité explicite : les API sensibles ne doivent
            // JAMAIS être persistées par le Service Worker. Cela couvre la
            // banque admin (avec réponses), les examens officiels et les PII.
            // La regexp n'est pas ancrée afin de fonctionner aussi lorsque
            // VITE_API_BASE_URL pointe vers un domaine Render distinct.
            urlPattern: /\/api\/v1\/(questions|exams|auth|candidates|payments|bookings|entries|center-incidents|supervision|audit)(?:\/|\?|$)/,
            handler: 'NetworkOnly',
          },
          {
            // Seul le contenu pédagogique d'entraînement est autorisé dans
            // le cache API. StaleWhileRevalidate offre une reprise hors ligne
            // tout en rafraîchissant la banque dès que le réseau revient.
            // Cette regexp matche aussi https://backend.../api/v1/training.
            urlPattern: /\/api\/v1\/training(?:\/|\?|$)/,
            handler: 'StaleWhileRevalidate',
            options: {
              cacheName: 'training-content-v2',
              cacheableResponse: { statuses: [0, 200] },
              expiration: {
                maxEntries: 120,
                maxAgeSeconds: 7 * 24 * 3600,
                purgeOnQuotaError: true,
              },
            },
          },
          {
            // Les images du pack d'entraînement guinéen sont petites et
            // critiques pour la compréhension d'une question. NetworkFirst
            // évite qu'un ancien cache Safari/PWA conserve indéfiniment une
            // réponse invalide après un redéploiement, tout en gardant un
            // fallback hors ligne lorsque le réseau n'est pas disponible.
            // Les vidéos ne sont volontairement pas mises en cache ici afin
            // de préserver les Range Requests et le budget data mobile.
            urlPattern: /\/media\/exam\/guinea\/.*\.webp(?:\?.*)?$/,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'guinea-exam-images-v4',
              networkTimeoutSeconds: 5,
              cacheableResponse: { statuses: [200] },
              expiration: {
                maxEntries: 40,
                maxAgeSeconds: 30 * 24 * 3600,
                purgeOnQuotaError: true,
              },
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
    host: '0.0.0.0',
    allowedHosts: ['all'],   // Nécessaire pour Render preview
  },

  preview: {
    port: 4173,
    host: '0.0.0.0',
    allowedHosts: ['all'],   // Nécessaire pour Render preview
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
