"""
Common utility functions.

Data normalization, character mapping, and competition type detection.
"""
import unicodedata


# Polish character mapping for database search
# Database stores ASCII-only names (e.g., "Ziolkowski")
# but users type with Polish characters (e.g., "Ziółkowski")
POLISH_TO_ASCII = {
    'ą': 'a', 'Ą': 'A',
    'ć': 'c', 'Ć': 'C',
    'ę': 'e', 'Ę': 'E',
    'ł': 'l', 'Ł': 'L',
    'ń': 'n', 'Ń': 'N',
    'ó': 'o', 'Ó': 'O',
    'ś': 's', 'Ś': 'S',
    'ź': 'z', 'Ź': 'Z',
    'ż': 'z', 'Ż': 'Z',
}


def normalize_search(name: str) -> str:
    """
    Normalize Polish characters for database search.

    Database stores names without Polish characters (e.g., "Ziolkowski")
    but users type with Polish characters (e.g., "Ziółkowski").

    Args:
        name: Name to normalize (may contain Polish characters)

    Returns:
        Name with Polish characters converted to ASCII equivalents
    """
    result = []
    for char in name:
        # Use manual mapping for Polish characters
        if char in POLISH_TO_ASCII:
            result.append(POLISH_TO_ASCII[char])
        else:
            result.append(char)
    return ''.join(result)


def get_competition_type(competition_name: str) -> str:
    """
    Determine competition type from competition name.
    Maps name to one of: LEAGUE, DOMESTIC_CUP, EUROPEAN_CUP, NATIONAL_TEAM.
    """
    if not competition_name:
        return "LEAGUE"

    comp_lower = competition_name.lower()

    # 1. National team (CHECK FIRST - before club competitions keywords)
    if any(keyword in comp_lower for keyword in [
        'national team', 'reprezentacja', 'international',
        'friendlies', 'wcq', 'world cup', 'uefa euro', 'euro qualifying',
        'uefa nations league', 'copa america', 'concacaf nations league'
    ]):
        return "NATIONAL_TEAM"

    # 2. Domestic cups (CHECK SECOND)
    if any(keyword in comp_lower for keyword in [
        'copa del rey', 'copa', 'pokal', 'coupe', 'coppa',
        'fa cup', 'league cup', 'efl', 'carabao',
        'dfb-pokal', 'dfl-supercup', 'supercopa', 'supercoppa',
        'u.s. open cup', 'puchar', 'krajowy puchar', 'leagues cup'
    ]):
        return "DOMESTIC_CUP"

    # 3. European / International club competitions
    if any(keyword in comp_lower for keyword in [
        'champions league', 'europa league', 'conference league',
        'uefa', 'champions lg', 'europa lg', 'conf lg', 'ucl', 'uel', 'uecl',
        'concacaf champions', 'libertadores', 'club world cup'
    ]):
        return "EUROPEAN_CUP"

    # Default to league
    return "LEAGUE"
