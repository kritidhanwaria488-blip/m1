'use client';

import { cn, formatDate } from '@/lib/utils';
import { Message } from '@/types';
import { useState } from 'react';

interface MessageBubbleProps {
  message: Message;
  showTimestamp?: boolean;
}

export function MessageBubble({ message, showTimestamp = true }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const [showDebug, setShowDebug] = useState(false);

  // Extract URL from content if present
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  const contentWithLinks = message.content.replace(urlRegex, (url) => {
    return `<a href="${url}" target="_blank" rel="noopener noreferrer" class="text-primary hover:underline break-all">${url}</a>`;
  });

  return (
    <div
      className={cn(
        'flex w-full',
        isUser ? 'justify-end' : 'justify-start'
      )}
    >
      <div
        className={cn(
          'max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-3.5',
          'animate-fade-in shadow-subtle',
          isUser
            ? 'bg-primary text-white rounded-br-lg'
            : 'bg-white border border-border rounded-bl-lg'
        )}
      >
        {/* Message content */}
        <div
          className={cn(
            'text-sm leading-relaxed',
            isUser ? 'text-white' : 'text-foreground'
          )}
          dangerouslySetInnerHTML={{ __html: contentWithLinks }}
        />

        {/* Error indicator */}
        {message.isError && (
          <div className="mt-2 flex items-center gap-1.5 text-error/80 text-xs">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Error occurred
          </div>
        )}

        {/* Refusal indicator */}
        {message.isRefusal && (
          <div className="mt-2 flex items-center gap-1.5 text-warning text-xs">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Advisory query refused
          </div>
        )}

        {/* Timestamp */}
        {showTimestamp && (
          <div
            className={cn(
              'mt-2 text-xs',
              isUser ? 'text-white/70' : 'text-foreground-muted'
            )}
          >
            {formatDate(message.timestamp)}
          </div>
        )}

        {/* Debug info toggle */}
        {message.retrievalDebugId && (
          <button
            onClick={() => setShowDebug(!showDebug)}
            className="mt-2 text-xs text-foreground-muted hover:text-primary transition-colors"
          >
            {showDebug ? 'Hide debug' : 'Show debug'}
          </button>
        )}

        {/* Debug info */}
        {showDebug && message.retrievalDebugId && (
          <pre className="mt-2 p-2 bg-background-tertiary rounded-lg text-xs text-foreground-secondary overflow-x-auto">
            {message.retrievalDebugId}
          </pre>
        )}
      </div>
    </div>
  );
}
