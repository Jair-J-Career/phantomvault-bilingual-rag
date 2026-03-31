const TOOL_ICONS = {
  detect_language: '🔍',
  retrieve: '📄',
  translate_chunks: '🌐',
  summarize: '📝',
  answer: '💬',
};

const STATUS_COLORS = {
  running: 'text-blue-500 animate-pulse',
  completed: 'text-emerald-600',
  error: 'text-red-500',
};

function Step({ step, isRunning }) {
  const icon = TOOL_ICONS[step.tool] || '⚙️';
  const statusClass = isRunning ? STATUS_COLORS.running : STATUS_COLORS[step.status] || STATUS_COLORS.completed;

  return (
    <div className="flex gap-3 text-sm">
      <div className="flex flex-col items-center">
        <span className="text-lg leading-none">{icon}</span>
        <div className="w-px flex-1 bg-slate-200 mt-1" />
      </div>
      <div className="pb-3 flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={`font-semibold ${statusClass}`}>{step.tool}</span>
          <span className="text-slate-400 text-xs">{step.latency_ms}ms</span>
        </div>
        <p className="text-slate-500 text-xs mt-0.5 truncate">{step.input_summary}</p>
        <p className="text-slate-700 mt-1 text-xs line-clamp-2">{step.output_summary}</p>
      </div>
    </div>
  );
}

export default function AgentSteps({ steps, isRunning }) {
  if (!steps.length && !isRunning) return null;

  return (
    <div className="border border-slate-100 rounded-lg p-3 bg-slate-50 mb-3">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
        Agent Execution
      </p>
      <div>
        {steps.map((step, i) => (
          <Step
            key={i}
            step={step}
            isRunning={isRunning && i === steps.length - 1}
          />
        ))}
        {isRunning && steps.length === 0 && (
          <p className="text-slate-400 text-xs animate-pulse">Planning…</p>
        )}
      </div>
    </div>
  );
}
