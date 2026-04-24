'use client';

export function TypingIndicator() {
  return (
    <div className="flex w-full mb-4 justify-start">
      <div className="bg-background-secondary border border-border rounded-2xl rounded-bl-md px-4 py-3">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 bg-foreground-muted rounded-full typing-dot" />
          <span className="w-2 h-2 bg-foreground-muted rounded-full typing-dot" />
          <span className="w-2 h-2 bg-foreground-muted rounded-full typing-dot" />
        </div>
      </div>
    </div>
  );
}
