export interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  retrievalDebugId?: string;
  isError?: boolean;
  isRefusal?: boolean;
}

export interface Thread {
  threadId: string;
  sessionKey: string;
  createdAt: string;
  updatedAt: string;
  messages: Message[];
}

export interface ThreadSummary {
  threadId: string;
  sessionKey: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
}

export interface RetrievedChunk {
  chunkId: string;
  text: string;
  score: number;
  sourceUrl: string;
  schemeName: string;
  amc: string;
  fetchedAt: string;
}

export interface ChatResponse {
  assistantMessage: string;
  debug?: {
    retrievedChunks: number | RetrievedChunk[];
    scores: number[];
    safetyCheck: string;
    validation: boolean | object;
    retrievalLatencyMs: number;
    generationLatencyMs: number;
    latencyMs: number;
  };
}

export interface HealthStatus {
  status: string;
  version: string;
  components: {
    retriever: string;
    generator: string;
    safety: string;
    threads: string;
  };
}

export interface ApiError {
  detail: string;
  status?: number;
}
