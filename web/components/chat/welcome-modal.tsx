'use client';

import { useState } from 'react';

interface WelcomeModalProps {
  onStart: (name: string) => void;
}

export function WelcomeModal({ onStart }: WelcomeModalProps) {
  const [name, setName] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!name.trim()) {
      setError('Please enter your name to continue');
      return;
    }
    
    if (name.trim().length < 2) {
      setError('Name must be at least 2 characters');
      return;
    }
    
    onStart(name.trim());
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/60 backdrop-blur-sm">
      <div className="w-full max-w-md p-8 mx-4 bg-white rounded-2xl border border-border shadow-card">
        {/* Logo */}
        <div className="flex justify-center mb-6">
          <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
            <svg className="w-8 h-8 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
        </div>

        {/* Title */}
        <h1 className="text-2xl font-semibold text-center text-foreground mb-2">
          Welcome to MF FAQ Assistant
        </h1>
        
        <p className="text-center text-foreground-secondary mb-8">
          Your trusted source for mutual fund information
        </p>

        {/* Features */}
        <div className="space-y-3 mb-8">
          <div className="flex items-center gap-3 text-sm text-foreground-secondary">
            <svg className="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span>Factual answers from official sources</span>
          </div>
          <div className="flex items-center gap-3 text-sm text-foreground-secondary">
            <svg className="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span>Multi-turn conversations supported</span>
          </div>
          <div className="flex items-center gap-3 text-sm text-foreground-secondary">
            <svg className="w-5 h-5 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span>No investment advice - just facts</span>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="name" className="block text-sm font-medium text-foreground mb-2">
              Enter your name to get started
            </label>
            <input
              type="text"
              id="name"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setError('');
              }}
              placeholder="Your name"
              className="w-full px-4 py-3 rounded-xl bg-background-tertiary border border-border text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
              autoFocus
            />
            {error && (
              <p className="mt-2 text-sm text-error">{error}</p>
            )}
          </div>

          <button
            type="submit"
            className="w-full py-3 px-6 bg-primary hover:bg-primary-600 text-white rounded-full font-medium transition-all duration-200 shadow-subtle hover:shadow-card focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
          >
            Start Conversation
          </button>
        </form>

        {/* Disclaimer */}
        <p className="mt-6 text-xs text-center text-foreground-muted leading-relaxed">
          By continuing, you agree that this assistant provides factual information only. 
          It does not provide investment advice.
        </p>
      </div>
    </div>
  );
}
