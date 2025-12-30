import streamlit as st
import random
import colorsys
import math

# ---------------------------------------------------------
# 1. CONSTANTS & PREDEFINED COLORS (The "First 32")
# ---------------------------------------------------------

COMMON_COLORS = [
    "#FF0000", "#0000FF", "#00FF00", "#FFFF00", "#800080", "#FFA500", "#00FFFF", "#FF00FF",
    # Red, Blue, Green, Yellow, Purple, Orange, Cyan, Magenta
    "#000000", "#FFFFFF", "#808080", "#A52A2A", "#FFC0CB", "#008080", "#E6E6FA", "#40E0D0",
    # Black, White, Gray, Brown, Pink, Teal, Lavender, Turquoise
    "#800000", "#000080", "#808000", "#C0C0C0", "#FFD700", "#4B0082", "#FA8072", "#98FB98",
    # Maroon, Navy, Olive, Silver, Gold, Indigo, Salmon, PaleGreen
    "#DC143C", "#00BFFF", "#B22222", "#FF7F50", "#2E8B57", "#DDA0DD", "#F0E68C", "#708090"
    # Crimson, DeepSky, FireBrick, Coral, SeaGreen, Plum, Khaki, SlateGray
]


# ---------------------------------------------------------
# 2. HELPER FUNCTIONS
# ---------------------------------------------------------

def hex_to_rgb(hex_code):
    """Converts #RRGGBB to a tuple (r, g, b) where values are 0-1."""
    hex_code = hex_code.lstrip('#')
    return tuple(int(hex_code[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def get_hsv(hex_code):
    """Converts Hex to HSV tuple."""
    rgb = hex_to_rgb(hex_code)
    return colorsys.rgb_to_hsv(rgb[0], rgb[1], rgb[2])


def color_distance(hex1, hex2):
    """Calculates Euclidean distance between two colors in RGB space."""
    r1, g1, b1 = hex_to_rgb(hex1)
    r2, g2, b2 = hex_to_rgb(hex2)
    return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)


def generate_distinct_color(existing_hexes):
    """
    Generates a random color that is not too similar to any color in the existing list.
    Uses an adaptive threshold.
    """
    threshold = 0.25
    max_attempts = 50
    attempts = 0

    while True:
        candidate = "#{:06x}".format(random.randint(0, 0xFFFFFF))

        is_distinct = True
        for existing in existing_hexes:
            if color_distance(candidate, existing) < threshold:
                is_distinct = False
                break

        if is_distinct:
            return candidate

        attempts += 1
        if attempts > max_attempts:
            threshold *= 0.90
            attempts = 0


def chunk_list(data, num_chunks):
    """Splits a list into N chunks of equal size (+-1)."""
    k, m = divmod(len(data), num_chunks)
    return [data[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(num_chunks)]


# ---------------------------------------------------------
# 3. SORTING ALGORITHM
# ---------------------------------------------------------

def sort_players_perceptually(players):
    """Sorts players: Grayscale/Blacks first, then Colors by Hue."""

    def sort_key(player):
        h, s, v = get_hsv(player['hex'])

        is_grayscale = s < 0.15 or v < 0.15

        if is_grayscale:
            return (0, v, 0)
        else:
            return (1, h, v)

    return sorted(players, key=sort_key)


# ---------------------------------------------------------
# 4. UI RENDERING
# ---------------------------------------------------------

def render_player_grid(player_list):
    """Renders a responsive grid of colored boxes."""
    if not player_list:
        return

    items_html = ""
    for p in player_list:
        rgb = hex_to_rgb(p['hex'])
        brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
        text_color = "black" if brightness > 0.6 else "white"

        box_style = f"background-color:{p['hex']};width:50px;height:50px;border-radius:4px;display:flex;align-items:center;justify-content:center;color:{text_color};font-family:monospace;font-size:10px;box-shadow:1px 1px 2px rgba(0,0,0,0.2);"
        items_html += f'<div style="{box_style}" title="{p["id"]}"><strong>{p["id"]}</strong></div>'

    container_style = "display:flex;flex-wrap:wrap;gap:4px;margin-bottom:10px;"
    st.markdown(f'<div style="{container_style}">{items_html}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------
# 5. MAIN APP LOGIC
# ---------------------------------------------------------

st.set_page_config(page_title="Team Auto-Balancer", layout="wide")
st.title("⚔️ Smart Team Balancer")
st.markdown("Groups players into teams based on color similarity.")

# --- SIDEBAR ---
st.sidebar.header("Configuration")

total_players = st.sidebar.slider("Total Players", min_value=2, max_value=100, value=32)
num_teams = st.sidebar.slider("Number of Teams", min_value=2, max_value=20, value=2)

regenerate = st.sidebar.button("Regenerate / Reset")
# NEW TEXT ADDED HERE
st.sidebar.caption(
    "🔒 **Note:** The first 32 colors are locked to a standard palette. This button only randomizes players 33+.")


# --- STATE MANAGEMENT ---

def initialize_players(n):
    """Creates N players using predefined list first, then distinct randoms."""
    new_players = []

    # Use fixed colors for as many as we can
    limit = min(n, len(COMMON_COLORS))
    for i in range(limit):
        new_players.append({"id": str(i + 1), "hex": COMMON_COLORS[i]})

    # If we need more, generate distinct randoms
    if n > limit:
        current_hexes = [p['hex'] for p in new_players]
        for i in range(limit, n):
            new_hex = generate_distinct_color(current_hexes)
            new_players.append({"id": str(i + 1), "hex": new_hex})
            current_hexes.append(new_hex)

    return new_players


# 1. Handle Initialization or Regenerate Click
if 'players' not in st.session_state or regenerate:
    st.session_state.players = initialize_players(total_players)

# 2. Handle Slider Movement (Add/Remove without full reset)
elif len(st.session_state.players) != total_players:
    current_list = st.session_state.players
    current_count = len(current_list)

    if total_players < current_count:
        # User reduced slider: Trim
        st.session_state.players = current_list[:total_players]
    else:
        # User increased slider: Add
        current_hexes = [p['hex'] for p in current_list]
        for i in range(current_count, total_players):
            # Check if we are filling back into the "Common" range
            if i < len(COMMON_COLORS):
                new_hex = COMMON_COLORS[i]
            else:
                new_hex = generate_distinct_color(current_hexes)

            st.session_state.players.append({"id": str(i + 1), "hex": new_hex})
            current_hexes.append(new_hex)

players = st.session_state.players

# --- PROCESSING ---

sorted_players = sort_players_perceptually(players)
teams_list = chunk_list(sorted_players, num_teams)

# --- VISUALIZATION ---

col_left, col_right = st.columns([1, 2])

with col_left:
    st.subheader(f"Player Pool ({total_players})")
    render_player_grid(players)

with col_right:
    st.subheader(f"Formed Teams ({num_teams})")

    for i, team_members in enumerate(teams_list):
        count = len(team_members)
        with st.container():
            st.markdown(f"**Team {i + 1}** <span style='color:gray;font-size:0.8em'>({count} players)</span>",
                        unsafe_allow_html=True)
            render_player_grid(team_members)
            st.markdown("---")