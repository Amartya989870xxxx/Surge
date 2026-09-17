import { initializeApp, getApps, getApp } from 'firebase/app';
import {
  getAuth,
  signInWithPopup,
  GoogleAuthProvider,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut as fbSignOut,
  onAuthStateChanged as fbOnAuthStateChanged,
  setPersistence,
  browserLocalPersistence,
  type User,
} from 'firebase/auth';

// No hardcoded fallbacks: every clone/deployment must supply its own Firebase project via
// these env vars (see .env.example). Falling back to a baked-in project would silently point
// anyone else's deployment at this project's Firebase instance instead of their own.
const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

export const app = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig);
export const auth = getAuth(app);

// Enforce local persistence on client so user stays logged in across reloads
setPersistence(auth, browserLocalPersistence).catch((err) => {
  console.warn('Firebase persistence setup warning:', err);
});

export const googleProvider = new GoogleAuthProvider();

export async function signInWithGoogle(): Promise<User> {
  const result = await signInWithPopup(auth, googleProvider);
  return result.user;
}

export async function signInWithEmail(email: string, pass: string): Promise<User> {
  const result = await signInWithEmailAndPassword(auth, email, pass);
  return result.user;
}

export async function signUpWithEmail(email: string, pass: string): Promise<User> {
  const result = await createUserWithEmailAndPassword(auth, email, pass);
  return result.user;
}

export async function signOutUser(): Promise<void> {
  try {
    localStorage.removeItem('surge_cached_profile');
  } catch {}
  await fbSignOut(auth);
}

export async function getCurrentIdToken(): Promise<string | null> {
  if (typeof (auth as any).authStateReady === 'function') {
    await (auth as any).authStateReady();
  }
  const user = auth.currentUser;
  if (!user) return null;
  return user.getIdToken();
}

export function onAuthChanged(callback: (user: User | null) => void) {
  return fbOnAuthStateChanged(auth, callback);
}
