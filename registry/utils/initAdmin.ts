import { getApps, initializeApp, cert } from 'firebase-admin/app';

export function initAdmin() {
  const apps = getApps()
  
  if (!apps.length) {
    initializeApp({
      credential: cert({
        projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
        clientEmail: process.env.FIREBASE_CLIENT_EMAIL,
        privateKey: process.env.FIREBASE_PRIVATE_KEY
          ? JSON.parse(process.env.FIREBASE_PRIVATE_KEY)
          : undefined,
      }),
      databaseURL: process.env.NEXT_PUBLIC_FIREBASE_DATABASE_URL,
    })
  }
}
