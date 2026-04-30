import { useState, useRef } from 'react';
import { auth } from '../firebaseConfig';

export default function Uploader({ onUploadSuccess }) {
    const [file, setFile] = useState(null);
    const [status, setStatus] = useState({ type: '', message: '' });
    const fileInputRef = useRef(null);

    const handleFileSelect = (e) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
            setStatus({ type: '', message: '' });
        }
    };

    const triggerFileInput = () => {
        fileInputRef.current.click();
    };

    const handleUpload = async () => {
        if (!file || !auth.currentUser) return;
        setStatus({ type: 'loading', message: 'Uploading and parsing document structure...' });

        const formData = new FormData();
        formData.append('file', file);

        try {
            const token = await auth.currentUser.getIdToken();
            const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/upload`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                body: formData
            });

            const result = await response.json();
            if (response.ok) {
                setStatus({ type: 'success', message: `Success! Document ID: ${result.doc_id}` });
                console.log("Generated JSON Tree Index:", result.tree_preview);
                setFile(null);
                if (onUploadSuccess) {
                    onUploadSuccess(result.doc_id);
                }
                setTimeout(() => setStatus({ type: '', message: '' }), 3000);
            } else {
                setStatus({ type: 'error', message: `Error: ${result.detail}` });
            }
        } catch (error) {
            setStatus({ type: 'error', message: 'Network error. Please try again.' });
            console.error(error);
        }
    };

    return (
        <div className="glass-panel">
            <h3 style={{ marginBottom: '1.5rem', fontSize: '1.25rem' }}>Upload Document</h3>

            <div
                className={`uploader-dropzone ${file ? 'has-file' : ''}`}
                onClick={triggerFileInput}
            >
                <input
                    type="file"
                    className="file-input-hidden"
                    ref={fileInputRef}
                    onChange={handleFileSelect}
                    accept=".pdf,.docx,.xlsx,.xls,.doc"
                />
                <div className="uploader-icon">
                    {file ? '📄' : '☁️'}
                </div>
                <div className="uploader-text" style={{ wordBreak: 'break-all', padding: '0 5px' }}>
                    {file ? (
                        <>Selected:<br/><strong style={{ fontSize: '0.9rem' }}>{file.name}</strong></>
                    ) : (
                        <>Click to browse files</>
                    )}
                </div>
                {!file && <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>PDF, DOCX, XLSX</div>}
            </div>

            <button
                className="btn-primary"
                onClick={handleUpload}
                disabled={!file || status.type === 'loading'}
                style={{ width: '100%', opacity: (!file || status.type === 'loading') ? 0.6 : 1 }}
            >
                {status.type === 'loading' ? 'Processing...' : 'Process Document'}
            </button>

            {status.message && (
                <div className={`status-badge status-${status.type}`}>
                    {status.message}
                </div>
            )}
        </div>
    );
}