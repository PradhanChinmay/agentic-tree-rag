import { useState, useEffect } from 'react';
import { auth, googleProvider } from './firebaseConfig';
import { signInWithPopup, signOut, onAuthStateChanged } from 'firebase/auth';
import Uploader from './components/Uploader';
import ChatBox from './components/ChatBox';

function App() {
  const [user, setUser] = useState(null);
  const [activeDocId, setActiveDocId] = useState(null);
  const [documents, setDocuments] = useState([]);

  useEffect(() => {
    onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      if (currentUser) fetchDocuments();
    });
  }, []);

  const fetchDocuments = async () => {
    const token = await auth.currentUser.getIdToken();
    const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/documents`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) setDocuments(await res.json());
  };

  const deleteDocument = async (docId) => {
    const token = await auth.currentUser.getIdToken();
    await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/documents/${docId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (activeDocId === docId) setActiveDocId(null);
    fetchDocuments();
  };

  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      {/* Sidebar */}
      {user && (
        <div className="glass-panel" style={{ width: '320px', margin: '20px', padding: '20px', display: 'flex', flexDirection: 'column', height: 'calc(100vh - 40px)' }}>
          <h3 className="text-gradient" style={{ marginBottom: '1.5rem', fontSize: '1.5rem' }}>My Documents</h3>
          <Uploader onUploadSuccess={(docId) => { setActiveDocId(docId); fetchDocuments(); }} />
          
          <div style={{ overflowY: 'auto', flex: 1, marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {documents.map(doc => (
            <div key={doc.doc_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 15px', background: activeDocId === doc.doc_id ? 'var(--bg-glass)' : 'rgba(0,0,0,0.2)', border: '1px solid', borderColor: activeDocId === doc.doc_id ? 'var(--accent-primary)' : 'var(--border-glass)', borderRadius: '0.5rem', cursor: 'pointer', transition: 'all 0.2s ease' }} onClick={() => setActiveDocId(doc.doc_id)}>
              <span style={{ flex: 1, minWidth: 0, marginRight: '10px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: activeDocId === doc.doc_id ? 'white' : 'var(--text-primary)', fontSize: '0.95rem' }}>{doc.filename}</span>
              <button onClick={(e) => { e.stopPropagation(); deleteDocument(doc.doc_id); }} style={{ color: 'var(--error)', border: 'none', background: 'none', cursor: 'pointer', fontSize: '1.2rem', opacity: 0.8, padding: '0 5px' }}>×</button>
            </div>
          ))}
          </div>
        </div>
      )}

      {/* Main Content */}
      <div style={{ flex: 1, padding: '20px 20px 20px 0', display: 'flex', flexDirection: 'column', height: '100vh', boxSizing: 'border-box' }}>
        {!user ? (
            <div className="main-content">
              <h1 className="hero-text text-gradient">Vectorless RAG</h1>
              <p className="sub-hero">Sign in to manage and query your documents.</p>
              <button className="btn-primary" onClick={() => signInWithPopup(auth, googleProvider)}>Sign in with Google</button>
            </div>
        ) : (
          <>
            <div className="header" style={{ borderRadius: '1rem', marginBottom: '20px' }}>
              <h1 className="text-gradient">Vectorless RAG</h1>
              <div className="user-profile">
                <div className="profile-trigger">
                  <img src={user.photoURL || `https://ui-avatars.com/api/?name=${encodeURIComponent(user.displayName)}&background=333&color=fff`} alt="Profile" style={{ width: '40px', height: '40px', borderRadius: '50%', objectFit: 'cover' }} />
                </div>
                <div className="profile-dropdown">
                  <div className="dropdown-header">
                    <span className="user-name">{user.displayName}</span>
                  </div>
                  <div className="dropdown-body">
                    <button className="btn-secondary" onClick={() => signOut(auth)} style={{ width: '100%', fontSize: '0.9rem', padding: '0.5rem' }}>Sign Out</button>
                  </div>
                </div>
              </div>
            </div>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              {activeDocId ? <ChatBox docId={activeDocId} key={activeDocId} /> : <div className="glass-panel" style={{ margin: 'auto', textAlign: 'center' }}><h2 className="sub-hero" style={{ marginBottom: 0 }}>Select or upload a document to begin.</h2></div>}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
export default App;