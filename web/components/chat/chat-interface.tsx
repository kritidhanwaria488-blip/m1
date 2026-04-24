'use client';

import { useState, useRef, useEffect } from 'react';
import { Thread, ThreadSummary, Message } from '@/types';
import { ThreadSidebar } from './thread-sidebar';
import { MessageBubble } from './message-bubble';
import { TypingIndicator } from './typing-indicator';
import { cn } from '@/lib/utils';
import * as api from '@/lib/api';

const EXAMPLE_QUESTIONS = [
  'What is the expense ratio of HDFC ELSS?',
  'What is the minimum SIP amount for HDFC Mid Cap Fund?',
  'What is the lock-in period for ELSS schemes?',
];

export function ChatInterface() {
  const [threads, setThreads] = useState<ThreadSummary[]>([]);
  const [activeThread, setActiveThread] = useState<Thread | null>(null);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Load threads on mount
  useEffect(() => {
    loadThreads();
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeThread?.messages, isTyping]);

  async function loadThreads() {
    try {
      const threadList = await api.listThreads(20);
      setThreads(threadList);
      // Auto-select first thread if none active
      if (!activeThread && threadList.length > 0) {
        await selectThread(threadList[0].threadId);
      }
    } catch (err) {
      setError('Failed to load threads');
    }
  }

  async function createNewThread() {
    try {
      setIsLoading(true);
      const thread = await api.createThread();
      setActiveThread(thread);
      await loadThreads();
      inputRef.current?.focus();
    } catch (err) {
      setError('Failed to create thread');
    } finally {
      setIsLoading(false);
    }
  }

  async function selectThread(threadId: string) {
    try {
      const thread = await api.getThread(threadId);
      setActiveThread(thread);
      setError(null);
    } catch (err) {
      setError('Failed to load thread');
    }
  }

  async function deleteThread(threadId: string) {
    try {
      await api.deleteThread(threadId);
      if (activeThread?.threadId === threadId) {
        setActiveThread(null);
      }
      await loadThreads();
    } catch (err) {
      setError('Failed to delete thread');
    }
  }

  async function sendMessage() {
    if (!input.trim() || !activeThread || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setIsLoading(true);
    setIsTyping(true);
    setError(null);

    // Optimistically add user message
    const newMessage: Message = {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString(),
    };

    setActiveThread(prev => prev ? {
      ...prev,
      messages: [...prev.messages, newMessage],
    } : prev);

    try {
      const response = await api.sendMessage(activeThread.threadId, userMessage);

      // Add assistant response
      const assistantMessage: Message = {
        role: 'assistant',
        content: response.assistantMessage,
        timestamp: new Date().toISOString(),
        retrievalDebugId: response.debug ? JSON.stringify(response.debug) : undefined,
        isRefusal: response.assistantMessage.toLowerCase().includes('cannot provide'),
      };

      setActiveThread(prev => prev ? {
        ...prev,
        messages: [...prev.messages, assistantMessage],
      } : prev);

      // Refresh thread list to update order
      await loadThreads();
    } catch (err) {
      // Add error message
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date().toISOString(),
        isError: true,
      };

      setActiveThread(prev => prev ? {
        ...prev,
        messages: [...prev.messages, errorMessage],
      } : prev);

      setError('Failed to send message');
    } finally {
      setIsLoading(false);
      setIsTyping(false);
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      {/* Sidebar */}
      <div className="w-80 flex-shrink-0 hidden md:block">
        <ThreadSidebar
          threads={threads}
          activeThreadId={activeThread?.threadId || null}
          onSelectThread={selectThread}
          onDeleteThread={deleteThread}
          onNewThread={createNewThread}
          isLoading={isLoading}
        />
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="h-16 border-b border-border flex items-center justify-between px-4 sm:px-6 bg-background-secondary/50 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-glow">
              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-semibold text-foreground">MF FAQ Assistant</h1>
              <p className="text-xs text-foreground-muted">Facts-only. No investment advice.</p>
            </div>
          </div>

          {/* Mobile menu button */}
          <button className="md:hidden p-2 rounded-lg hover:bg-background-tertiary">
            <svg className="w-6 h-6 text-foreground" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </header>

        {/* Error Banner */}
        {error && (
          <div className="bg-error/10 border-b border-error/20 px-4 py-2 text-sm text-error flex items-center justify-between">
            <span>{error}</span>
            <button onClick={() => setError(null)} className="text-error hover:text-error/80">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6">
          {!activeThread ? (
            // Welcome State
            <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary to-accent flex items-center justify-center shadow-glow-lg mb-6">
                <svg className="w-10 h-10 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-foreground mb-2 gradient-text">Welcome to MF FAQ Assistant</h2>
              <p className="text-foreground-secondary mb-8">
                Ask factual questions about mutual fund schemes. I provide information from official sources only.
              </p>

              <div className="w-full">
                <p className="text-sm text-foreground-muted mb-3">Try asking:</p>
                <div className="space-y-2">
                  {EXAMPLE_QUESTIONS.map((q, i) => (
                    <button
                      key={i}
                      onClick={() => {
                        if (!activeThread) createNewThread();
                        setInput(q);
                      }}
                      className="w-full p-3 text-left bg-background-secondary hover:bg-background-tertiary rounded-lg border border-border hover:border-primary/50 transition-all text-sm text-foreground-secondary hover:text-foreground"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={createNewThread}
                className="mt-8 px-6 py-3 bg-primary hover:bg-primary-600 text-white rounded-lg font-medium transition-all shadow-glow hover:shadow-glow-lg"
              >
                Start New Conversation
              </button>
            </div>
          ) : activeThread.messages.length === 0 ? (
            // Empty Thread
            <div className="h-full flex flex-col items-center justify-center text-center">
              <p className="text-foreground-muted mb-4">Start the conversation by sending a message</p>
              <div className="space-y-2 w-full max-w-md">
                {EXAMPLE_QUESTIONS.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => setInput(q)}
                    className="w-full p-3 text-left bg-background-secondary hover:bg-background-tertiary rounded-lg border border-border hover:border-primary/50 transition-all text-sm text-foreground-secondary hover:text-foreground"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            // Message List
            <>
              {activeThread.messages.map((message, index) => (
                <MessageBubble
                  key={index}
                  message={message}
                  showTimestamp={true}
                />
              ))}
              {isTyping && <TypingIndicator />}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-border p-4 bg-background-secondary/50">
          <div className="max-w-4xl mx-auto flex gap-3">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={activeThread ? "Ask about mutual funds..." : "Start a new conversation first"}
              disabled={!activeThread || isLoading}
              rows={1}
              className={cn(
                'flex-1 resize-none rounded-xl px-4 py-3 bg-background-tertiary border border-border',
                'text-foreground placeholder:text-foreground-muted',
                'focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary',
                'transition-all duration-200',
                (!activeThread || isLoading) && 'opacity-50 cursor-not-allowed'
              )}
              style={{ minHeight: '48px', maxHeight: '120px' }}
            />
            <button
              onClick={sendMessage}
              disabled={!input.trim() || !activeThread || isLoading}
              className={cn(
                'px-4 py-3 rounded-xl bg-primary hover:bg-primary-600 text-white',
                'transition-all duration-200 shadow-glow hover:shadow-glow-lg',
                'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2',
                'active:scale-[0.98]',
                (!input.trim() || !activeThread || isLoading) && 'opacity-50 cursor-not-allowed'
              )}
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
          <p className="text-center text-xs text-foreground-muted mt-2">
            Facts-only. No investment advice. Responses include source links and last updated date.
          </p>
        </div>
      </div>
    </div>
  );
}
