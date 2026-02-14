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
    ptype = page.get("type", "unknown")
    links = page.get("_links", {})
    webui = links.get("webui", "N/A")
    # Clean webui if it's relative
    if webui.startswith("/"):
        base = os.getenv("CONFLUENCE_BASE_URL", "https://jdalejandro91.atlassian.net/wiki").rstrip("/")
        webui = f"{base}{webui}"
        
    logger.info(f"{prefix}ID: {pid} | Type: {ptype} | Status: {status} | Title: {repr(title)} | URL: {webui}")
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
            # Ensure we pass limit to client if logic allows, or params
            # Client supports params dict directly in get
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
    cql_drafts = f'space = "{space_key}" AND type = "page" AND status = "draft" order by created desc'
    drafts = raw_search_cql(cql_drafts)
    
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
    # PHASE 2: The "Title" Sniper
    # =========================================================================
    target_term = "shopping"
    logger.info(f"\n🎯 PHASE 2: The 'Title' Sniper (Term: '{target_term}')")
    
    # 2.1 Current (Broad)
    cql_curr = f'space = "{space_key}" AND title ~ "{target_term}"' 
    curr_res = raw_search_cql(cql_curr)
    if curr_res:
         for p in curr_res:
             log_page(p, "   [MATCH-CURRENT] ")
             found_pages.append(p)

    # 2.2 Check Type for Exact "shopping-cart"
    # This is critical to see if type="page" is valid
    exact_target = "shopping-cart"
    logger.info(f"\n🧪 PHASE 2.2: Checking Type/Existence for '{exact_target}'")
    
    # Use simple CONTAINS logic for parts to find it
    cql_type = f'space = "{space_key}" AND title ~ "shopping" AND title ~ "cart"'
    # Note: I REMOVED 'type = "page"' from this query to see if it shows up without type filter
    type_res = raw_search_cql(cql_type)
    
    if type_res:
        for p in type_res:
             log_page(p, "   [TYPE-CHECK] ")
             if "shopping-cart" in p.get("title", "").lower():
                 if p.get("type") != "page":
                     logger.warning(f"   🚨 ALERT: Page type is '{p.get('type')}', NOT 'page'!")
    else:
        logger.warning("   Could not find page via AND query in Type Check.")
        # Try OR query
        cql_or = f'space = "{space_key}" AND (title ~ "shopping" OR title ~ "cart")'
        or_res = raw_search_cql(cql_or)
        if or_res:
             for p in or_res:
                 log_page(p, "   [OR-CHECK] ")


    logger.info("\n✅ Probe Complete.")

if __name__ == "__main__":
    diagnose()
