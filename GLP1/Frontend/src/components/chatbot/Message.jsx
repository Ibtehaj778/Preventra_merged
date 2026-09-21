function renderInline(text) {
  const parts = [];
  let last = 0;
  const re = /(\*\*([^*]+)\*\*|`([^`]+)`)/g;
  let match;
  let key = 0;
  while ((match = re.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index));
    if (match[2] !== undefined) {
      parts.push(<strong key={`b-${key++}`}>{match[2]}</strong>);
    } else if (match[3] !== undefined) {
      parts.push(
        <code key={`c-${key++}`} className="bg-slate-100 rounded px-1 py-0.5 text-[12px] font-mono">
          {match[3]}
        </code>
      );
    }
    last = re.lastIndex;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

function renderContent(content) {
  const lines = (content || '').split('\n');
  const blocks = [];
  let list = null;

  const flushList = () => {
    if (!list) return;
    blocks.push(
      <ul key={`ul-${blocks.length}`} className="list-disc pl-5 space-y-0.5">
        {list.map((item, i) => (
          <li key={i}>{renderInline(item)}</li>
        ))}
      </ul>
    );
    list = null;
  };

  lines.forEach((raw, idx) => {
    const line = raw.trimEnd();
    const bulletMatch = line.match(/^\s*[-*]\s+(.*)$/);
    if (bulletMatch) {
      if (!list) list = [];
      list.push(bulletMatch[1]);
      return;
    }
    flushList();
    if (!line) {
      blocks.push(<div key={`sp-${idx}`} className="h-1.5" />);
      return;
    }
    blocks.push(
      <p key={`p-${idx}`} className="whitespace-pre-wrap">
        {renderInline(line)}
      </p>
    );
  });
  flushList();
  return blocks;
}

export default function Message({ message }) {
  const isUser = message.role === 'user';
  const isError = !!message.isError;
  const tools = (message.toolCalls || []).filter((t) => t?.name);

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} animate-fade-in`}>
      <div
        className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-[13.5px] leading-relaxed shadow-sm ${
          isUser
            ? 'bg-[var(--color-primary)] text-white rounded-br-sm'
            : isError
              ? 'bg-red-50 text-red-900 border border-red-200 rounded-bl-sm'
              : 'bg-slate-100 text-slate-900 rounded-bl-sm'
        }`}
      >
        <div className="space-y-1">{renderContent(message.content)}</div>
        {tools.length > 0 && !isUser && (
          <div className="mt-2 flex flex-wrap gap-1">
            {tools.map((t, i) => (
              <span
                key={i}
                className={`inline-flex items-center gap-1 text-[10.5px] font-medium rounded-full px-2 py-0.5 ${
                  t.ok === false
                    ? 'bg-red-100 text-red-700'
                    : 'bg-white/70 text-slate-600 border border-slate-200'
                }`}
                title={t.error || ''}
              >
                <span className="opacity-60">tool:</span>
                <code className="font-mono">{t.name}</code>
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
