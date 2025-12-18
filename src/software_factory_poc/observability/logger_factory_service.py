import logging
import sys
from typing import Any, Dict, Optional

# Basic configuration to ensure logs go to stdout
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    force=True # Override any previous config
)

def build_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger instance.
    """
    return logging.getLogger(name)

def build_log_context(
    run_id: Optional[str] = None,
    issue_key: Optional[str] = None,
    step_name: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Builds a dictionary for use in logging 'extra' fields or structural logging.
    Since standard python logging %s formatting doesn't automatically print 'extra',
    we usually format this into the string or use a structured logger.
    
    For this PoC, we will return a string header to prepend to log messages,
    simulating structured logging context.
    
    Example Usage:
        ctx_str = log_context_string(run_id="...", ...)
        logger.info(f"{ctx_str} Starting render...")
    """
    # This helper was requested to build a dict, but standard logger usage varies.
    # We'll provide the dict for generic usage.
    context = {}
    if run_id:
        context["run_id"] = run_id
    if issue_key:
        context["issue_key"] = issue_key
    if step_name:
        context["step_name"] = step_name
    
    if extra:
        context.update(extra)
        
    return context

def log_context_string(
    run_id: Optional[str] = None,
    issue_key: Optional[str] = None,
    step_name: Optional[str] = None
) -> str:
    """
    Helper to create a standard prefix string '[run_id=... issue_key=...]'
    """
    parts = []
    if run_id:
        parts.append(f"run_id={run_id}")
    if issue_key:
        parts.append(f"issue_key={issue_key}")
    if step_name:
        parts.append(f"step={step_name}")
        
    if not parts:
        return ""
        
    return f"[{' '.join(parts)}]"
