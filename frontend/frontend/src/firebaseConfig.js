import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider, signInWithPopup, signOut } from "firebase/auth";

const firebaseConfig = {
    apiKey: "AIzaSyDYAyMprWWXJbwTRJwcj-m2suxOw_iX6xI",
    authDomain: "sonar-9fb73.firebaseapp.com",
    projectId: "sonar-9fb73",
    storageBucket: "sonar-9fb73.firebasestorage.app",
    messagingSenderId: "141832085977",
    appId: "1:141832085977:web:f2f25b9bb17c84346eb9c8",
    measurementId: "G-EDMRMV1BT3"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();