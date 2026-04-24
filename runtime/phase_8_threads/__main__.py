"""
Phase 8: Multi-Thread Chat CLI

Usage:
    python -m runtime.phase_8_threads new-thread
    python -m runtime.phase_8_threads say "message" [--thread <id>]
    python -m runtime.phase_8_threads history [--thread <id>]
    python -m runtime.phase_8_threads context [--thread <id>] [--turns 6]
    python -m runtime.phase_8_threads list-threads
    python -m runtime.phase_8_threads delete-thread <id>
"""

import argparse
import json
import logging
import os
import sys
from typing import Optional

from dotenv import load_dotenv

from runtime.phase_8_threads.storage import ThreadStorage, Message

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Active thread storage (in-memory for session)
_current_thread_id: Optional[str] = None


def get_storage() -> ThreadStorage:
    """Get thread storage instance."""
    db_path = os.getenv("THREAD_DB_PATH", "data/threads.db")
    return ThreadStorage(db_path)


def cmd_new_thread(args):
    """Create a new conversation thread."""
    storage = get_storage()
    thread = storage.create_thread(session_key=args.session)
    
    global _current_thread_id
    _current_thread_id = thread.thread_id
    
    if args.json:
        print(json.dumps(thread.to_dict(), indent=2))
    else:
        print(f"\n{'=' * 60}")
        print("NEW THREAD CREATED")
        print('=' * 60)
        print(f"Thread ID: {thread.thread_id}")
        print(f"Session: {thread.session_key}")
        print(f"Created: {thread.created_at}")
        print('=' * 60)
    
    return 0


def cmd_say(args):
    """Add a message to a thread."""
    storage = get_storage()
    thread_id = args.thread or _current_thread_id
    
    if not thread_id:
        logger.error("No thread specified. Use --thread or create one with new-thread")
        return 1
    
    # Check thread exists
    thread = storage.get_thread(thread_id)
    if not thread:
        logger.error(f"Thread not found: {thread_id}")
        return 1
    
    # Add user message
    success = storage.add_message(thread_id, "user", args.message)
    if not success:
        return 1
    
    if args.json:
        print(json.dumps({
            "thread_id": thread_id,
            "role": "user",
            "content": args.message,
            "status": "added"
        }, indent=2))
    else:
        print(f"\n{'=' * 60}")
        print("MESSAGE ADDED")
        print('=' * 60)
        print(f"Thread: {thread_id}")
        print(f"Role: user")
        print(f"Message: {args.message}")
        print('=' * 60)
    
    return 0


def cmd_reply(args):
    """Add an assistant reply to a thread."""
    storage = get_storage()
    thread_id = args.thread or _current_thread_id
    
    if not thread_id:
        logger.error("No thread specified")
        return 1
    
    success = storage.add_message(
        thread_id,
        "assistant",
        args.message,
        retrieval_debug_id=args.debug_id
    )
    
    if not success:
        return 1
    
    if args.json:
        print(json.dumps({
            "thread_id": thread_id,
            "role": "assistant",
            "content": args.message,
            "retrieval_debug_id": args.debug_id,
            "status": "added"
        }, indent=2))
    else:
        print(f"\n{'=' * 60}")
        print("ASSISTANT REPLY ADDED")
        print('=' * 60)
        print(f"Thread: {thread_id}")
        print(f"Message: {args.message[:100]}...")
        print('=' * 60)
    
    return 0


def cmd_history(args):
    """Show thread history."""
    storage = get_storage()
    thread_id = args.thread or _current_thread_id
    
    if not thread_id:
        logger.error("No thread specified")
        return 1
    
    thread = storage.get_thread(thread_id)
    if not thread:
        logger.error(f"Thread not found: {thread_id}")
        return 1
    
    if args.json:
        print(json.dumps(thread.to_dict(), indent=2))
    else:
        print(f"\n{'=' * 60}")
        print(f"THREAD HISTORY: {thread_id[:8]}...")
        print('=' * 60)
        print(f"Session: {thread.session_key}")
        print(f"Created: {thread.created_at}")
        print(f"Messages: {len(thread.messages)}")
        print('-' * 60)
        
        for i, msg in enumerate(thread.messages, 1):
            role_label = "You" if msg.role == "user" else "Assistant"
            content_preview = msg.content[:60] + "..." if len(msg.content) > 60 else msg.content
            print(f"\n[{i}] {role_label} ({msg.timestamp[:19]}):")
            print(f"    {content_preview}")
        
        print('\n' + '=' * 60)
    
    return 0


def cmd_context(args):
    """Show recent context (last N turns)."""
    storage = get_storage()
    thread_id = args.thread or _current_thread_id
    
    if not thread_id:
        logger.error("No thread specified")
        return 1
    
    messages = storage.get_recent_messages(thread_id, n_turns=args.turns)
    
    if not messages:
        logger.info("No messages in thread")
        return 0
    
    if args.json:
        print(json.dumps({
            "thread_id": thread_id,
            "turns": args.turns,
            "messages": [m.to_dict() for m in messages]
        }, indent=2))
    else:
        print(f"\n{'=' * 60}")
        print(f"RECENT CONTEXT (last {args.turns} turns)")
        print('=' * 60)
        
        for msg in messages:
            role_label = "You" if msg.role == "user" else "Assistant"
            print(f"\n{role_label}: {msg.content[:100]}")
        
        print('\n' + '=' * 60)
    
    return 0


def cmd_list_threads(args):
    """List all threads."""
    storage = get_storage()
    threads = storage.list_threads(limit=args.limit)
    
    if args.json:
        print(json.dumps({"threads": threads}, indent=2))
    else:
        print(f"\n{'=' * 60}")
        print("CONVERSATION THREADS")
        print('=' * 60)
        
        if not threads:
            print("No threads found")
        else:
            for t in threads:
                print(f"\n{t['thread_id'][:8]}... | {t['message_count']:3d} msgs | {t['updated_at'][:19]}")
                print(f"    Session: {t['session_key'][:20]}")
        
        print('\n' + '=' * 60)
        print(f"Total: {len(threads)} threads")
        print('=' * 60)
    
    return 0


def cmd_delete_thread(args):
    """Delete a thread."""
    storage = get_storage()
    
    if not args.thread_id:
        logger.error("Thread ID required")
        return 1
    
    success = storage.delete_thread(args.thread_id)
    
    if success:
        logger.info(f"Deleted thread: {args.thread_id}")
        return 0
    else:
        logger.error(f"Thread not found: {args.thread_id}")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Phase 8: Multi-Thread Chat Management"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # new-thread
    new_parser = subparsers.add_parser("new-thread", help="Create new conversation thread")
    new_parser.add_argument("--session", help="Session identifier")
    new_parser.set_defaults(func=cmd_new_thread)
    
    # say
    say_parser = subparsers.add_parser("say", help="Add user message to thread")
    say_parser.add_argument("message", help="Message content")
    say_parser.add_argument("--thread", help="Thread ID (or use current)")
    say_parser.set_defaults(func=cmd_say)
    
    # reply
    reply_parser = subparsers.add_parser("reply", help="Add assistant reply to thread")
    reply_parser.add_argument("message", help="Reply content")
    reply_parser.add_argument("--thread", help="Thread ID")
    reply_parser.add_argument("--debug-id", help="Retrieval debug ID")
    reply_parser.set_defaults(func=cmd_reply)
    
    # history
    hist_parser = subparsers.add_parser("history", help="Show thread history")
    hist_parser.add_argument("--thread", help="Thread ID")
    hist_parser.set_defaults(func=cmd_history)
    
    # context
    ctx_parser = subparsers.add_parser("context", help="Show recent context")
    ctx_parser.add_argument("--thread", help="Thread ID")
    ctx_parser.add_argument("--turns", type=int, default=6, help="Number of turns (default: 6)")
    ctx_parser.set_defaults(func=cmd_context)
    
    # list-threads
    list_parser = subparsers.add_parser("list-threads", help="List all threads")
    list_parser.add_argument("--limit", type=int, default=20, help="Max threads to show")
    list_parser.set_defaults(func=cmd_list_threads)
    
    # delete-thread
    del_parser = subparsers.add_parser("delete-thread", help="Delete a thread")
    del_parser.add_argument("thread_id", help="Thread ID to delete")
    del_parser.set_defaults(func=cmd_delete_thread)
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
