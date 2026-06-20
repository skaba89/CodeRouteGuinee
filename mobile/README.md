# CodeRoute Guinée Mobile — Architecture React Native (Mois 7–9)

## Stack technique

| Composant | Technologie |
|---|---|
| Framework | React Native 0.75 + Expo SDK 52 |
| Langage | TypeScript strict |
| Navigation | Expo Router (file-based) |
| Storage local | expo-sqlite (mode hors-ligne) |
| Notifications | expo-notifications + Firebase FCM |
| Caméra QR | expo-camera + expo-barcode-scanner |
| Paiement | React Native Orange Money / MTN MoMo |
| État | Zustand (léger, offline-first) |
| Tests | Jest + React Native Testing Library |

## Structure du projet

```
mobile/
├── app/                    Expo Router (pages)
│   ├── (tabs)/
│   │   ├── index.tsx       Accueil candidat
│   │   ├── training.tsx    Mode entraînement
│   │   ├── exam.tsx        Examen officiel
│   │   └── results.tsx     Résultats & Certificat
│   ├── auth/
│   │   ├── login.tsx       Connexion
│   │   └── register.tsx    Inscription
│   ├── center/
│   │   ├── scanner.tsx     Scanner QR caméra
│   │   └── start-exam.tsx  Démarrer examen
│   └── payment.tsx         Paiement Mobile Money
├── components/             Composants réutilisables
│   ├── QuestionCard.tsx    Question avec SVG
│   ├── Timer.tsx           Timer circulaire natif
│   ├── QRScanner.tsx       Scanner caméra
│   └── OfflineBanner.tsx   Bannière hors-ligne
├── lib/
│   ├── api.ts              Client API (partagé avec le web)
│   ├── offline/
│   │   ├── db.ts           SQLite schema
│   │   ├── sync.ts         Synchronisation différée
│   │   └── questions.ts    Banque 200Q en local
│   └── notifications.ts    Push notifications
├── stores/
│   ├── auth.ts             État authentification
│   ├── exam.ts             État examen en cours
│   └── training.ts         Progrès entraînement
└── assets/
    ├── signs/              SVG panneaux (offline)
    └── sounds/             Sons feedback
```

## Fonctionnalités clés

### Mode hors-ligne (critique pour les préfectures)
```typescript
// lib/offline/questions.ts
import * as SQLite from 'expo-sqlite';

const db = SQLite.openDatabase('coderoute.db');

export async function syncQuestions(token: string) {
  const questions = await fetch(`${API_URL}/training/questions?limit=200`, {
    headers: { Authorization: `Bearer ${token}` }
  }).then(r => r.json());

  await db.runAsync(
    'CREATE TABLE IF NOT EXISTS questions (id TEXT, category TEXT, data TEXT)'
  );
  
  for (const q of questions) {
    await db.runAsync(
      'INSERT OR REPLACE INTO questions VALUES (?, ?, ?)',
      [q.id, q.category, JSON.stringify(q)]
    );
  }
}
```

### Scanner QR (centres d'examen)
```typescript
// components/QRScanner.tsx
import { CameraView } from 'expo-camera';

export function QRScanner({ onScanned }) {
  return (
    <CameraView
      style={{ flex: 1 }}
      facing="back"
      barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
      onBarcodeScanned={({ data }) => onScanned(data)}
    />
  );
}
```

### Notifications push
```typescript
// lib/notifications.ts — Convocation automatique J-48h
import * as Notifications from 'expo-notifications';

export async function scheduleConvocationReminder(examDate: string, center: string) {
  const trigger = new Date(examDate);
  trigger.setHours(trigger.getHours() - 48);
  
  await Notifications.scheduleNotificationAsync({
    content: {
      title: '🇬🇳 CodeRoute Guinée — Rappel examen',
      body: `Votre examen est dans 48h au ${center}. Vérifiez votre convocation !`,
      data: { screen: 'exam_convocation' },
    },
    trigger,
  });
}
```

## Déploiement

```bash
# Installation
npm install -g @expo/cli eas-cli
eas login

# Build Android (APK pour distribution hors Play Store)
eas build --platform android --profile preview

# Build iOS (TestFlight)
eas build --platform ios --profile preview

# Build production
eas build --platform all --profile production

# Soumettre aux stores
eas submit --platform android
eas submit --platform ios
```

## Configuration EAS (eas.json)

```json
{
  "build": {
    "preview": {
      "android": { "buildType": "apk" }
    },
    "production": {
      "android": { "buildType": "aab" },
      "ios": { "simulator": false }
    }
  }
}
```

## Variables d'environnement mobile

```
EXPO_PUBLIC_API_URL=https://api.coderoute.gov.gn/api/v1
EXPO_PUBLIC_SENTRY_DSN=...
FIREBASE_PROJECT_ID=coderoute-guinee
```

## Roadmap mobile

| Semaine | Livrable |
|---|---|
| S1–S2 | Setup Expo + navigation + auth JWT |
| S3–S4 | SQLite offline + sync 200 questions |
| S5–S6 | TrainingScreen + ExamScreen |
| S7–S8 | QR Scanner centre + push notifications |
| S9–S10 | Tests + build APK + beta test interne |
| S11–S12 | Corrections + soumission Play Store / App Store |
