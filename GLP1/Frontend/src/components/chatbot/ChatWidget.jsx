import { useState } from 'react';
import { MessageCircle, X } from 'lucide-react';
import ChatPanel from './ChatPanel';

export default function ChatWidget() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {open && <ChatPanel onClose={() => setOpen(false)} />}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-[var(--color-primary)] text-white shadow-lg hover:bg-[var(--color-primary-light)] hover:shadow-xl transition-all flex items-center justify-center"
        aria-label={open ? 'Close assistant' : 'Open assistant'}
        title={open ? 'Close assistant' : 'Ask the analytics assistant'}
      >
        {open ? <X size={22} /> : <MessageCircle size={22} />}
      </button>
    </>
  );
}
