'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Thread, ThreadSummary, Message } from '@/types';
import { ThreadSidebar } from './thread-sidebar';
import { MessageBubble } from './message-bubble';
import { TypingIndicator } from './typing-indicator';
import { WelcomeModal } from './welcome-modal';
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
  const [showWelcome, setShowWelcome] = useState(true);
  const [userName, setUserName] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const hasStartedRef = useRef(false);

  // Load threads on mount - only once
  useEffect(() => {
    if (!hasStartedRef.current) {
      loadThreads();
    }
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeThread?.messages, isTyping]);

  // Focus input when thread is active and not loading
  useEffect(() => {
    if (activeThread && !isLoading && !showWelcome) {
      inputRef.current?.focus();
    }
  }, [activeThread, isLoading, showWelcome]);

  async function loadThreads() {
    try {
      const threadList = await api.listThreads(20);
      setThreads(threadList);
      // Auto-select first thread if none active (only on initial load)
      if (!activeThread && !hasStartedRef.current && threadList.length > 0) {
        await selectThread(threadList[0].threadId);
      }
    } catch (err) {
      setError('Failed to load threads');
    }
  }

  async function handleWelcomeStart(name: string) {
    setUserName(name);
    setShowWelcome(false);
    hasStartedRef.current = true;
    
    // Create first thread for the user
    try {
      setIsLoading(true);
      const thread = await api.createThread(name);
      setActiveThread(thread);
      await loadThreads();
      // Focus input after thread creation
      setTimeout(() => inputRef.current?.focus(), 100);
    } catch (err) {
      setError('Failed to create thread');
    } finally {
      setIsLoading(false);
    }
  }

  async function createNewThread() {
    try {
      setIsLoading(true);
      const thread = await api.createThread(userName || undefined);
      setActiveThread(thread);
      // Clear input for new thread
      setInput('');
      await loadThreads();
      // Focus input after creation
      setTimeout(() => inputRef.current?.focus(), 100);
    } catch (err) {
      setError('Failed to create thread');
    } finally {
      setIsLoading(false);
    }
  }

  async function handleExampleQuestion(question: string) {
    if (!activeThread) {
      // Create new thread first if none exists
      await createNewThread();
    }
    setInput(question);
    // Focus input and allow user to edit before sending
    setTimeout(() => {
      inputRef.current?.focus();
      // Auto-resize textarea
      if (inputRef.current) {
        inputRef.current.style.height = 'auto';
        inputRef.current.style.height = inputRef.current.scrollHeight + 'px';
      }
    }, 100);
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
    const currentThreadId = activeThread.threadId;
    
    // Clear input immediately for better UX
    setInput('');
    setIsLoading(true);
    setIsTyping(true);
    setError(null);

    // Optimistically add user message to UI
    const newUserMessage: Message = {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString(),
    };

    setActiveThread(prev => {
      if (!prev || prev.threadId !== currentThreadId) return prev;
      return {
        ...prev,
        messages: [...prev.messages, newUserMessage],
        updatedAt: new Date().toISOString(),
      };
    });

    try {
      // Send message to API
      const response = await api.sendMessage(currentThreadId, userMessage);

      // Add assistant response to UI
      const assistantMessage: Message = {
        role: 'assistant',
        content: response.assistantMessage,
        timestamp: new Date().toISOString(),
        retrievalDebugId: response.debug ? JSON.stringify(response.debug) : undefined,
        isRefusal: response.assistantMessage.toLowerCase().includes('cannot provide') || 
                   response.assistantMessage.toLowerCase().includes('sorry'),
      };

      setActiveThread(prev => {
        if (!prev || prev.threadId !== currentThreadId) return prev;
        return {
          ...prev,
          messages: [...prev.messages, assistantMessage],
          updatedAt: new Date().toISOString(),
        };
      });

      // Refresh thread list in background (don't block)
      loadThreads().catch(() => {});
      
      // Refocus input for next message
      setTimeout(() => inputRef.current?.focus(), 50);
      
    } catch (err) {
      console.error('Failed to send message:', err);
      
      // Add error message to UI
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request. Please try again.',
        timestamp: new Date().toISOString(),
        isError: true,
      };

      setActiveThread(prev => {
        if (!prev || prev.threadId !== currentThreadId) return prev;
        return {
          ...prev,
          messages: [...prev.messages, errorMessage],
          updatedAt: new Date().toISOString(),
        };
      });

      setError('Failed to send message. Please try again.');
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
    <>
      {/* Welcome Modal */}
      {showWelcome && <WelcomeModal onStart={handleWelcomeStart} />}
      
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
            <p className="text-xs text-foreground-muted">
              {userName ? `Welcome, ${userName}` : 'Facts-only. No investment advice.'}
            </p>
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
                      onClick={() => handleExampleQuestion(q)}
                      disabled={isLoading}
                      className="w-full p-3 text-left bg-background-secondary hover:bg-background-tertiary rounded-lg border border-border hover:border-primary/50 transition-all text-sm text-foreground-secondary hover:text-foreground disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>

              <button
                onClick={() => handleExampleQuestion(EXAMPLE_QUESTIONS[0])}
                disabled={isLoading}
                className="mt-8 px-6 py-3 bg-primary hover:bg-primary-600 text-white rounded-lg font-medium transition-all shadow-glow hover:shadow-glow-lg disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? 'Creating thread...' : 'Start New Conversation'}
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
                    onClick={() => handleExampleQuestion(q)}
                    disabled={isLoading}
                    className="w-full p-3 text-left bg-background-secondary hover:bg-background-tertiary rounded-lg border border-border hover:border-primary/50 transition-all text-sm text-foreground-secondary hover:text-foreground disabled:opacity-50 disabled:cursor-not-allowed"
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
    </>
  );
}
