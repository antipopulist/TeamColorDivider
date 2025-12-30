import streamlit as st
import random
import colorsys
import math
import time

# ---------------------------------------------------------
# 1. SETUP & SCI-FI STYLING
# ---------------------------------------------------------

st.set_page_config(page_title="BAR Commander Sim", layout="wide", page_icon="⚙️")

st.markdown("""
<style>
    /* Dark Sci-Fi Background */
    .stApp {
        background-color: #050505;
        color: #e0e0e0;
    }

    /* Animations */
    @keyframes shake {
        0% { transform: translate(1px, 1px) rotate(0deg); }
        10% { transform: translate(-1px, -2px) rotate(-1deg); }
        20% { transform: translate(-3px, 0px) rotate(1deg); }
        30% { transform: translate(3px, 2px) rotate(0deg); }
        40% { transform: translate(1px, -1px) rotate(1deg); }
        50% { transform: translate(-1px, 2px) rotate(-1deg); }
        60% { transform: translate(-3px, 1px) rotate(0deg); }
        100% { transform: translate(0px, 0px) rotate(0deg); }
    }

    @keyframes blast {
        0% { transform: scale(1); box-shadow: 0 0 0 red; opacity: 1;}
        50% { transform: scale(1.5); box-shadow: 0 0 50px red; opacity: 0.5;}
        100% { transform: scale(0); opacity: 0;}
    }

    .shake-box { animation: shake 0.4s; border: 2px solid #ff4444 !important; }
    .blast-box { animation: blast 0.6s forwards; background-color: white !important; }

    .attacker-box {
        border: 2px solid #00ffff !important;
        transform: scale(1.1);
        z-index: 10;
        box-shadow: 0 0 15px #00ffff;
    }

    /* Resource Bars */
    .bar-container {
        width: 100%; height: 4px; background-color: #333;
        margin-top: 2px; position: relative;
    }
    .hp-fill { height: 100%; background-color: #00ff00; transition: width 0.2s; }
    .energy-fill { height: 100%; background-color: #ffff00; transition: width 0.2s; }

    /* Terminal Log */
    .battle-log {
        background-color: #0a0a0a;
        border: 1px solid #333;
        border-left: 4px solid #00ffff;
        font-family: 'Consolas', 'Courier New', monospace;
        padding: 15px;
        height: 200px;
        overflow-y: auto;
        font-size: 11px;
        color: #cccccc;
        display: flex; flex-direction: column-reverse;
    }
    .log-dgun { color: #ffff00; font-weight: bold; text-shadow: 0 0 5px #ffff00; }
    .log-kill { color: #ff4444; font-weight: bold; }

    /* Faction Badges */
    .faction-label {
        font-size: 10px; text-transform: uppercase; letter-spacing: 1px;
        margin-bottom: 5px; color: #888;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. CONSTANTS & DATA
# ---------------------------------------------------------

COMMON_COLORS = [
    "#FF0000", "#0000FF", "#00FF00", "#FFFF00", "#800080", "#FFA500", "#00FFFF", "#FF00FF",
    "#FFFFFF", "#808080", "#A52A2A", "#FFC0CB", "#008080", "#E6E6FA", "#40E0D0",
    "#800000", "#000080", "#808000", "#C0C0C0", "#FFD700", "#4B0082", "#FA8072", "#98FB98",
    "#DC143C", "#00BFFF", "#B22222", "#FF7F50", "#2E8B57", "#DDA0DD", "#F0E68C", "#708090"
]

# UPDATED: Added Legion
FACTIONS = ["Armada", "Cortex", "Legion"]


# ---------------------------------------------------------
# 3. HELPER FUNCTIONS
# ---------------------------------------------------------

def hex_to_rgb(hex_code):
    hex_code = hex_code.lstrip('#')
    return tuple(int(hex_code[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def get_hsv(hex_code):
    rgb = hex_to_rgb(hex_code)
    return colorsys.rgb_to_hsv(rgb[0], rgb[1], rgb[2])


def color_distance(hex1, hex2):
    r1, g1, b1 = hex_to_rgb(hex1)
    r2, g2, b2 = hex_to_rgb(hex2)
    return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)


def generate_distinct_color(existing_hexes):
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
        if is_distinct: return candidate
        attempts += 1
        if attempts > max_attempts:
            threshold *= 0.90
            attempts = 0


def chunk_list(data, num_chunks):
    k, m = divmod(len(data), num_chunks)
    return [data[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(num_chunks)]


def sort_players_perceptually(players):
    def sort_key(player):
        h, s, v = get_hsv(player['hex'])
        is_grayscale = s < 0.15 or v < 0.15
        if is_grayscale:
            return (0, v, 0)
        else:
            return (1, h, v)

    return sorted(players, key=sort_key)


# ---------------------------------------------------------
# 4. RENDERER
# ---------------------------------------------------------

def render_commander_box(p, hp, energy, is_alive, event_type=None, show_hud=True):
    """
    Renders a 'Commander' unit box.
    """
    pid = p['id']
    hex_c = p['hex']
    faction = p['faction']

    # Text Contrast
    rgb = hex_to_rgb(hex_c)
    brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
    text_color = "black" if brightness > 0.6 else "white"

    # Animation Class
    extra_class = ""
    if is_alive:
        if event_type == "hit":
            extra_class = "shake-box"
        elif event_type == "dgun":
            extra_class = "attacker-box"  # DGUN uses attacker style
        elif event_type == "attack":
            extra_class = "attacker-box"
    elif event_type == "die":
        extra_class = "blast-box"  # Comblast effect

    opacity = "1.0" if is_alive else "0.15"
    content = f"<strong>{pid}</strong>"

    # If dead, show skull
    if not is_alive and event_type != "die":
        content = "💀"

    # HUD (Bars)
    hud_html = ""
    if is_alive and show_hud:
        # Structure (HP)
        hp_pct = max(0, hp)
        # Energy (Yellow)
        en_pct = max(0, energy)

        hud_html = f"""
        <div class="bar-container" title="Structure: {hp}%">
            <div class="hp-fill" style="width:{hp_pct}%;"></div>
        </div>
        <div class="bar-container" title="Energy: {energy}%">
            <div class="energy-fill" style="width:{en_pct}%;"></div>
        </div>
        """

    # Shape style based on Faction
    if faction == "Cortex":
        radius = "0px"  # Square
    elif faction == "Legion":
        radius = "50%"  # Circle
    else:
        radius = "8px"  # Armada (Rounded)

    style = (
        f"background-color:{hex_c}; width:60px; height:60px; "
        f"border-radius:{radius}; display:flex; flex-direction:column; "
        f"align-items:center; justify-content:center; "
        f"color:{text_color}; font-family:monospace; font-size:10px; "
        f"box-shadow:0 0 5px rgba(0,0,0,0.5); opacity:{opacity}; "
        f"position:relative; margin:5px; border: 1px solid rgba(255,255,255,0.2);"
    )

    return f'<div class="{extra_class}" style="{style}" title="{faction} Commander {pid}">{content}{hud_html}</div>'


# ---------------------------------------------------------
# 5. MAIN APP LOGIC
# ---------------------------------------------------------

st.title("⚙️ BAR Commander Simulator")
st.markdown("Group Commanders by team color and simulate **Beyond All Reason** battles.")

# --- CONFIG ---
st.sidebar.header("Lobby Settings")
total_players = st.sidebar.slider("Commander Count", 2, 100, 32)
num_teams = st.sidebar.slider("Team Count", 2, 10, 2)
sim_speed = st.sidebar.slider("Tick Rate (s)", 0.05, 1.0, 0.1)
regenerate = st.sidebar.button("Re-Roll Commanders")
st.sidebar.caption("First 32 colors are standard palette. 33+ are procedurally generated.")


# --- STATE MANAGEMENT ---
def initialize_commanders(n):
    new_coms = []
    limit = min(n, len(COMMON_COLORS))
    for i in range(limit):
        # Randomly assign faction from updated list (Armada, Cortex, Legion)
        f = random.choice(FACTIONS)
        new_coms.append({"id": str(i + 1), "hex": COMMON_COLORS[i], "faction": f})

    if n > limit:
        current_hexes = [p['hex'] for p in new_coms]
        for i in range(limit, n):
            new_hex = generate_distinct_color(current_hexes)
            f = random.choice(FACTIONS)
            new_coms.append({"id": str(i + 1), "hex": new_hex, "faction": f})
            current_hexes.append(new_hex)
    return new_coms


if 'players' not in st.session_state or regenerate:
    st.session_state.players = initialize_commanders(total_players)
elif len(st.session_state.players) != total_players:
    st.session_state.players = initialize_commanders(total_players)

players = st.session_state.players
sorted_players = sort_players_perceptually(players)
teams_list = chunk_list(sorted_players, num_teams)

# --- TABS ---
tab1, tab2 = st.tabs(["🏭 Lobby & Groups", "⚔️ Battle Simulation"])

with tab1:
    col_l, col_r = st.columns([1, 2])
    with col_l:
        st.subheader("Commander Pool")
        html = "<div style='display:flex;flex-wrap:wrap;'>"
        for p in players: html += render_commander_box(p, 100, 100, True, show_hud=False)
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
    with col_r:
        st.subheader("Team Assignments")
        for i, tm in enumerate(teams_list):
            # REMOVED: Team Alignment Calculation. Just showing Team ID.
            st.markdown(f"**Team {i + 1}**")
            html = "<div style='display:flex;flex-wrap:wrap;'>"
            for p in tm: html += render_commander_box(p, 100, 100, True, show_hud=False)
            html += "</div>"
            st.markdown(html, unsafe_allow_html=True)

with tab2:
    start_battle = st.button("🔴 INITIALIZE COMBAT", use_container_width=True)

    log_placeholder = st.empty()
    arena_placeholder = st.empty()

    if start_battle:
        # Battle State
        sim_state = {p['id']: {'hp': 100, 'en': 50} for p in players}
        p_team_map = {p['id']: i for i, tm in enumerate(teams_list) for p in tm}

        battle_active = True
        tick = 0
        logs = []

        while battle_active:
            tick += 1
            alive_ids = [pid for pid, s in sim_state.items() if s['hp'] > 0]
            alive_teams = set(p_team_map[pid] for pid in alive_ids)

            active_attacker = None
            active_victim = None
            event_type = None

            if len(alive_teams) <= 1:
                battle_active = False
                winner_idx = list(alive_teams)[0] if alive_teams else -1
                msg = f"GAME OVER. TEAM {winner_idx + 1} VICTORY." if winner_idx != -1 else "DRAW. MUTUAL ANNIHILATION."
                logs.append(f"<span style='color:#00ff00'> >> {msg}</span>")
            else:
                for pid in alive_ids:
                    sim_state[pid]['en'] = min(100, sim_state[pid]['en'] + 5)

                att_id = random.choice(alive_ids)
                att_team = p_team_map[att_id]
                active_attacker = att_id

                enemies = [pid for pid in alive_ids if p_team_map[pid] != att_team]
                if enemies:
                    vic_id = random.choice(enemies)
                    active_victim = vic_id

                    current_en = sim_state[att_id]['en']

                    if current_en >= 100 and random.random() < 0.3:
                        dmg = 9999
                        sim_state[att_id]['en'] = 0
                        event_type = "dgun"
                        log_cls = "log-dgun"
                        wpn_name = "D-GUN"
                    else:
                        dmg = random.randint(10, 25)
                        sim_state[att_id]['en'] = max(0, current_en - 10)
                        event_type = "attack"
                        log_cls = ""
                        wpn_name = "Laser"

                    sim_state[vic_id]['hp'] -= dmg

                    att_hex = next(p['hex'] for p in players if p['id'] == att_id)
                    vic_hex = next(p['hex'] for p in players if p['id'] == vic_id)

                    log_entry = (
                        f"[{tick}] <span style='color:{att_hex}'>COM_{att_id}</span> "
                        f"fires {wpn_name} >> <span style='color:{vic_hex}'>COM_{vic_id}</span> "
                        f"(-{dmg} HP)"
                    )

                    if event_type == "dgun":
                        log_entry = f"<span class='log-dgun'>{log_entry}</span>"

                    if sim_state[vic_id]['hp'] <= 0:
                        log_entry += " <span class='log-kill'>[COMBLAST]</span>"
                        active_victim = vic_id
                        event_type = "die"

                    logs.append(log_entry)

            if len(logs) > 50: logs = logs[-50:]
            reversed_logs = "<br>".join(logs[::-1])
            log_placeholder.markdown(f'<div class="battle-log">{reversed_logs}</div>', unsafe_allow_html=True)

            arena_html = "<div style='display:flex; flex-wrap:wrap; gap:15px; justify-content:center;'>"
            for t_idx, team in enumerate(teams_list):
                team_alive = any(sim_state[p['id']]['hp'] > 0 for p in team)
                opacity = "1.0" if team_alive else "0.3"
                border_col = "#00ff00" if team_alive else "#333"

                arena_html += f"<div style='flex:1; min-width:220px; border-top: 2px solid {border_col}; background:#111; padding:10px; opacity:{opacity}'>"
                arena_html += f"<div class='faction-label'>TEAM {t_idx + 1}</div>"
                arena_html += "<div style='display:flex; flex-wrap:wrap; justify-content:center;'>"

                for p in team:
                    pid = p['id']
                    s = sim_state[pid]
                    is_alive = s['hp'] > 0

                    evt = None
                    if is_alive and pid == active_attacker: evt = event_type if event_type == "dgun" else "attack"
                    if is_alive and pid == active_victim: evt = "hit"
                    if not is_alive and pid == active_victim and event_type == "die": evt = "die"

                    arena_html += render_commander_box(p, s['hp'], s['en'], is_alive, evt, show_hud=True)

                arena_html += "</div></div>"
            arena_html += "</div>"
            arena_placeholder.markdown(arena_html, unsafe_allow_html=True)

            time.sleep(sim_speed)