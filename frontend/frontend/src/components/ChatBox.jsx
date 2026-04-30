import { useState, useEffect, useRef } from 'react';
import { auth } from '../firebaseConfig';

export default function ChatBox({ docId }) {
    const [query, setQuery] = useState('');
    const [chatHistory, setChatHistory] = useState([]);
    const [streamingText, setStreamingText] = useState('');
    const [isStreaming, setIsStreaming] = useState(false);
    const [isWaiting, setIsWaiting] = useState(false);
    const wsRef = useRef(null);

    useEffect(() => {
        const loadHistory = async () => {
            const token = await auth.currentUser.getIdToken();
            const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/chat/${docId}/history`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.ok) {
                const history = await res.json();
                setChatHistory(history.map(msg => ({ role: msg.role === 'ai' ? 'model' : 'user', text: msg.message })));
            }
        };
        loadHistory();
    }, [docId]);

    useEffect(() => {
        const connectWs = async () => {
            const token = await auth.currentUser.getIdToken();
            wsRef.current = new WebSocket(`${import.meta.env.VITE_WS_BASE_URL}/ws/chat/${docId}?token=${token}`);

            wsRef.current.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'start') {
                    setIsWaiting(false);
                    setIsStreaming(true);
                    setStreamingText('');
                } else if (data.type === 'chunk') {
                    setStreamingText(prev => prev + data.text);
                } else if (data.type === 'end') {
                    setIsStreaming(false);
                    setIsWaiting(false);
                }
            };
        };
        connectWs();
        return () => wsRef.current?.close();
    }, [docId]);

    useEffect(() => {
        if (!isStreaming && streamingText !== '') {
            setChatHistory(prev => [...prev, { role: 'model', text: streamingText }]);
            setStreamingText('');
        }
    }, [isStreaming])

    const handleSend = () => {
        if (!query.trim() || !wsRef.current) return;

        setChatHistory(prev => [...prev, { role: 'user', text: query }]);
        setIsWaiting(true);
        wsRef.current.send(JSON.stringify({ query }));
        setQuery('');
    };

    return (
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', maxWidth: '100%', padding: '1.5rem', flex: 1 }}>
            <div className="chat-container" style={{ flex: 1, height: '0', marginBottom: '1rem' }}>
                {chatHistory.map((msg, idx) => (
                    <div key={idx} className={`chat-message-wrapper ${msg.role === 'user' ? 'user' : 'ai'}`}>
                        <div className={`chat-message ${msg.role === 'user' ? 'user' : 'ai'}`} style={{ whiteSpace: 'pre-wrap' }}>
                            {msg.text}
                        </div>
                    </div>
                ))}
                {isWaiting && !isStreaming && (
                    <div className="chat-message-wrapper ai fade-in">
                        <div className="chat-message ai">
                            <div className="typing-loader">
                                <div className="typing-dot typing-delay-1"></div>
                                <div className="typing-dot typing-delay-2"></div>
                                <div className="typing-dot typing-delay-3"></div>
                            </div>
                        </div>
                    </div>
                )}
                {isStreaming && (
                    <div className="chat-message-wrapper ai">
                        <div className="chat-message ai" style={{ whiteSpace: 'pre-wrap' }}>
                            {streamingText} █
                        </div>
                    </div>
                )}
            </div>
            <div className="chat-input-wrapper">
                <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    className="chat-input"
                    placeholder="Ask a question..."
                />
                <button onClick={handleSend} disabled={isStreaming || isWaiting} className="btn-primary">Send</button>
            </div>
        </div>
    );
}