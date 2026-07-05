import { getApps, initializeApp, type FirebaseOptions } from "firebase/app";
import { getAuth, type Auth } from "firebase/auth";

// Real values are provided via env vars once a Firebase project exists (open_questions.md —
// no real project is configured yet, same placeholder gap as iOS/Android). Empty strings let
// the app build and render; sign-in itself will fail until real config is supplied.
const firebaseConfig: FirebaseOptions = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY ?? "",
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN ?? "",
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID ?? "",
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID ?? "",
};

export const isFirebaseConfigured = Boolean(firebaseConfig.apiKey && firebaseConfig.projectId);

export const firebaseApp = getApps().length ? getApps()[0] : initializeApp(firebaseConfig);

// getAuth() validates the API key eagerly and throws immediately when it's empty/invalid — even
// during build-time prerendering. Constructing it lazily, only once actually needed at runtime
// and only when configured, keeps `next build` working with no Firebase project set up yet.
let cachedAuth: Auth | null = null;

export function getFirebaseAuth(): Auth | null {
  if (!isFirebaseConfigured) return null;
  if (!cachedAuth) cachedAuth = getAuth(firebaseApp);
  return cachedAuth;
}
