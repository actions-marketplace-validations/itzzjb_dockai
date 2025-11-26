
import os

def smart_truncate(content: str, filename: str, max_chars: int, max_lines: int) -> str:
    """
    Truncates file content while preserving as much context as possible.
    
    Strategies:
    1. If content fits, return as is.
    2. If it's a code file (py, js, ts, go, rs, java), try to preserve structure.
    3. Fallback to Head + Tail truncation.
    """
    if len(content) <= max_chars and len(content.splitlines()) <= max_lines:
        return content

    lines = content.splitlines()
    total_lines = len(lines)
    
    # Strategy 1: Simple Head + Tail for non-code or massive files
    # We keep more of the head (context/imports) than the tail
    head_ratio = 0.7
    keep_lines = max_lines
    
    if total_lines > keep_lines:
        head_count = int(keep_lines * head_ratio)
        tail_count = keep_lines - head_count
        
        head = "\n".join(lines[:head_count])
        tail = "\n".join(lines[-tail_count:])
        
        return f"{head}\n\n... [TRUNCATED {total_lines - keep_lines} LINES] ...\n\n{tail}"
        
    return content
