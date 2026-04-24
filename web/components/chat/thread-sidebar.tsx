'use client';

import { ThreadSummary } from '@/types';
import { cn, formatDate, truncateText } from '@/lib/utils';
import { useState } from 'react';

interface ThreadSidebarProps {
  threads: ThreadSummary[];
  activeThreadId: string | null;
  onSelectThread: (threadId: string) => void;
  onDeleteThread: (threadId: string) => void;
  onNewThread: () => void;
  isLoading?: boolean;
}

export function ThreadSidebar({
  threads,
  activeThreadId,
  onSelectThread,
  onDeleteThread,
  onNewThread,
  isLoading,
}: ThreadSidebarProps) {
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  return (
    <div className="w-full h-full flex flex-col bg-background-secondary border-r border-border">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <button
          onClick={onNewThread}
          disabled={isLoading}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-primary hover:bg-primary-600 text-white rounded-lg font-medium transition-all duration-200 shadow-glow hover:shadow-glow-lg active:scale-[0.98] disabled:opacity-50"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Chat
        </button>
      </div>

      {/* Thread List */}
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {threads.length === 0 ? (
          <div className="p-4 text-center text-foreground-muted text-sm">
            <svg className="w-12 h-12 mx-auto mb-2 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <p>No conversations yet</p>
            <p className="text-xs mt-1">Start a new chat to begin</p>
          </div>
        ) : (
          threads.map((thread) => (
            <div
              key={thread.threadId}
              className={cn(
                'group relative p-3 rounded-lg cursor-pointer transition-all duration-200',
                'hover:bg-background-tertiary/50',
                activeThreadId === thread.threadId
                  ? 'bg-primary/10 border-l-2 border-primary'
                  : 'border-l-2 border-transparent'
              )}
              onClick={() => onSelectThread(thread.threadId)}
            >
              <div className="flex items-start gap-3">
                {/* Icon */}
                <div className={cn(
                  'w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0',
                  activeThreadId === thread.threadId
                    ? 'bg-primary text-white'
                    : 'bg-background-tertiary text-foreground-secondary'
                )}>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                </div>

                {/* Thread Info */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">
                    {truncateText(thread.sessionKey, 25)}
                  </p>
                  <p className="text-xs text-foreground-muted mt-0.5">
                    {thread.messageCount} messages · {formatDate(thread.updatedAt)}
                  </p>
                </div>

                {/* Delete Button */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (deleteConfirm === thread.threadId) {
                      onDeleteThread(thread.threadId);
                      setDeleteConfirm(null);
                    } else {
                      setDeleteConfirm(thread.threadId);
                      setTimeout(() => setDeleteConfirm(null), 3000);
                    }
                  }}
                  className={cn(
                    'opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded',
                    'hover:bg-error/20 text-foreground-muted hover:text-error',
                    deleteConfirm === thread.threadId && 'opacity-100 bg-error/20 text-error'
                  )}
                  title={deleteConfirm === thread.threadId ? 'Click again to confirm' : 'Delete thread'}
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-border text-center">
        <p className="text-xs text-foreground-muted">
          {threads.length} conversation{threads.length !== 1 ? 's' : ''}
        </p>
      </div>
    </div>
  );
}
