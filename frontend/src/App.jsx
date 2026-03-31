import { useState, useRef, useEffect } from 'react';
import UploadPanel from './components/UploadPanel';
import MessageBubble from './components/MessageBubble';
import AgentSteps from './components/AgentSteps';
import { askQuestion } from './services/api';
import useAgentStream from './hooks/useAgentStream';

export default function App() {
  const [sessionId, setSessionId] = useState(null);
  const [filename, setFilename] = useState('');
  const [question, setQuestion] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [mode, setMode] = useState('quick'); // 'quick' | 'deep'

  const { steps, answer, isRunning, error: agentError, run: runAgent, reset: resetAgent } = useAgentStream();
  const chatEndRef = useRef(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory, isTyping, isRunning]);

  // When a streaming agent run completes, append the final answer
  useEffect(() => {
    if (!isRunning && answer) {
      setChatHistory((prev) => {
        // Avoid appending the same answer twice
        const last = prev[prev.length - 1];
        if (last?.role === 'ai' && last?.text === answer) return prev;
        return [...prev, { role: 'ai', text: answer, steps }];
      });
      resetAgent();
    }
  }, [isRunning, answer]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleSessionReady = (sid, fname) => {
    setSessionId(sid);
    setFilename(fname);
    setChatHistory([]);
    resetAgent();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!question.trim() || !sessionId) return;

    const q = question.trim();
    setChatHistory((prev) => [...prev, { role: 'user', text: q }]);
    setQuestion('');

    if (mode === 'quick') {
      setIsTyping(true);
      try {
        const data = await askQuestion(sessionId, q);
        setChatHistory((prev) => [...prev, { role: 'ai', text: data.answer }]);
      } catch (err) {
        setChatHistory((prev) => [
          ...prev,
          { role: 'ai', text: `Error: ${err.message}` },
        ]);
      } finally {
        setIsTyping(false);
      }
    } else {
      resetAgent();
      runAgent(sessionId, q);
    }
  };

  const canSend = question.trim() && sessionId && !isTyping && !isRunning;

  return (
    <div className="min-h-screen bg-slate-50 p-8 font-sans">
      <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">

        {/* Left: Upload */}
        <div className="md:col-span-1">
          <UploadPanel onSessionReady={handleSessionReady} />

          {/* Mode toggle */}
          {sessionId && (
            <div className="mt-4 bg-white p-4 rounded-xl shadow-sm border border-slate-200">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Mode</p>
              <div className="flex flex-col gap-2">
                <ModeButton
                  active={mode === 'quick'}
                  onClick={() => setMode('quick')}
                  label="Quick Answer"
                  description="Fast single-step RAG"
                />
                <ModeButton
                  active={mode === 'deep'}
                  onClick={() => setMode('deep')}
                  label="Deep Analysis"
                  description="Agentic multi-step pipeline"
                />
              </div>
              <p className="text-xs text-slate-400 mt-2 break-all">
                Document: {filename}
              </p>
            </div>
          )}
        </div>

        {/* Right: Chat */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 md:col-span-2 flex flex-col h-[650px]">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">
            2. Ask in your preferred language
          </h2>

          <div className="flex-1 overflow-y-auto mb-4 border border-slate-100 rounded-lg p-4 bg-slate-50 flex flex-col gap-3">
            {chatHistory.length === 0 && !isRunning ? (
              <p className="text-slate-400 text-center mt-auto mb-auto">
                Upload a document to start the conversation.
              </p>
            ) : (
              <>
                {chatHistory.map((msg, idx) => (
                  <div key={idx}>
                    {msg.steps && msg.steps.length > 0 && (
                      <AgentSteps steps={msg.steps} isRunning={false} />
                    )}
                    <MessageBubble role={msg.role} text={msg.text} />
                  </div>
                ))}

                {/* Live agent steps for in-progress run */}
                {isRunning && (
                  <AgentSteps steps={steps} isRunning={isRunning} />
                )}
                {agentError && (
                  <MessageBubble role="ai" text={`Agent error: ${agentError}`} />
                )}
              </>
            )}

            {isTyping && (
              <div className="text-slate-400 text-sm self-start animate-pulse">
                Thinking…
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder={
                sessionId
                  ? 'e.g., ¿Cuáles son los puntos principales?'
                  : 'Upload a document first…'
              }
              disabled={!sessionId || isTyping || isRunning}
              className="flex-1 border border-slate-300 rounded-md px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-100"
            />
            <button
              type="submit"
              disabled={!canSend}
              className="bg-slate-800 text-white py-2 px-6 rounded-md font-medium hover:bg-slate-900 transition-colors disabled:bg-slate-300"
            >
              Send
            </button>
          </form>
        </div>

      </div>
    </div>
  );
}

function ModeButton({ active, onClick, label, description }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`text-left px-3 py-2 rounded-lg border text-sm transition-colors ${
        active
          ? 'border-blue-500 bg-blue-50 text-blue-700'
          : 'border-slate-200 text-slate-600 hover:border-slate-300'
      }`}
    >
      <span className="font-medium block">{label}</span>
      <span className="text-xs opacity-70">{description}</span>
    </button>
  );
}
