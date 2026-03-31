export default function MessageBubble({ role, text }) {
  const isUser = role === 'user';
  return (
    <div
      className={`p-3 rounded-lg max-w-[80%] whitespace-pre-wrap ${
        isUser
          ? 'bg-blue-600 text-white self-end'
          : 'bg-white border border-slate-200 text-slate-700 self-start'
      }`}
    >
      {text}
    </div>
  );
}
