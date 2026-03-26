import { useState } from 'react';

function App() {
  const [file, setFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState('');
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isTyping, setIsTyping] = useState(false);

  // 1. Send the PDF to FastAPI
  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    
    setUploadStatus('Uploading and parsing document...');
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      setUploadStatus(data.status);
    } catch (error) {
      setUploadStatus('Error: Could not connect to the server.');
    }
  };

  // 2. Send the question to FastAPI
  const handleAsk = async (e) => {
    e.preventDefault();
    if (!question.trim()) return;

    const newHistory = [...chatHistory, { role: 'user', text: question }];
    setChatHistory(newHistory);
    setQuestion('');
    setIsTyping(true);

    try {
      const response = await fetch(`http://127.0.0.1:8000/api/ask?question=${encodeURIComponent(question)}`, {
        method: 'POST',
      });
      const data = await response.json();
      
      setChatHistory([...newHistory, { role: 'ai', text: data.answer }]);
    } catch (error) {
      setChatHistory([...newHistory, { role: 'ai', text: 'Connection error. Is the backend running?' }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 p-8 font-sans">
      <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Left Column: Upload Zone */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 md:col-span-1 h-fit">
          <h1 className="text-2xl font-bold text-slate-800 mb-6">PhantomVault</h1>
          
          <form onSubmit={handleUpload} className="flex flex-col gap-4">
            <label className="text-sm font-semibold text-slate-600">1. Upload Document (English)</label>
            <input 
              type="file" 
              accept="application/pdf"
              onChange={(e) => setFile(e.target.files[0])}
              className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
            <button 
              type="submit"
              className="bg-blue-600 text-white py-2 px-4 rounded-md font-medium hover:bg-blue-700 transition-colors disabled:bg-slate-300"
              disabled={!file}
            >
              Process PDF
            </button>
            {uploadStatus && <p className="text-sm text-emerald-600 font-medium mt-2">{uploadStatus}</p>}
          </form>
        </div>

        {/* Right Column: Chat Interface */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 md:col-span-2 flex flex-col h-[600px]">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">2. Ask in your preferred language</h2>
          
          {/* Chat Window */}
          <div className="flex-1 overflow-y-auto mb-4 border border-slate-100 rounded-lg p-4 bg-slate-50 flex flex-col gap-3">
            {chatHistory.length === 0 ? (
              <p className="text-slate-400 text-center mt-auto mb-auto">Upload a document to start the conversation.</p>
            ) : (
              chatHistory.map((msg, idx) => (
                <div key={idx} className={`p-3 rounded-lg max-w-[80%] ${msg.role === 'user' ? 'bg-blue-600 text-white self-end' : 'bg-white border border-slate-200 text-slate-700 self-start'}`}>
                  {msg.text}
                </div>
              ))
            )}
            {isTyping && <div className="text-slate-400 text-sm self-start animate-pulse">PhantomVault is translating and thinking...</div>}
          </div>

          {/* Input Box */}
          <form onSubmit={handleAsk} className="flex gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g., ¿Cuáles son los puntos principales de este texto?"
              className="flex-1 border border-slate-300 rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button 
              type="submit"
              className="bg-slate-800 text-white py-2 px-6 rounded-md font-medium hover:bg-slate-900 transition-colors disabled:bg-slate-300"
              disabled={!question.trim() || chatHistory.length === 0 && !uploadStatus.includes('memorized')}
            >
              Send
            </button>
          </form>
        </div>

      </div>
    </div>
  );
}

export default App;