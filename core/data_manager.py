import json
import uuid
import threading
import socket
import requests
import math
import random
import sqlite3
import os
from flask import Flask, request, jsonify
from PySide6.QtCore import QDateTime, QObject, Signal

# --- SERVER SIDE (FLASK) ---
app = Flask(__name__)
import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

db_store = {
    "sessions": {},
    "active_session_id": None,
    "items": {},
    "combat_state": {}
}


@app.route('/status', methods=['GET'])
def get_status(): return jsonify({"status": "running", "dm_id": "HOST"})


@app.route('/session/<sid>', methods=['GET'])
def get_session(sid):
    session = db_store["sessions"].get(sid)
    return jsonify(session) if session else (jsonify({"error": "Not found"}), 404)


@app.route('/session/new', methods=['POST'])
def create_session():
    data = request.json
    sid = data.get("id")
    db_store["sessions"][sid] = data["data"]
    db_store["active_session_id"] = sid
    db_store["combat_state"][sid] = {
        "active": False, "round": 0, "turn_order": [],
        "current_turn_index": 0, "tokens": {}
    }
    return jsonify({"success": True})


@app.route('/join', methods=['POST'])
def join_player():
    data = request.json
    sid, uid, p_data = data.get("sid"), data.get("uid"), data.get("player_data")
    if sid in db_store["sessions"]:
        db_store["sessions"][sid]["players"][uid] = p_data
        log = {"type": "JOIN", "content": f"{p_data['name']} joined!", "timestamp": "NOW", "sender_id": "SYS",
               "is_secret": False}
        db_store["sessions"][sid]["logs"].append(log)
        return jsonify({"success": True})
    return jsonify({"error": "No session"}), 404


@app.route('/player/update', methods=['POST'])
def update_player():
    data = request.json
    sid, uid, new_data = data.get("sid"), data.get("uid"), data.get("data")
    if sid in db_store["sessions"] and uid in db_store["sessions"][sid]["players"]:
        db_store["sessions"][sid]["players"][uid].update(new_data)
        return jsonify({"success": True})
    return jsonify({"error": "Err"}), 404


@app.route('/update/logs', methods=['POST'])
def add_log():
    data = request.json
    sid, log = data.get("sid"), data.get("log")
    if sid in db_store["sessions"]:
        db_store["sessions"][sid]["logs"].append(log)
        return jsonify({"success": True})
    return jsonify({"error": "Err"}), 404


@app.route('/combat/state/<sid>', methods=['GET'])
def get_combat_state_route(sid):
    state = db_store["combat_state"].get(sid, {})
    return jsonify(state)


@app.route('/combat/update', methods=['POST'])
def update_combat_route():
    data = request.json
    sid = data.get("sid")
    new_state = data.get("state")
    if sid in db_store["combat_state"]:
        db_store["combat_state"][sid].update(new_state)
        return jsonify({"success": True})
    return jsonify({"error": "No session"}), 404


# --- CLIENT (DATA MANAGER) ---
class DataManager(QObject):
    _instance = None

    GITHUB_RAW_BASE_2014 = "https://raw.githubusercontent.com/5e-bits/5e-database/refs/heads/main/src/2014"
    GITHUB_RAW_BASE_2024 = "https://raw.githubusercontent.com/5e-bits/5e-database/refs/heads/main/src/2024"

    FILES_MAP = {
        "races": "5e-SRD-Races.json",
        "classes": "5e-SRD-Classes.json",
        "monsters": "5e-SRD-Monsters.json",
        "spells": "5e-SRD-Spells.json",
        "subraces": "5e-SRD-Subraces.json",
        "subclasses": "5e-SRD-Subclasses.json",
        "skills": "5e-SRD-Skills.json",
        "equipment": "5e-SRD-Equipment.json",
        "traits": "5e-SRD-Traits.json",
        "ability_scores": "5e-SRD-Ability-Scores.json"
    }

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(DataManager, cls).__new__(cls)
            cls._instance._init_once()
        return cls._instance

    def __init__(self):
        pass

    def _init_once(self):
        super().__init__()
        self.user_id = "USER_" + str(uuid.uuid4())[:4].upper()
        self.is_host = False  # Will be set to True when server starts
        self.server_ip = "127.0.0.1"
        self.server_port = 5000
        self.server_url = f"http://{self.server_ip}:{self.server_port}"  # Set default immediately
        self._current_session_id = None

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        self.db_path = os.path.join(project_root, "dnd_data.sqlite3")

        print(f"🔍 DB Path: {self.db_path}")

        self.races = {}
        self.classes = {}
        self.skills_list = []
        self.subrace_map = {}
        self.subclass_map = {}
        self.spells_data = {}
        self.creature_bestiary = {}

        loaded = self._load_data_from_sqlite()

        if not loaded:
            print("⚠️ Database needs initialization. Starting download...")
            self._seed_db_combined()
            if self._load_data_from_sqlite():
                print("✅ Database initialized and loaded successfully.")
            else:
                print("❌ Failed to initialize DB. Using fallbacks.")
                self._load_fallbacks()

        self.master_items = {
            "dagger": {"name": "Dagger", "type": "Weapon", "subtype": "Melee", "damage": "1d4"},
            "shortsword": {"name": "Shortsword", "type": "Weapon", "subtype": "Melee", "damage": "1d6"},
            "longsword": {"name": "Longsword", "type": "Weapon", "subtype": "Melee", "damage": "1d8"},
            "bow": {"name": "Shortbow", "type": "RangedWeapon", "subtype": "Ranged", "damage": "1d6"},
            "potion": {"name": "Potion of Healing", "type": "Consumable", "effect": "Heal 2d4+2"},
            "focus": {"name": "Arcane Focus", "type": "Focus", "desc": "Orb or Wand"}
        }

        self.combat_maneuvers = {
            "phys_pressure": {"name": "⚔️ Physical Pressure", "desc": "Strong weapon attack.", "type": "physical",
                              "stat_options": ["str", "dex"], "effect_formula": "mod", "req_item_type": "Weapon"},
            "unarmed_strike": {"name": "👊 Unarmed Strike", "desc": "Punch or Kick.", "type": "physical",
                               "stat_options": ["str", "dex"], "effect_formula": "mod", "req_item_type": None},
            "morale_break": {"name": "😱 Intimidate", "desc": "Psychological attack.", "type": "morale",
                             "stat_options": ["cha"], "effect_formula": "mod", "req_item_type": None},
            "magic_assault": {"name": "✨ Magic Bolt", "desc": "Magical damage.", "type": "hybrid",
                              "stat_options": ["int", "wis"], "effect_formula": "half_mod_split",
                              "req_item_type": "Focus"},
            "precise_shot": {"name": "🎯 Precise Shot", "desc": "Ranged attack.", "type": "physical",
                             "stat_options": ["dex"], "effect_formula": "mod", "req_item_type": "RangedWeapon"},
            "support": {"name": "❤️ Support", "desc": "Help ally.", "type": "support",
                        "stat_options": ["int", "wis", "cha"], "effect_formula": "mod", "req_item_type": None}
        }

        self._local_combat_state = {"active": False, "round": 0, "turn_order": [], "current_turn_index": 0,
                                    "tokens": {}}

        # --- CRITICAL FIX: START SERVER AUTOMATICALLY ---
        # This ensures that when you run the app locally, the 'server' is active
        # so that requests to localhost:5000 don't fail.
        self.start_server()

    # --- DB MANAGEMENT ---

    def _seed_db_combined(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except:
                pass

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for table_name in self.FILES_MAP.keys():
            cursor.execute(
                f'CREATE TABLE IF NOT EXISTS "{table_name}" (index_name TEXT PRIMARY KEY, name TEXT, data JSON, source TEXT)')

        def process_version(base_url, version_label):
            print(f"🌐 Processing {version_label} rules from {base_url}...")
            for table_name, filename in self.FILES_MAP.items():
                url = f"{base_url}/{filename}"
                try:
                    resp = requests.get(url, timeout=10)
                    if resp.status_code == 200:
                        data_list = resp.json()
                        count = 0
                        for item in data_list:
                            idx = item.get('index')
                            name = item.get('name')
                            if idx and name:
                                cursor.execute(f'INSERT OR REPLACE INTO "{table_name}" VALUES (?, ?, ?, ?)',
                                               (idx, name, json.dumps(item), version_label))
                                count += 1
                        print(f"      ✅ Inserted {count} records into {table_name}.")
                except Exception as e:
                    print(f"      ❌ Error downloading {filename}: {e}")

        process_version(self.GITHUB_RAW_BASE_2014, "2014")
        process_version(self.GITHUB_RAW_BASE_2024, "2024")

        conn.commit()
        conn.close()
        print("🎉 Database seeding finished.")

    def _load_data_from_sqlite(self):
        if not os.path.exists(self.db_path): return False

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in cursor.fetchall()}

            required = {'races', 'classes', 'monsters'}
            if not required.issubset(existing_tables):
                conn.close()
                return False

            try:
                if 'subraces' in existing_tables:
                    cursor.execute("SELECT data FROM subraces")
                    for row in cursor.fetchall():
                        d = json.loads(row[0])
                        if d.get('race'): self.subrace_map.setdefault(d['race']['index'], []).append(d['name'])
                if 'subclasses' in existing_tables:
                    cursor.execute("SELECT data FROM subclasses")
                    for row in cursor.fetchall():
                        d = json.loads(row[0])
                        if d.get('class'): self.subclass_map.setdefault(d['class']['index'], []).append(d['name'])
            except:
                pass

            self.races = {}
            try:
                cursor.execute("SELECT data, source FROM races")
                rows = cursor.fetchall()
            except:
                cursor.execute("SELECT data FROM races")
                rows = [(r[0], "unknown") for r in cursor.fetchall()]

            for row in rows:
                d = json.loads(row[0])
                src = row[1]
                name = d['name']
                if src == '2024': name += " (2024)"
                bonuses = {b['ability_score']['index']: b['bonus'] for b in d.get('ability_bonuses', [])}
                self.races[name] = {"speed": d.get('speed', 30), "bonuses": bonuses,
                                    "subraces": self.subrace_map.get(d['index'], [])}

            self.classes = {}
            skill_set = set()
            try:
                cursor.execute("SELECT data FROM classes")
                for row in cursor.fetchall():
                    d = json.loads(row[0])
                    name = d['name']
                    skills = []
                    if 'proficiency_choices' in d:
                        choices = d['proficiency_choices']
                        if isinstance(choices, list):
                            for choice in choices:
                                if 'from' in choice and 'options' in choice['from']:
                                    for opt in choice['from']['options']:
                                        if 'item' in opt:
                                            s = opt['item']['name'].replace('Skill: ', '')
                                            skills.append(s);
                                            skill_set.add(s)

                    self.classes[name] = {
                        "hit_die": d.get('hit_die', 8),
                        "skills_count": d.get('proficiency_choices', [{}])[0].get('choose', 2) if d.get(
                            'proficiency_choices') else 2,
                        "available_skills": skills,
                        "is_caster": 'spellcasting' in d,
                        "specializations": self.subclass_map.get(d['index'], [])
                    }
                self.skills_list = sorted(list(skill_set)) if skill_set else ["Athletics", "Perception"]
            except:
                pass

            self.creature_bestiary = {}
            cursor.execute("SELECT data FROM monsters")
            for row in cursor.fetchall():
                m = json.loads(row[0])
                key = m['index']
                ac = 10
                if 'armor_class' in m:
                    raw_ac = m['armor_class']
                    if isinstance(raw_ac, list) and raw_ac:
                        ac = raw_ac[0].get('value', 10)
                    elif isinstance(raw_ac, int):
                        ac = raw_ac

                actions = []
                for act in m.get('actions', []):
                    actions.append({"name": act['name'], "desc": act.get('desc', ''), "type": "physical"})

                if not actions: actions.append({"name": "Attack", "desc": "Basic melee", "type": "physical"})

                self.creature_bestiary[key] = {
                    "name": m['name'], "hp": m.get('hit_points', 10), "ac": ac,
                    "initiative_bonus": (m.get('dexterity', 10) - 10) // 2,
                    "symbol": m['name'][0], "actions": actions
                }

            self.spells_data = {}
            if 'spells' in existing_tables:
                cursor.execute("SELECT data FROM spells")
                for row in cursor.fetchall():
                    s = json.loads(row[0])
                    s_name = s['name']
                    for c in s.get('classes', []):
                        if c.get('name'): self.spells_data.setdefault(c['name'], []).append(s_name)
                for k in self.spells_data: self.spells_data[k].sort()

            conn.close()
            if not self.races: return False
            return True
        except Exception as e:
            print(f"❌ DB Load Error: {e}")
            return False

    def _load_fallbacks(self):
        self.races = {"Human": {"speed": 30, "bonuses": {"str": 1}, "subraces": []}}
        self.classes = {
            "Fighter": {"hit_die": 10, "skills_count": 2, "available_skills": ["Athletics"], "is_caster": False}}
        self.skills_list = ["Athletics"]
        self.creature_bestiary = {"goblin": {"name": "Goblin", "hp": 7, "ac": 15, "initiative_bonus": 2, "symbol": "G",
                                             "actions": [{"name": "Scimitar", "desc": "1d6+2", "type": "physical"}]}}

    # --- GETTERS ---
    def get_inventory(self, uid):
        return {"w1": {"name": "Longsword", "type": "Weapon", "is_equipped": True},
                "p1": {"name": "Health Potion", "type": "Consumable", "is_equipped": False}}

    def get_master_item_dataset(self):
        return self.master_items

    def get_combat_maneuvers(self):
        return self.combat_maneuvers

    def get_races_data(self):
        return self.races

    def get_classes_data(self):
        return self.classes

    def get_all_skills(self):
        return self.skills_list

    def get_user_id(self):
        return self.user_id

    def get_current_session(self):
        return self._current_session_id

    def set_current_session(self, sid):
        self._current_session_id = sid

    def get_backgrounds(self):
        return ["Soldier", "Noble", "Acolyte", "Criminal"]

    def get_starter_pack(self, c):
        return []

    def get_spells_for_class(self, c):
        return self.spells_data.get(c, [])

    def calculate_max_fatigue(self, hp):
        return int(hp * 1.5)

    def get_potion_recovery(self, r):
        return "2d4+2"

    def get_rest_recovery_formula(self, l):
        return "1d8"

    # Server
    def start_server(self):
        self.is_host = True
        # Run Flask in a thread
        threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False),
                         daemon=True).start()

        local_ip = socket.gethostbyname(socket.gethostname())
        print(f"🚀 Server started at http://{local_ip}:5000")
        return local_ip

    def set_host_address(self, ip):
        self.server_url = f"http://{ip}:5000"

    def start_new_session(self):
        if not self.is_host:
            # Auto-start if not started yet (fallback safety)
            self.start_server()

        sid = "SESS_" + str(uuid.uuid4())[:4].upper()
        db_store["sessions"][sid] = {"status": "ACTIVE", "players": {}, "logs": [], "dm_id": self.user_id}
        db_store["combat_state"][sid] = {"active": False, "round": 0, "turn_order": [], "current_turn_index": 0,
                                         "tokens": {}}
        self._current_session_id = sid
        return sid

    def stop_session(self, sid):
        return True

    def join_session(self, cs):
        try:
            ip, sid = cs.split("/") if "/" in cs else ("127.0.0.1", cs)
            self.set_host_address(ip)
            if requests.get(f"{self.server_url}/session/{sid}", timeout=2).status_code == 200:
                self._current_session_id = sid
                return True
        except:
            pass
        return False

    def get_session_players(self, sid):
        if self.is_host: return db_store["sessions"].get(sid, {}).get("players", {})
        try:
            return requests.get(f"{self.server_url}/session/{sid}", timeout=1).json().get("players", {})
        except:
            return {}

    def get_session_updates(self, sid):
        if self.is_host: return db_store["sessions"].get(sid, {}).get("logs", [])
        try:
            return requests.get(f"{self.server_url}/session/{sid}", timeout=1).json().get("logs", [])
        except:
            return []

    def get_dm_id(self, sid):
        return "HOST" if self.is_host else None

    def save_character(self, data):
        # Ensure we have a session ID. If not, assume local play/creation.
        # If just creating a char without a session, we don't push to server.
        if not self._current_session_id: return data

        payload = {"sid": self._current_session_id, "uid": self.user_id, "player_data": data}
        try:
            requests.post(f"{self.server_url}/join", json=payload)
            return data
        except Exception as e:
            print(f"Save char failed: {e}")
            return data  # Return data anyway to not crash UI

    def update_character_data(self, p):
        if not self._current_session_id: return
        if self.is_host:
            sess = db_store["sessions"].get(self._current_session_id)
            if sess and self.user_id in sess["players"]:
                sess["players"][self.user_id].update(p)
        else:
            try:
                requests.post(f"{self.server_url}/player/update",
                              json={"sid": self._current_session_id, "uid": self.user_id, "data": p})
            except:
                pass

    def push_session_update(self, sid, c, t="MESSAGE", is_secret=False):
        if not sid: return False
        l = {"type": t, "content": c, "timestamp": QDateTime.currentDateTime().toString("hh:mm"),
             "sender_id": self.user_id, "is_secret": is_secret}

        if self.is_host:
            if sid in db_store["sessions"]:
                db_store["sessions"][sid]["logs"].append(l)
        else:
            try:
                requests.post(f"{self.server_url}/update/logs", json={"sid": sid, "log": l})
            except Exception as e:
                print(f"Push update failed: {e}")
        return True

    def subscribe_to_players(self, s, cb):
        cb(self.get_session_players(s))

    def grant_item_to_player(self, t, i):
        return True

    def save_item(self, d):
        return True

    def save_scenario_tree(self, d):
        return True

    # --- COMBAT LOGIC ---
    def get_bestiary(self):
        return self.creature_bestiary

    def get_combat_state(self):
        if not self._current_session_id: return self._local_combat_state

        if self.is_host:
            return db_store["combat_state"].get(self._current_session_id, self._local_combat_state)
        else:
            try:
                r = requests.get(f"{self.server_url}/combat/state/{self._current_session_id}", timeout=0.5)
                if r.status_code == 200: return r.json()
            except:
                pass
        return self._local_combat_state

    def update_combat_state(self, p):
        if not self._current_session_id: return

        if self.is_host:
            if self._current_session_id in db_store["combat_state"]:
                db_store["combat_state"][self._current_session_id].update(p)
        else:
            try:
                requests.post(f"{self.server_url}/combat/update", json={"sid": self._current_session_id, "state": p})
            except:
                pass

    def start_combat(self):
        self.update_combat_state({"active": True, "round": 1})

    def add_creature_to_combat(self, key, custom_name=None):
        d = self.creature_bestiary.get(key)
        if not d: return
        uid = f"NPC_{str(uuid.uuid4())[:4]}"
        name = custom_name if custom_name else d['name']
        st = self.get_combat_state()
        t = st.get("tokens", {})
        t[uid] = {"name": name, "x": 0, "y": 0, "color": "#D32F2F", "type": "enemy",
                  "init_bonus": d['initiative_bonus'], "actions": d.get('actions', [])}
        self.update_combat_state({"tokens": t})
        return uid

    def roll_initiative(self):
        c = []
        st = self.get_combat_state()
        t = st.get("tokens", {})

        # Add players if they are not on map yet
        for u, p in self.get_session_players(self._current_session_id).items():
            if u not in t: t[u] = {"x": 1, "y": 1, "color": "#388E3C", "name": p.get("name"), "type": "player"}

        # Recalculate initiative for everyone
        for uid, token in t.items():
            roll = random.randint(1, 20)
            if token.get('type') == 'enemy':
                roll += token.get('init_bonus', 0)
            # For players, we assume +0 mod if we don't have char sheet accessible here easily (simplified)

            c.append({"uid": uid, "name": token["name"], "total": roll, "type": token.get('type', 'unknown')})

        c.sort(key=lambda x: x["total"], reverse=True)
        self.update_combat_state({"turn_order": c, "current_turn_index": 0, "tokens": t})

    def move_token(self, u, x, y):
        st = self.get_combat_state()
        t = st.get("tokens", {})
        if u in t:
            t[u]["x"] = x;
            t[u]["y"] = y
            self.update_combat_state({"tokens": t})
            return True
        return False