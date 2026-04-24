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
    <div className="w-full h-full flex flex-col bg-white">
      {/* Header */}
      <div className="p-4 border-b border-border">
        <button
          onClick={onNewThread}
          disabled={isLoading}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-primary hover:bg-primary-600 text-white rounded-full font-medium transition-all duration-200 shadow-subtle hover:shadow-card active:scale-95 disabled:opacity-50"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Chat
        </button>
      </div>

      {/* Thread List */}
      <div className="flex-1 overflow-y-auto py-2">
        {threads.length === 0 ? (
          <div className="p-6 text-center text-foreground-muted text-sm">
            <svg className="w-10 h-10 mx-auto mb-3 text-foreground-muted/50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <p className="text-foreground-secondary">No conversations yet</p>
            <p className="text-xs mt-1 text-foreground-muted">Start a new chat to begin</p>
          </div>
        ) : (
          <div className="px-2 space-y-1">
            {threads.map((thread) => (
              <div
                key={thread.threadId}
                className={cn(
                  'group relative px-3 py-3 rounded-xl cursor-pointer transition-all duration-150',
                  'hover:bg-background-tertiary',
                  activeThreadId === thread.threadId
                    ? 'bg-primary-50 border-l-[3px] border-primary'
                    : 'border-l-[3px] border-transparent'
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
                    <p className={cn(
                      'text-sm font-medium truncate',
                      activeThreadId === thread.threadId ? 'text-foreground' : 'text-foreground-secondary'
                    )}>
                      {truncateText(thread.sessionKey, 22)}
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
                      'opacity-0 group-hover:opacity-100 transition-opacity p-1.5 rounded-lg',
                      'hover:bg-error/10 text-foreground-muted hover:text-error',
                      deleteConfirm === thread.threadId && 'opacity-100 bg-error/10 text-error'
                    )}
                    title={deleteConfirm === thread.threadId ? 'Click again to confirm' : 'Delete thread'}
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer - Clean */}
      <div className="p-3 border-t border-border text-center bg-background-tertiary/30">
        <p className="text-xs text-foreground-muted">
          {threads.length} conversation{threads.length !== 1 ? 's' : ''}
        </p>
      </div>
    </div>
  );
}
