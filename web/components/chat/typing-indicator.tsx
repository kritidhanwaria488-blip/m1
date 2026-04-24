'use client';

export function TypingIndicator() {
  return (
    <div className="flex w-full justify-start">
      <div className="bg-white border border-border rounded-2xl rounded-bl-lg px-4 py-3.5 shadow-subtle">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 bg-foreground-muted/50 rounded-full typing-dot" />
          <span className="w-2 h-2 bg-foreground-muted/50 rounded-full typing-dot" />
          <span className="w-2 h-2 bg-foreground-muted/50 rounded-full typing-dot" />
        </div>
      </div>
    </div>
  );
}
