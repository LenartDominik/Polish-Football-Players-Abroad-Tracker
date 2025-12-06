"""
FBref Scraper using Playwright - More reliable than cloudscraper
Uses real browser automation to bypass anti-bot protection
"""
import asyncio
import time
import re
from typing import Optional, Dict, List
from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


class FBrefPlaywrightScraper:
    """Scraper using Playwright for reliable FBref access"""
    
    BASE_URL = "https://fbref.com"
    
    def __init__(self, headless: bool = True, rate_limit_seconds: float = 12.0):
        """
        Initialize the Playwright scraper
        
        Args:
            headless: Run browser in headless mode (True) or visible mode (False)
            rate_limit_seconds: Minimum seconds between requests (default 12)
        """
        self.headless = headless
        self.rate_limit_seconds = rate_limit_seconds
        self.last_request_time = 0
        self.browser: Optional[Browser] = None
        self.playwright = None
        logger.info(f"FBref Playwright scraper initialized (rate limit: {rate_limit_seconds}s)")
    
    async def __aenter__(self):
        """Context manager entry"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        await self.close()
    
    async def start(self):
        """Start the browser"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        logger.info("Browser started")
    
    async def close(self):
        """Close the browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")
    
    async def _wait_for_rate_limit(self):
        """Wait to respect rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.rate_limit_seconds:
            wait_time = self.rate_limit_seconds - time_since_last
            logger.info(f"⏳ Waiting {wait_time:.1f}s for rate limit...")
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    async def _create_page(self) -> Page:
        """Create a new page with realistic settings"""
        context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US'
        )
        page = await context.new_page()
        
        # Hide automation indicators
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        return page
    
    async def _fetch_all_comps_page(self, player_id: str) -> Optional[BeautifulSoup]:
        """Fetch and parse the /all_comps/ page for a player"""
        try:
            all_comps_url = f"{self.BASE_URL}/en/players/{player_id}/all_comps/"
            
            page = await self._create_page()
            await page.goto(all_comps_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(1.5)  # Wait for any JS to load
            
            content = await page.content()
            await page.close()
            
            return BeautifulSoup(content, 'html.parser')
            
        except Exception as e:
            logger.error(f"Error fetching /all_comps/ page: {e}")
            return None
    
    async def get_player_by_id(self, player_id: str, player_name: str = "") -> Optional[Dict]:
        # Helper inside class to fetch extra GK sections by page
        async def _fetch_gk_section(path_suffix: str, table_id: str, comp_type: Optional[str]):
            try:
                await self._wait_for_rate_limit()
                page = await self._create_page()
                url = f"{self.BASE_URL}/en/players/{player_id}/{path_suffix}"
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(1.5)
                html = await page.content()
                await page.context.close()
                soup2 = BeautifulSoup(html, 'html.parser')
                table = soup2.find('table', {'id': table_id})
                if table:
                    return self._parse_goalkeeper_table(table, comp_type)
            except Exception as e:
                logger.warning(f"[GK_FALLBACK] Failed fetching {path_suffix}: {e}")
            return []
        """
        Get player data directly by FBref player ID
        
        Args:
            player_id: FBref player ID (e.g., '8d78e732')
            player_name: Player name for URL (optional)
        
        Returns:
            Dictionary with player data including competition stats
        """
        await self._wait_for_rate_limit()
        
        name_slug = player_name.replace(' ', '-') if player_name else 'player'
        player_url = f"{self.BASE_URL}/en/players/{player_id}/{name_slug}"
        
        logger.info(f"🔗 Fetching player: {player_url}")
        
        page = await self._create_page()
        
        try:
            await page.goto(player_url, wait_until="networkidle", timeout=30000)
            
            # Check if we got the player page
            if '/players/' not in page.url:
                logger.error(f"Not redirected to player page: {page.url}")
                return None
            
            # Get page content
            content = await page.content()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            player_data = await self._parse_player_page(soup, page.url)
            
            logger.info(f"✅ Successfully fetched player data")
            return player_data
            
        except Exception as e:
            logger.error(f"Error fetching player by ID {player_id}: {e}", exc_info=True)
            return None
        finally:
            await page.close()
    
    async def search_player(self, player_name: str) -> Optional[Dict]:
        """
        Search for a player by name
        
        Args:
            player_name: Player name to search for
        
        Returns:
            Dictionary with player data
        """
        await self._wait_for_rate_limit()
        
        search_url = f"{self.BASE_URL}/en/search/search.fcgi?search={player_name.replace(' ', '+')}"
        
        logger.info(f"🔍 Searching for: {player_name}")
        
        page = await self._create_page()
        
        try:
            await page.goto(search_url, wait_until="networkidle", timeout=30000)
            
            # Check if redirected to player page directly
            if '/players/' in page.url:
                logger.info("✅ Redirected directly to player page")
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                return await self._parse_player_page(soup, page.url)
            
            # Otherwise, find first player result
            first_result = await page.query_selector('.search-item-name a')
            if not first_result:
                logger.warning(f"No player found for: {player_name}")
                return None
            
            player_href = await first_result.get_attribute('href')
            player_url = f"{self.BASE_URL}{player_href}"
            
            logger.info(f"🔗 Found player: {player_url}")
            
            # Wait for rate limit before next request
            await self._wait_for_rate_limit()
            
            # Go to player page
            await page.goto(player_url, wait_until="networkidle", timeout=30000)
            content = await page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            return await self._parse_player_page(soup, page.url)
            
        except Exception as e:
            logger.error(f"Error searching player {player_name}: {e}", exc_info=True)
            return None
        finally:
            await page.close()
    
    async def _parse_player_page(self, soup: BeautifulSoup, url: str) -> Dict:
        """Parse player page and extract data - now uses /all_comps/ page for complete data"""
        
        player_data = {
            'url': url,
            'name': None,
            'competition_stats': []
        }
        
        # Extract player ID from URL
        player_id = None
        if '/players/' in url:
            parts = url.split('/players/')
            if len(parts) > 1:
                player_id = parts[1].split('/')[0]
                player_data['player_id'] = player_id
        
        # Get player name
        name_elem = soup.find('h1')
        if name_elem:
            player_data['name'] = name_elem.get_text(strip=True)
        
        # Get current team
        strong_club = soup.find('strong', string=re.compile('Club|Team'))
        if strong_club and strong_club.parent:
            club_link = strong_club.parent.find('a')
            if club_link:
                player_data['team'] = club_link.get_text(strip=True)
            else:
                # Try to get text after the strong tag
                text = strong_club.parent.get_text(strip=True)
                # Remove "Club:" prefix
                if ':' in text:
                    player_data['team'] = text.split(':', 1)[1].strip()
        
        # If we have player_id, fetch from /all_comps/ page for complete data
        if player_id:
            logger.info(f"📊 Fetching complete stats from /all_comps/ page...")
            all_comps_soup = await self._fetch_all_comps_page(player_id)
            if all_comps_soup:
                player_data['competition_stats'] = self._parse_competition_stats(all_comps_soup)
            else:
                # Fallback to current page
                logger.warning("⚠️ Could not fetch /all_comps/, using current page")
                player_data['competition_stats'] = self._parse_competition_stats(soup)
        else:
            # Parse from current page if no player_id
            player_data['competition_stats'] = self._parse_competition_stats(soup)
        
        # DEBUG: Log all competition_name and season for diagnostics
        for stat in player_data['competition_stats']:
            logger.info(f"[COMP_DEBUG] season={stat.get('season')} comp={stat.get('competition_name')}")

        return player_data
    
    def _parse_competition_stats(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Parse competition statistics from player page
        Separates stats by League, European Cups, and National Team
        Also checks HTML comments for hidden tables
        """
        competition_stats = []
        
        # Helper function to find table in comments
        def find_table_in_comments(table_id: str):
            """Find table in HTML comments"""
            import re
            for comment in soup.find_all(string=lambda text: isinstance(text, str) and table_id in text):
                if '<table' in str(comment):
                    comment_soup = BeautifulSoup(str(comment), 'html.parser')
                    table = comment_soup.find('table', {'id': table_id})
                    if table:
                        logger.info(f"✅ Found {table_id} in HTML comments")
                        return table
            return None
        
        # Find the standard stats table (domestic leagues)
        stats_table = soup.find('table', {'id': 'stats_standard_dom_lg'})
        if not stats_table:
            stats_table = find_table_in_comments('stats_standard_dom_lg')
        if stats_table:
            league_stats = self._parse_stats_table(stats_table, 'LEAGUE')
            
            # Try to get Expected stats table for xG/npxG/xAG (often in comments)
            expected_table = soup.find('table', {'id': 'stats_expected_dom_lg'})
            if not expected_table:
                logger.info("🔍 Expected table not in visible HTML, checking comments...")
                expected_table = find_table_in_comments('stats_expected_dom_lg')
            
            if expected_table:
                logger.info("✅ Found Expected stats table for domestic league")
                expected_stats = self._parse_expected_table(expected_table)
                logger.info(f"📊 Parsed {len(expected_stats)} Expected stat rows")
                if expected_stats:
                    logger.info(f"   Example: {expected_stats[0]}")
                league_stats = self._merge_expected_stats(league_stats, expected_stats)
            else:
                logger.warning("⚠️ Expected stats table NOT FOUND for domestic league - trying shooting table as fallback")
                # Try to get xG from shooting table
                shooting_table = soup.find('table', {'id': 'stats_shooting_dom_lg'})
                if not shooting_table:
                    shooting_table = find_table_in_comments('stats_shooting_dom_lg')
                if shooting_table:
                    logger.info("✅ Found Shooting stats table for domestic league")
                    shooting_stats = self._parse_shooting_table(shooting_table)
                    league_stats = self._merge_expected_stats(league_stats, shooting_stats)
                else:
                    logger.warning("⚠️ Shooting stats table also NOT FOUND - xG/npxG/xAG will be missing")
            
            competition_stats.extend(league_stats)
        
        # Find domestic cup stats (from /all_comps/ page)
        dom_cup_table = soup.find('table', {'id': 'stats_standard_dom_cup'})
        if not dom_cup_table:
            dom_cup_table = find_table_in_comments('stats_standard_dom_cup')
        if dom_cup_table:
            dom_cup_stats = self._parse_stats_table(dom_cup_table, 'DOMESTIC_CUP')
            
            # Try to get Expected stats for domestic cups
            expected_dom_cup = soup.find('table', {'id': 'stats_expected_dom_cup'})
            if not expected_dom_cup:
                expected_dom_cup = find_table_in_comments('stats_expected_dom_cup')
            if expected_dom_cup:
                logger.info("✅ Found Expected stats table for domestic cups")
                expected_stats = self._parse_expected_table(expected_dom_cup)
                dom_cup_stats = self._merge_expected_stats(dom_cup_stats, expected_stats)
            else:
                # Try shooting table as fallback
                shooting_dom_cup = soup.find('table', {'id': 'stats_shooting_dom_cup'})
                if not shooting_dom_cup:
                    shooting_dom_cup = find_table_in_comments('stats_shooting_dom_cup')
                if shooting_dom_cup:
                    logger.info("✅ Found Shooting stats table for domestic cups (fallback)")
                    shooting_stats = self._parse_shooting_table(shooting_dom_cup)
                    dom_cup_stats = self._merge_expected_stats(dom_cup_stats, shooting_stats)
            
            competition_stats.extend(dom_cup_stats)
        
        # Find international cup stats (European competitions from /all_comps/ page)
        intl_cup_table = soup.find('table', {'id': 'stats_standard_intl_cup'})
        if not intl_cup_table:
            intl_cup_table = find_table_in_comments('stats_standard_intl_cup')
        if intl_cup_table:
            intl_cup_stats = self._parse_stats_table(intl_cup_table, 'EUROPEAN_CUP')
            
            # Try to get Expected stats for international cups
            expected_intl_cup = soup.find('table', {'id': 'stats_expected_intl_cup'})
            if not expected_intl_cup:
                expected_intl_cup = find_table_in_comments('stats_expected_intl_cup')
            if expected_intl_cup:
                logger.info("✅ Found Expected stats table for international cups")
                expected_stats = self._parse_expected_table(expected_intl_cup)
                intl_cup_stats = self._merge_expected_stats(intl_cup_stats, expected_stats)
            else:
                # Try shooting table as fallback
                shooting_intl_cup = soup.find('table', {'id': 'stats_shooting_intl_cup'})
                if not shooting_intl_cup:
                    shooting_intl_cup = find_table_in_comments('stats_shooting_intl_cup')
                if shooting_intl_cup:
                    logger.info("✅ Found Shooting stats table for international cups (fallback)")
                    shooting_stats = self._parse_shooting_table(shooting_intl_cup)
                    intl_cup_stats = self._merge_expected_stats(intl_cup_stats, shooting_stats)
            
            competition_stats.extend(intl_cup_stats)
        
        # Find club competition stats (fallback, includes European competitions)
        club_comps_table = soup.find('table', {'id': 'stats_standard_club_comps'})
        if not club_comps_table:
            club_comps_table = find_table_in_comments('stats_standard_club_comps')
        if club_comps_table:
            # This table includes both league and European competitions
            stats = self._parse_stats_table(club_comps_table, None)
            for stat in stats:
                # Determine competition type from competition name
                comp_name = stat.get('competition_name', '').lower()
                # Domestic cup keywords (Copa, FA Cup, DFB-Pokal, etc.) - CHECK FIRST
                domestic_cup_keywords = [
                    'copa del rey', 'copa', 'pokal', 'coupe', 'coppa',
                    'fa cup', 'league cup', 'efl', 'carabao',
                    'dfb-pokal', 'dfl-supercup', 'supercopa', 'supercoppa',
                    'u.s. open cup', 'leagues cup'
                ]
                # European competition keywords
                european_keywords = [
                    'champions', 'europa', 'uefa', 'conference',
                    'champions lg', 'europa lg', 'ucl', 'uel', 'uecl',
                    'european', 'cup winners', 'super cup', 'club world cup'
                ]
                
                # Check if it's a domestic cup FIRST (before European)
                if any(keyword in comp_name for keyword in domestic_cup_keywords):
                    stat['competition_type'] = 'DOMESTIC_CUP'
                # Check if it's a European competition
                elif any(keyword in comp_name for keyword in european_keywords):
                    stat['competition_type'] = 'EUROPEAN_CUP'
                # Otherwise it's probably a league
                else:
                    # Check if we already have this season/competition as league
                    is_duplicate = False
                    for existing in competition_stats:
                        if (existing.get('season') == stat.get('season') and 
                            existing.get('competition_name') == stat.get('competition_name') and
                            existing.get('competition_type') == 'LEAGUE'):
                            is_duplicate = True
                            break
                    
                    if not is_duplicate:
                        stat['competition_type'] = 'LEAGUE'
                    else:
                        continue  # Skip duplicate league entry
            
            competition_stats.extend(stats)
        
        # Find national team stats (from /all_comps/ page)
        nat_tm_table = soup.find('table', {'id': 'stats_standard_nat_tm'})
        if not nat_tm_table:
            nat_tm_table = find_table_in_comments('stats_standard_nat_tm')
        if nat_tm_table:
            competition_stats.extend(self._parse_stats_table(nat_tm_table, 'NATIONAL_TEAM'))
        
        # Find international stats (fallback, national team)
        intl_table = soup.find('table', {'id': 'stats_standard_intl'})
        if not intl_table:
            intl_table = find_table_in_comments('stats_standard_intl')
        if intl_table:
            competition_stats.extend(self._parse_stats_table(intl_table, 'NATIONAL_TEAM'))

        # --- GOALKEEPER STATS (ADVANCED) ---
        # Domestic league goalkeeper stats
        gk_dom_table = soup.find('table', {'id': 'stats_keeper_dom_lg'})
        if not gk_dom_table:
            gk_dom_table = find_table_in_comments('stats_keeper_dom_lg')
        if gk_dom_table:
            competition_stats = self._merge_goalkeeper_stats(competition_stats, self._parse_goalkeeper_table(gk_dom_table, 'LEAGUE'))

        # Domestic cup goalkeeper stats (from /all_comps/)
        gk_dom_cup_table = soup.find('table', {'id': 'stats_keeper_dom_cup'})
        if not gk_dom_cup_table:
            gk_dom_cup_table = find_table_in_comments('stats_keeper_dom_cup')
        if gk_dom_cup_table:
            competition_stats = self._merge_goalkeeper_stats(competition_stats, self._parse_goalkeeper_table(gk_dom_cup_table, 'DOMESTIC_CUP'))

        # International cup goalkeeper stats (European competitions from /all_comps/)
        gk_intl_cup_table = soup.find('table', {'id': 'stats_keeper_intl_cup'})
        if not gk_intl_cup_table:
            gk_intl_cup_table = find_table_in_comments('stats_keeper_intl_cup')
        if gk_intl_cup_table:
            competition_stats = self._merge_goalkeeper_stats(competition_stats, self._parse_goalkeeper_table(gk_intl_cup_table, 'EUROPEAN_CUP'))

        # National team goalkeeper stats (from /all_comps/)
        gk_nat_tm_table = soup.find('table', {'id': 'stats_keeper_nat_tm'})
        if not gk_nat_tm_table:
            gk_nat_tm_table = find_table_in_comments('stats_keeper_nat_tm')
        if gk_nat_tm_table:
            competition_stats = self._merge_goalkeeper_stats(competition_stats, self._parse_goalkeeper_table(gk_nat_tm_table, 'NATIONAL_TEAM'))

        # Club competitions (fallback, Europe, cups)
        gk_club_comps_table = soup.find('table', {'id': 'stats_keeper_club_comps'})
        if not gk_club_comps_table:
            gk_club_comps_table = find_table_in_comments('stats_keeper_club_comps')
        if gk_club_comps_table:
            competition_stats = self._merge_goalkeeper_stats(competition_stats, self._parse_goalkeeper_table(gk_club_comps_table, None))

        # International (fallback, national team)
        gk_intl_table = soup.find('table', {'id': 'stats_keeper_intl'})
        if not gk_intl_table:
            gk_intl_table = find_table_in_comments('stats_keeper_intl')
        if gk_intl_table:
            competition_stats = self._merge_goalkeeper_stats(competition_stats, self._parse_goalkeeper_table(gk_intl_table, 'NATIONAL_TEAM'))
        
        return competition_stats

    def _parse_goalkeeper_table(self, table, competition_type: Optional[str]) -> List[Dict]:
        """Parse a goalkeeper stats table (advanced stats)"""
        stats = []
        tbody = table.find('tbody')
        if not tbody:
            return stats
        rows = tbody.find_all('tr')
        for row in rows:
            # Skip header rows only
            if row.get('class') and 'thead' in row.get('class'):
                continue
            debug_cells = {}
            for cell in row.find_all(['th', 'td']):
                stat_name = cell.get('data-stat', 'NO_DATA_STAT')
                debug_cells[stat_name] = cell.get_text(strip=True)
            # Print full debug_cells for diagnostics
            logger.info(f"[GK_ROW_DEBUG] CELLS={debug_cells}")
            stat = {}
            # Season
            season_cell = row.find('th', {'data-stat': 'season'})
            if not season_cell:
                season_cell = row.find('th')
            if season_cell:
                season_text = season_cell.get_text(strip=True)
                season_link = season_cell.find('a')
                if season_link:
                    season_text = season_link.get_text(strip=True)
                stat['season'] = season_text
            # Competition name
            comp_cell = row.find('td', {'data-stat': 'comp_level'})
            if not comp_cell:
                comp_cell = row.find('td', {'data-stat': 'comp_name'})
            if not comp_cell:
                all_tds = row.find_all('td')
                if len(all_tds) >= 2:
                    comp_cell = all_tds[1]
            if comp_cell:
                comp_text = comp_cell.get_text(strip=True)
                comp_link = comp_cell.find('a')
                if comp_link:
                    comp_text = comp_link.get_text(strip=True)
                stat['competition_name'] = comp_text
            
            # Determine competition type
            if competition_type:
                stat['competition_type'] = competition_type
            elif stat.get('competition_name'):
                # If no type provided, infer from competition name
                comp_name = stat['competition_name'].lower()
                # Domestic cups (check first before European)
                domestic_keywords = [
                    'copa del rey', 'copa', 'pokal', 'coupe', 'coppa',
                    'fa cup', 'league cup', 'efl', 'carabao',
                    'dfb-pokal', 'dfl-supercup', 'supercopa', 'supercoppa'
                ]
                # European cups
                european_keywords = ['champions', 'europa', 'uefa', 'conference', 'super cup', 'club world']
                
                if any(keyword in comp_name for keyword in domestic_keywords):
                    stat['competition_type'] = 'DOMESTIC_CUP'
                elif any(keyword in comp_name for keyword in european_keywords):
                    stat['competition_type'] = 'EUROPEAN_CUP'
                else:
                    stat['competition_type'] = 'LEAGUE'
            # Games (FBref uses 'gk_games' for goalkeeper stats)
            games_cell = row.find('td', {'data-stat': 'gk_games'})
            if not games_cell:
                games_cell = row.find('td', {'data-stat': 'games'})
            stat['games'] = self._parse_int(games_cell.get_text(strip=True)) if games_cell else None
            
            # Games starts
            starts_cell = row.find('td', {'data-stat': 'gk_games_starts'})
            if not starts_cell:
                starts_cell = row.find('td', {'data-stat': 'games_starts'})
            stat['games_starts'] = self._parse_int(starts_cell.get_text(strip=True)) if starts_cell else None
            
            # Minutes (FBref uses 'gk_minutes' for goalkeeper stats)
            minutes_cell = row.find('td', {'data-stat': 'gk_minutes'})
            if not minutes_cell:
                minutes_cell = row.find('td', {'data-stat': 'minutes'})
            stat['minutes'] = self._parse_int(minutes_cell.get_text(strip=True)) if minutes_cell else None
            
            # Goals against
            ga_cell = row.find('td', {'data-stat': 'gk_goals_against'})
            if not ga_cell:
                ga_cell = row.find('td', {'data-stat': 'goals_against'})
            stat['goals_against'] = self._parse_int(ga_cell.get_text(strip=True)) if ga_cell else None
            
            # Goals against per 90
            ga90_cell = row.find('td', {'data-stat': 'gk_goals_against_per90'})
            if not ga90_cell:
                ga90_cell = row.find('td', {'data-stat': 'goals_against_per90'})
            stat['ga90'] = self._parse_float(ga90_cell.get_text(strip=True)) if ga90_cell else None
            
            # Shots on target against
            sota_cell = row.find('td', {'data-stat': 'gk_shots_on_target_against'})
            if not sota_cell:
                sota_cell = row.find('td', {'data-stat': 'shots_on_target_against'})
            stat['sota'] = self._parse_int(sota_cell.get_text(strip=True)) if sota_cell else None
            
            # Saves
            saves_cell = row.find('td', {'data-stat': 'gk_saves'})
            if not saves_cell:
                saves_cell = row.find('td', {'data-stat': 'saves'})
            stat['saves'] = self._parse_int(saves_cell.get_text(strip=True)) if saves_cell else None
            
            # Save percentage
            save_pct_cell = row.find('td', {'data-stat': 'gk_save_pct'})
            if not save_pct_cell:
                save_pct_cell = row.find('td', {'data-stat': 'save_pct'})
            stat['save_pct'] = self._parse_float(save_pct_cell.get_text(strip=True)) if save_pct_cell else None
            
            # Wins
            wins_cell = row.find('td', {'data-stat': 'gk_wins'})
            if not wins_cell:
                wins_cell = row.find('td', {'data-stat': 'wins'})
            stat['wins'] = self._parse_int(wins_cell.get_text(strip=True)) if wins_cell else None
            
            # Draws/Ties
            ties_cell = row.find('td', {'data-stat': 'gk_ties'})
            if not ties_cell:
                ties_cell = row.find('td', {'data-stat': 'ties'})
            stat['ties'] = self._parse_int(ties_cell.get_text(strip=True)) if ties_cell else None
            stat['draws'] = stat['ties']  # Alias for ties
            
            # Losses
            losses_cell = row.find('td', {'data-stat': 'gk_losses'})
            if not losses_cell:
                losses_cell = row.find('td', {'data-stat': 'losses'})
            stat['losses'] = self._parse_int(losses_cell.get_text(strip=True)) if losses_cell else None
            
            # Clean sheets
            cs_cell = row.find('td', {'data-stat': 'gk_clean_sheets'})
            if not cs_cell:
                cs_cell = row.find('td', {'data-stat': 'clean_sheets'})
            stat['clean_sheets'] = self._parse_int(cs_cell.get_text(strip=True)) if cs_cell else None
            
            # Clean sheet percentage
            cs_pct_cell = row.find('td', {'data-stat': 'gk_clean_sheets_pct'})
            if not cs_pct_cell:
                cs_pct_cell = row.find('td', {'data-stat': 'clean_sheets_pct'})
            stat['clean_sheets_pct'] = self._parse_float(cs_pct_cell.get_text(strip=True)) if cs_pct_cell else None
            
            # Penalties
            pens_att_cell = row.find('td', {'data-stat': 'gk_pens_att'})
            if not pens_att_cell:
                pens_att_cell = row.find('td', {'data-stat': 'pens_att'})
            stat['pens_att'] = self._parse_int(pens_att_cell.get_text(strip=True)) if pens_att_cell else None
            
            pens_allowed_cell = row.find('td', {'data-stat': 'gk_pens_allowed'})
            if not pens_allowed_cell:
                pens_allowed_cell = row.find('td', {'data-stat': 'pens_allowed'})
            stat['pens_allowed'] = self._parse_int(pens_allowed_cell.get_text(strip=True)) if pens_allowed_cell else None
            
            pens_saved_cell = row.find('td', {'data-stat': 'gk_pens_saved'})
            if not pens_saved_cell:
                pens_saved_cell = row.find('td', {'data-stat': 'pens_saved'})
            stat['pens_saved'] = self._parse_int(pens_saved_cell.get_text(strip=True)) if pens_saved_cell else None
            
            pens_missed_cell = row.find('td', {'data-stat': 'gk_pens_missed'})
            if not pens_missed_cell:
                pens_missed_cell = row.find('td', {'data-stat': 'pens_missed'})
            stat['pens_missed'] = self._parse_int(pens_missed_cell.get_text(strip=True)) if pens_missed_cell else None
            
            # PSxG (post-shot expected goals)
            psxg_cell = row.find('td', {'data-stat': 'gk_psxg'})
            if not psxg_cell:
                psxg_cell = row.find('td', {'data-stat': 'psxg'})
            stat['psxg'] = self._parse_float(psxg_cell.get_text(strip=True)) if psxg_cell else None
            
            # PSxG +/-
            psxg_diff_cell = row.find('td', {'data-stat': 'gk_psxg_plus_minus'})
            if not psxg_diff_cell:
                psxg_diff_cell = row.find('td', {'data-stat': 'psxg_plus_minus'})
            stat['psxg_diff'] = self._parse_float(psxg_diff_cell.get_text(strip=True)) if psxg_diff_cell else None
            # Always append the stat dict, even if some fields are missing
            stats.append(stat)
        return stats

    def _normalize_competition_name(self, name):
        if not name:
            return ''
        # Usuń prefiksy typu '1.', '2.', itp. oraz spacje, zamień na lower-case
        name = name.strip().lower()
        if '.' in name and name[0].isdigit():
            name = name.split('.', 1)[1].strip()
        return name

    def _merge_goalkeeper_stats(self, stats: list, gk_stats: list) -> list:
        """Merge advanced goalkeeper stats into main competition stats by season and normalized competition name 
        IMPORTANT: Preserve minutes from standard table (don't overwrite with GK table which often has None/0)"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[MERGE_DEBUG] gk_stats: {gk_stats}")
        logger.info(f"[MERGE_DEBUG] stats before: {stats}")
        for gk in gk_stats:
            matched = False
            gk_season = gk.get('season')
            gk_comp = self._normalize_competition_name(gk.get('competition_name'))
            for stat in stats:
                stat_season = stat.get('season')
                stat_comp = self._normalize_competition_name(stat.get('competition_name'))
                if stat_season == gk_season and stat_comp == gk_comp:
                    # Preserve minutes from standard table if it exists and is not 0/None
                    existing_minutes = stat.get('minutes')
                    
                    # Merge all goalkeeper stats
                    for k, v in gk.items():
                        stat[k] = v
                    
                    # Restore minutes from standard table if GK table had None/0 and standard had valid data
                    if existing_minutes and (not stat.get('minutes') or stat.get('minutes') == 0):
                        stat['minutes'] = existing_minutes
                        logger.info(f"✅ Preserved minutes={existing_minutes} from standard table for {gk_season} {gk.get('competition_name')}")
                    
                    matched = True
                    break
            if not matched:
                stats.append(gk)
        logger.info(f"[MERGE_DEBUG] stats after: {stats}")
        return stats
    
    def _parse_expected_table(self, table) -> List[Dict]:
        """Parse Expected stats table (xG, npxG, xAG) from FBref"""
        expected_stats = []
        
        tbody = table.find('tbody')
        if not tbody:
            return expected_stats
        
        rows = tbody.find_all('tr')
        
        for row in rows:
            # Skip header rows
            if row.get('class') and 'thead' in row.get('class'):
                continue
            
            stat = {}
            
            # Season
            season_cell = row.find('th', {'data-stat': 'season'})
            if not season_cell:
                season_cell = row.find('th')
            if season_cell:
                season_text = season_cell.get_text(strip=True)
                season_link = season_cell.find('a')
                if season_link:
                    season_text = season_link.get_text(strip=True)
                stat['season'] = season_text
            
            # Competition name
            comp_cell = row.find('td', {'data-stat': 'comp_level'})
            if not comp_cell:
                comp_cell = row.find('td', {'data-stat': 'comp_name'})
            if not comp_cell:
                all_tds = row.find_all('td')
                if len(all_tds) >= 2:
                    comp_cell = all_tds[1]
            if comp_cell:
                comp_text = comp_cell.get_text(strip=True)
                comp_link = comp_cell.find('a')
                if comp_link:
                    comp_text = comp_link.get_text(strip=True)
                stat['competition_name'] = comp_text
            
            # xG
            xg_cell = row.find('td', {'data-stat': 'xg'})
            if xg_cell:
                stat['xg'] = self._parse_float(xg_cell.get_text(strip=True))
            
            # npxG (non-penalty xG)
            npxg_cell = row.find('td', {'data-stat': 'npxg'})
            if npxg_cell:
                stat['npxg'] = self._parse_float(npxg_cell.get_text(strip=True))
            
            # xAG (xG assisted / xA)
            xa_cell = row.find('td', {'data-stat': 'xg_assist'})
            if not xa_cell:
                xa_cell = row.find('td', {'data-stat': 'xa'})
            if xa_cell:
                stat['xa'] = self._parse_float(xa_cell.get_text(strip=True))
            
            # Only add if we have season and competition
            if stat.get('season') and stat.get('competition_name'):
                expected_stats.append(stat)
        
        return expected_stats
    
    def _parse_shooting_table(self, table) -> List[Dict]:
        """Parse Shooting stats table (xG, npxG from shooting table) from FBref"""
        shooting_stats = []
        
        tbody = table.find('tbody')
        if not tbody:
            return shooting_stats
        
        rows = tbody.find_all('tr')
        
        for row in rows:
            # Skip header rows
            if row.get('class') and 'thead' in row.get('class'):
                continue
            
            stat = {}
            
            # Season
            season_cell = row.find('th', {'data-stat': 'season'})
            if not season_cell:
                season_cell = row.find('th')
            if season_cell:
                season_text = season_cell.get_text(strip=True)
                season_link = season_cell.find('a')
                if season_link:
                    season_text = season_link.get_text(strip=True)
                stat['season'] = season_text
            
            # Competition name
            comp_cell = row.find('td', {'data-stat': 'comp_level'})
            if not comp_cell:
                comp_cell = row.find('td', {'data-stat': 'comp_name'})
            if not comp_cell:
                all_tds = row.find_all('td')
                if len(all_tds) >= 2:
                    comp_cell = all_tds[1]
            if comp_cell:
                comp_text = comp_cell.get_text(strip=True)
                comp_link = comp_cell.find('a')
                if comp_link:
                    comp_text = comp_link.get_text(strip=True)
                stat['competition_name'] = comp_text
            
            # xG (from shooting table)
            xg_cell = row.find('td', {'data-stat': 'xg'})
            if xg_cell:
                xg_val = self._parse_float(xg_cell.get_text(strip=True))
                if xg_val is not None and xg_val > 0:  # Only use if not empty/zero
                    stat['xg'] = xg_val
            
            # npxG (non-penalty xG from shooting table)
            npxg_cell = row.find('td', {'data-stat': 'npxg'})
            if npxg_cell:
                npxg_val = self._parse_float(npxg_cell.get_text(strip=True))
                if npxg_val is not None and npxg_val > 0:  # Only use if not empty/zero
                    stat['npxg'] = npxg_val
            
            # Note: shooting table doesn't have xA, so we skip it
            
            # Only add if we have season, competition, and at least one xG value
            if stat.get('season') and stat.get('competition_name') and (stat.get('xg') is not None or stat.get('npxg') is not None):
                shooting_stats.append(stat)
        
        return shooting_stats
    
    def _merge_expected_stats(self, stats: List[Dict], expected_stats: List[Dict]) -> List[Dict]:
        """Merge Expected stats (xG, npxG, xAG) into main stats by season and competition name"""
        for expected in expected_stats:
            expected_season = expected.get('season')
            expected_comp = self._normalize_competition_name(expected.get('competition_name'))
            
            matched = False
            for stat in stats:
                stat_season = stat.get('season')
                stat_comp = self._normalize_competition_name(stat.get('competition_name'))
                
                if stat_season == expected_season and stat_comp == expected_comp:
                    # Merge xG data (overwrite if exists and is not None/empty)
                    if 'xg' in expected and expected['xg'] is not None:
                        stat['xg'] = expected['xg']
                    if 'npxg' in expected and expected['npxg'] is not None:
                        stat['npxg'] = expected['npxg']
                    if 'xa' in expected and expected['xa'] is not None:
                        stat['xa'] = expected['xa']
                    
                    matched = True
                    logger.info(f"✅ Merged Expected stats for {stat_season} {stat.get('competition_name')}: xG={expected.get('xg')}, npxG={expected.get('npxg')}, xAG={expected.get('xa')}")
                    break
            
            if not matched:
                logger.debug(f"⚠️ Could not match Expected stats for {expected_season} {expected.get('competition_name')}")
        
        return stats
    
    def _parse_stats_table(self, table, competition_type: Optional[str]) -> List[Dict]:
        """Parse a statistics table"""
        stats = []
        
        tbody = table.find('tbody')
        if not tbody:
            return stats
        
        rows = tbody.find_all('tr')
        
        for row in rows:
            # Skip header rows
            if row.get('class') and 'thead' in row.get('class'):
                continue
            
            stat = {}
            
            # Season - try multiple methods
            season_cell = row.find('th', {'data-stat': 'season'})
            if not season_cell:
                season_cell = row.find('th')
            if season_cell:
                season_text = season_cell.get_text(strip=True)
                # Get link text if available (more reliable)
                season_link = season_cell.find('a')
                if season_link:
                    season_text = season_link.get_text(strip=True)
                stat['season'] = season_text
            
            # Competition name - try multiple methods
            comp_cell = row.find('td', {'data-stat': 'comp_level'})
            if not comp_cell:
                comp_cell = row.find('td', {'data-stat': 'comp_name'})
            if not comp_cell:
                # Try finding by position (usually 2nd or 3rd td)
                all_tds = row.find_all('td')
                if len(all_tds) >= 2:
                    comp_cell = all_tds[1]
            if comp_cell:
                comp_text = comp_cell.get_text(strip=True)
                # Get link text if available
                comp_link = comp_cell.find('a')
                if comp_link:
                    comp_text = comp_link.get_text(strip=True)
                stat['competition_name'] = comp_text
            
            if competition_type:
                stat['competition_type'] = competition_type
            
            # Games
            games_cell = row.find('td', {'data-stat': 'games'})
            if games_cell:
                stat['games'] = self._parse_int(games_cell.get_text(strip=True))
            
            # Games started
            games_starts_cell = row.find('td', {'data-stat': 'games_starts'})
            if games_starts_cell:
                stat['games_starts'] = self._parse_int(games_starts_cell.get_text(strip=True))
            
            # Minutes
            minutes_cell = row.find('td', {'data-stat': 'minutes'})
            if minutes_cell:
                stat['minutes'] = self._parse_int(minutes_cell.get_text(strip=True))
            
            # Goals
            goals_cell = row.find('td', {'data-stat': 'goals'})
            if goals_cell:
                stat['goals'] = self._parse_int(goals_cell.get_text(strip=True))
            
            # Assists
            assists_cell = row.find('td', {'data-stat': 'assists'})
            if assists_cell:
                stat['assists'] = self._parse_int(assists_cell.get_text(strip=True))
            
            # xG
            xg_cell = row.find('td', {'data-stat': 'xg'})
            if xg_cell:
                stat['xg'] = self._parse_float(xg_cell.get_text(strip=True))
            
            # npxG (non-penalty xG)
            npxg_cell = row.find('td', {'data-stat': 'npxg'})
            if npxg_cell:
                stat['npxg'] = self._parse_float(npxg_cell.get_text(strip=True))
            
            # xA
            xa_cell = row.find('td', {'data-stat': 'xg_assist'})
            if xa_cell:
                stat['xa'] = self._parse_float(xa_cell.get_text(strip=True))
            
            # Penalty goals
            pen_goals_cell = row.find('td', {'data-stat': 'pens_made'})
            if pen_goals_cell:
                stat['penalty_goals'] = self._parse_int(pen_goals_cell.get_text(strip=True))
            
            # Shots
            shots_cell = row.find('td', {'data-stat': 'shots'})
            if shots_cell:
                stat['shots'] = self._parse_int(shots_cell.get_text(strip=True))
            
            # Shots on target
            sot_cell = row.find('td', {'data-stat': 'shots_on_target'})
            if sot_cell:
                stat['shots_on_target'] = self._parse_int(sot_cell.get_text(strip=True))
            
            # Yellow cards
            yellow_cell = row.find('td', {'data-stat': 'cards_yellow'})
            if yellow_cell:
                stat['yellow_cards'] = self._parse_int(yellow_cell.get_text(strip=True))
            
            # Red cards
            red_cell = row.find('td', {'data-stat': 'cards_red'})
            if red_cell:
                stat['red_cards'] = self._parse_int(red_cell.get_text(strip=True))
            
            # Only add if we have at least games data
            if stat.get('games') is not None:
                stats.append(stat)
        
        return stats
    
    def _parse_int(self, value: str) -> Optional[int]:
        """Parse integer value"""
        try:
            return int(value) if value and value.strip() else None
        except:
            return None
    
    def _parse_float(self, value: str) -> Optional[float]:
        """Parse float value"""
        try:
            return float(value) if value and value.strip() else None
        except:
            return None
    
    async def get_player_match_logs(self, player_id: str, player_name: str = "", season: str = "2025-2026") -> List[Dict]:
        """
        Get match-by-match logs for a player in a specific season
        
        Args:
            player_id: FBref player ID
            player_name: Player name for URL
            season: Season in format YYYY-YYYY (e.g., "2025-2026")
        
        Returns:
            List of match dictionaries with detailed stats
        """
        await self._wait_for_rate_limit()
        
        name_slug = player_name.replace(' ', '-') if player_name else 'player'
        # FBref uses different format for season in URL
        season_slug = season.replace('-', '-')  # 2025-2026 stays as is
        match_logs_url = f"{self.BASE_URL}/en/players/{player_id}/matchlogs/{season_slug}/{name_slug}-Match-Logs"
        
        logger.info(f"📋 Fetching match logs: {match_logs_url}")
        
        page = await self._create_page()
        
        try:
            await page.goto(match_logs_url, wait_until="networkidle", timeout=30000)
            
            # Get page content
            content = await page.content()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find match logs table
            match_logs = []
            
            # Try to find the matchlogs table - check multiple possible IDs
            # Common IDs: matchlogs_all, matchlogs_for, matchlog_XXXX
            possible_table_ids = ['matchlogs_all', 'matchlogs_for', 'matchlog']
            
            table = None
            for table_id in possible_table_ids:
                table = soup.find('table', {'id': lambda x: x and table_id in x.lower()})
                if table:
                    logger.info(f"✅ Found match logs table: {table.get('id')}")
                    break
            
            # If still not found, try in comments
            if not table:
                for comment in soup.find_all(string=lambda text: isinstance(text, str) and 'matchlog' in text.lower()):
                    if '<table' in str(comment):
                        comment_soup = BeautifulSoup(str(comment), 'html.parser')
                        table = comment_soup.find('table')
                        if table and table.get('id') and 'matchlog' in table.get('id').lower():
                            logger.info(f"✅ Found match logs table in comment: {table.get('id')}")
                            break
            
            if table:
                match_logs = self._parse_match_logs_table(table)
            
            logger.info(f"✅ Found {len(match_logs)} match logs")
            return match_logs
            
        except Exception as e:
            logger.error(f"Error fetching match logs: {e}", exc_info=True)
            return []
        finally:
            await page.close()
    
    def _parse_match_logs_table(self, table) -> List[Dict]:
        """Parse match logs table"""
        matches = []
        
        tbody = table.find('tbody')
        if not tbody:
            return matches
        
        rows = tbody.find_all('tr')
        
        for row in rows:
            # Skip header rows
            if row.get('class') and 'thead' in row.get('class'):
                continue
            
            match = {}
            
            # Date (can be in th or td)
            date_cell = row.find('th', {'data-stat': 'date'})
            if not date_cell:
                date_cell = row.find('td', {'data-stat': 'date'})
            if date_cell:
                match['match_date'] = date_cell.get_text(strip=True)
            
            # Competition
            comp_cell = row.find('td', {'data-stat': 'comp'})
            if comp_cell:
                match['competition'] = comp_cell.get_text(strip=True)
            
            # Round
            round_cell = row.find('td', {'data-stat': 'round'})
            if round_cell:
                match['round'] = round_cell.get_text(strip=True)
            
            # Venue (Home/Away)
            venue_cell = row.find('td', {'data-stat': 'venue'})
            if venue_cell:
                match['venue'] = venue_cell.get_text(strip=True)
            
            # Opponent
            opponent_cell = row.find('td', {'data-stat': 'opponent'})
            if opponent_cell:
                match['opponent'] = opponent_cell.get_text(strip=True)
            
            # Result
            result_cell = row.find('td', {'data-stat': 'result'})
            if result_cell:
                match['result'] = result_cell.get_text(strip=True)
            
            # Minutes played (handle both 'gk_minutes' and 'minutes')
            minutes_cell = row.find('td', {'data-stat': 'gk_minutes'})
            if not minutes_cell:
                minutes_cell = row.find('td', {'data-stat': 'minutes'})
            if minutes_cell:
                match['minutes_played'] = self._parse_int(minutes_cell.get_text(strip=True))
            
            # Goals
            goals_cell = row.find('td', {'data-stat': 'goals'})
            if goals_cell:
                match['goals'] = self._parse_int(goals_cell.get_text(strip=True))
            
            # Assists
            assists_cell = row.find('td', {'data-stat': 'assists'})
            if assists_cell:
                match['assists'] = self._parse_int(assists_cell.get_text(strip=True))
            
            # xG
            xg_cell = row.find('td', {'data-stat': 'xg'})
            if xg_cell:
                match['xg'] = self._parse_float(xg_cell.get_text(strip=True))
            
            # xA
            xa_cell = row.find('td', {'data-stat': 'xg_assist'})
            if xa_cell:
                match['xa'] = self._parse_float(xa_cell.get_text(strip=True))
            
            # Shots
            shots_cell = row.find('td', {'data-stat': 'shots'})
            if shots_cell:
                match['shots'] = self._parse_int(shots_cell.get_text(strip=True))
            
            # Shots on target
            sot_cell = row.find('td', {'data-stat': 'shots_on_target'})
            if sot_cell:
                match['shots_on_target'] = self._parse_int(sot_cell.get_text(strip=True))
            
            # Yellow cards
            yellow_cell = row.find('td', {'data-stat': 'cards_yellow'})
            if yellow_cell:
                match['yellow_cards'] = self._parse_int(yellow_cell.get_text(strip=True))
            
            # Red cards
            red_cell = row.find('td', {'data-stat': 'cards_red'})
            if red_cell:
                match['red_cards'] = self._parse_int(red_cell.get_text(strip=True))
            
            # Touches
            touches_cell = row.find('td', {'data-stat': 'touches'})
            if touches_cell:
                match['touches'] = self._parse_int(touches_cell.get_text(strip=True))
            
            # Passes completed
            passes_completed_cell = row.find('td', {'data-stat': 'passes_completed'})
            if passes_completed_cell:
                match['passes_completed'] = self._parse_int(passes_completed_cell.get_text(strip=True))
            
            # Passes attempted
            passes_cell = row.find('td', {'data-stat': 'passes'})
            if passes_cell:
                match['passes_attempted'] = self._parse_int(passes_cell.get_text(strip=True))
            
            # Only add if we have at least a date
            if match.get('match_date'):
                matches.append(match)
        
        return matches


# Singleton instance
_playwright_scraper = None


async def get_playwright_scraper(headless: bool = True) -> FBrefPlaywrightScraper:
    """Get or create the Playwright scraper instance"""
    global _playwright_scraper
    
    if _playwright_scraper is None:
        _playwright_scraper = FBrefPlaywrightScraper(headless=headless)
        await _playwright_scraper.start()
    
    return _playwright_scraper


async def close_playwright_scraper():
    """Close the global Playwright scraper"""
    global _playwright_scraper
    
    if _playwright_scraper:
        await _playwright_scraper.close()
        _playwright_scraper = None
