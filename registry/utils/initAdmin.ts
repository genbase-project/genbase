import { getApps, initializeApp, cert } from 'firebase-admin/app';
import { defineAuth, secret } from '@aws-amplify/backend';

export function initAdmin() {
  const apps = getApps()
  
  if (!apps.length) {
    try {
      // More robust private key handling
      let privateKey = process.env.FIREBASE_PRIVATE_KEY || secret('FIREBASE_PRIVATE_KEY');

      console.log('Firebase private key:', privateKey);
      
      // Handle different formats that could be provided
      if (privateKey) {
        // If it's a JSON string (sometimes happens with cloud providers)
        if (privateKey!.startsWith('"') && privateKey!.endsWith('"')) {
          privateKey = JSON.parse(privateKey);
        }
        
        // Replace escaped newlines with actual newlines
        privateKey = privateKey!.replace(/\\n/g, '\n');
      }
      
      // Log the environment variable names for debugging (not values)
      console.log('Firebase environment variables available:', {
        projectId: !!process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
        clientEmail: !!process.env.FIREBASE_CLIENT_EMAIL || secret('FIREBASE_CLIENT_EMAIL'),
        privateKey: !!privateKey,
        databaseURL: !!process.env.NEXT_PUBLIC_FIREBASE_DATABASE_URL,
      });
      
      // Initialize the app with more defensive checks
      initializeApp({
        credential: cert({
          projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
          clientEmail: process.env.FIREBASE_CLIENT_EMAIL  || secret('FIREBASE_CLIENT_EMAIL'),
          privateKey: privateKey,
        }),
        databaseURL: process.env.NEXT_PUBLIC_FIREBASE_DATABASE_URL || undefined,
      });
      
      console.log('Firebase Admin initialized successfully');
    } catch (error) {
      console.error('Error initializing Firebase Admin:', error);
      throw error; // Re-throw to make the issue visible
    }
  }
}