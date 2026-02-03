import os
import sys
import logging
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from software_factory_poc.infrastructure.configuration.confluence_settings import ConfluenceSettings
from software_factory_poc.infrastructure.providers.research.clients.confluence_http_client import ConfluenceHttpClient

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ConfluenceProbe")

def log_page(page, prefix=""):
    pid = page.get("id")
    title = page.get("title", "No Title")
    status = page.get("status", "current")
    links = page.get("_links", {})
    webui = links.get("webui", "N/A")
    # Clean webui if it's relative
    if webui.startswith("/"):
        base = os.getenv("CONFLUENCE_BASE_URL", "https://jdalejandro91.atlassian.net/wiki").rstrip("/")
        webui = f"{base}{webui}"
        
    logger.info(f"{prefix}ID: {pid} | Status: {status} | Title: {repr(title)} | URL: {webui}")
    return pid, title

def diagnose():
    logger.info("🚀 Starting Confluence ROBUST Probe...")
    
    try:
        settings = ConfluenceSettings() # type: ignore
    except Exception as e:
        logger.error(f"❌ Failed to load settings: {e}")
        return

    client = ConfluenceHttpClient(settings)
    space_key = os.getenv("CONFLUENCE_SPACE_KEY", "DDS")
    
    def raw_search_cql(cql, limit=20, expand="version,ancestors"):
        try:
            logger.info(f"   Searching CQL: {cql}")
            resp = client.get("rest/api/content/search", params={"cql": cql, "limit": limit, "expand": expand})
            resp.raise_for_status()
            return resp.json().get("results", [])
        except Exception as e:
            logger.warning(f"   ⚠️ CQL Search failed: {e}")
            return None

    def raw_list_content(status="current", limit=20, expand="version,ancestors"):
        try:
            logger.info(f"   Listing Content (status={status})...")
            # Uses standard content endpoint which supports status param
            curr_params = {
                "spaceKey": space_key,
                "status": status,
                "limit": limit,
                "expand": expand
            }
            resp = client.get("rest/api/content", params=curr_params)
            resp.raise_for_status()
            return resp.json().get("results", [])
        except Exception as e:
            logger.error(f"   ❌ Content List failed: {e}")
            return []

    # =========================================================================
    # PHASE 0: Who Am I?
    # =========================================================================
    logger.info("\n🕵️  PHASE 0: Who Am I?")
    try:
        user_resp = client.get("rest/api/user/current")
        user_data = user_resp.json()
        logger.info(f"   ✅ {user_data.get('displayName')} ({user_data.get('email')})")
    except:
        logger.warning("   ⚠️  Could not get user info.")

    found_pages = []

    # =========================================================================
    # PHASE 1: The "Draft" Hunter
    # =========================================================================
    logger.info(f"\n👻 PHASE 1: The 'Draft' Hunter (Space: {space_key})")
    
    # Attempt 1: CQL
    cql_drafts = f'space = "{space_key}" AND type = "page" AND status = "draft" order by created desc'
    drafts = raw_search_cql(cql_drafts)
    
    # Attempt 2: Fallback to Content API if CQL failed (likely due to status field)
    if drafts is None:
        logger.info("   ⚠️ Falling back to /rest/api/content?status=draft")
        drafts = raw_list_content(status="draft")
    
    if drafts:
        for page in drafts:
            log_page(page, "   [DRAFT] ")
            found_pages.append(page)
    else:
        logger.info("   No DRAFT pages found.")


    # =========================================================================
    # PHASE 2: The "Title" Sniper (Term: 'shopping')
    # =========================================================================
    target_term = "shopping"
    logger.info(f"\n🎯 PHASE 2: The 'Title' Sniper (Term: '{target_term}')")
    
    # We will try searching by searching everything and filtering in python if status cql fails
    # Or just try specific clean queries.
    
    # 2.1 Current
    cql_curr = f'space = "{space_key}" AND title ~ "{target_term}"' # Defaults to current
    curr_res = raw_search_cql(cql_curr)
    if curr_res:
         for p in curr_res:
             log_page(p, "   [MATCH-CURRENT] ")
             found_pages.append(p)
             
    # 2.2 Draft (We already listed all drafts above, but let's filter if list was truncated, 
    # OR assume previous step covered it if we got all drafts. 
    # Let's rely on Phase 1 for drafts.)
    
    # 2.3 Historical? (Archived/Trashed)
    # CQL for historical/trashed is tricky.
    logger.info("   Checking 'historical' via separate CQL...")
    # status="historical" usually means versions. 
    # status="trashed" means deleted.
    cql_trash = f'space = "{space_key}" AND type = "page" AND status = "trashed" AND title ~ "{target_term}"'
    trash_res = raw_search_cql(cql_trash)
    if trash_res:
         for p in trash_res:
             log_page(p, "   [TRASHED] ")
             found_pages.append(p)

    if not found_pages:
        logger.warning(f"   No pages found matching '{target_term}' in any accessible state.")
    else:
        # Check if we have our target in found pages
        # Local fuzzy check
        for p in found_pages:
            t = p.get("title", "").lower().replace("-", "").replace(" ", "")
            if "shopping" in t and "cart" in t:
                 logger.info(f"   🎯 TARGET MATCH LIKELY: {p.get('title')}")


    # =========================================================================
    # PHASE 3: The "Ancestor" Trace
    # =========================================================================
    logger.info(f"\n🧬 PHASE 3: The 'Ancestor' Trace")
    
    # Filter unique by ID
    unique_pages = {p["id"]: p for p in found_pages}.values()
    
    if not unique_pages:
        logger.info("   Skipping Phase 3.")
    else:
        for child in unique_pages:
            ancestors = child.get("ancestors", [])
            logger.info(f"   Tracing Path for: '{child.get('title')}' ({child.get('status')})")
            if not ancestors:
                logger.info("      (No ancestors - likely a root page)")
                continue
                
            path_str = ""
            for anc in ancestors:
                aid = anc.get("id")
                atitle = anc.get("title")
                path_str += f"/{atitle}"
            logger.info(f"      Full Path: {path_str}/{child.get('title')}")

    logger.info("\n✅ Probe Complete.")

if __name__ == "__main__":
    diagnose()
