import json
import uuid
import threading
import socket
import requests
import math
import random
import sqlite3
import os
import time
import copy
from flask import Flask, request, jsonify
from PySide6.QtCore import QDateTime, QObject, Signal

# --- SERVER SIDE ---
app = Flask(__name__)
import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

db_lock = threading.Lock()

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
    with db_lock:
        session = db_store["sessions"].get(sid)
    return jsonify(session) if session else (jsonify({"error": "Not found"}), 404)


@app.route('/session/new', methods=['POST'])
def create_session():
    data = request.json
    sid = data.get("id")
    with db_lock:
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
    with db_lock:
        if sid in db_store["sessions"]:
            db_store["sessions"][sid]["players"][uid] = p_data
            log = {"type": "JOIN", "content": f"{p_data['name']} приєднався!", "timestamp": "NOW", "sender_id": "SYS",
                   "is_secret": False}
            db_store["sessions"][sid]["logs"].append(log)
            return jsonify({"success": True})
    return jsonify({"error": "No session"}), 404


@app.route('/player/update', methods=['POST'])
def update_player():
    data = request.json
    sid, uid, new_data = data.get("sid"), data.get("uid"), data.get("data")
    with db_lock:
        if sid in db_store["sessions"] and uid in db_store["sessions"][sid]["players"]:
            db_store["sessions"][sid]["players"][uid].update(new_data)
            return jsonify({"success": True})
    return jsonify({"error": "Err"}), 404


@app.route('/update/logs', methods=['POST'])
def add_log():
    data = request.json
    sid, log = data.get("sid"), data.get("log")
    with db_lock:
        if sid in db_store["sessions"]:
            db_store["sessions"][sid]["logs"].append(log)
            return jsonify({"success": True})
    return jsonify({"error": "Err"}), 404


@app.route('/combat/state/<sid>', methods=['GET'])
def get_combat_state_route(sid):
    with db_lock:
        state = db_store["combat_state"].get(sid, {})
    return jsonify(state)


@app.route('/combat/update', methods=['POST'])
def update_combat_route():
    data = request.json
    sid = data.get("sid")
    new_state = data.get("state")
    with db_lock:
        if sid in db_store["combat_state"]:
            if "tokens" in new_state:
                db_store["combat_state"][sid]["tokens"].update(new_state["tokens"])
                temp_state = new_state.copy()
                del temp_state["tokens"]
                db_store["combat_state"][sid].update(temp_state)
            else:
                db_store["combat_state"][sid].update(new_state)
            return jsonify({"success": True})
    return jsonify({"error": "No session"}), 404


# --- CLIENT ---
class DataManager(QObject):
    _instance = None
    GITHUB_RAW_BASE = "https://raw.githubusercontent.com/5e-bits/5e-database/refs/heads/main/src/2014"
    FILES_MAP = {
        "races": "5e-SRD-Races.json", "classes": "5e-SRD-Classes.json", "monsters": "5e-SRD-Monsters.json",
        "spells": "5e-SRD-Spells.json", "subraces": "5e-SRD-Subraces.json", "subclasses": "5e-SRD-Subclasses.json",
        "skills": "5e-SRD-Skills.json", "equipment": "5e-SRD-Equipment.json", "traits": "5e-SRD-Traits.json",
        "ability_scores": "5e-SRD-Ability-Scores.json"
    }

    def add_object_to_combat(self, obj_type):
        """
        Додає неживий об'єкт на поле бою (стіна, бочка).
        """
        if not self._current_session_id: return

        obj_definitions = {
            "wall": {"name": "Стіна", "color": "#607D8B", "symbol": "█", "hp": 100},
            "barrel": {"name": "Вибухова Бочка", "color": "#FF5722", "symbol": "🛢️", "hp": 10},
            "trap": {"name": "Пастка", "color": "#9E9E9E", "symbol": "⚠", "hp": 5},
            "chest": {"name": "Скриня", "color": "#FFC107", "symbol": "📦", "hp": 20}
        }

        definition = obj_definitions.get(obj_type)
        if not definition: return

        uid = f"OBJ_{str(uuid.uuid4())[:4]}"

        # Додаємо як токен, але з типом 'object'
        new_token = {
            uid: {
                "name": definition['name'],
                "x": 0, "y": 0,
                "color": definition['color'],
                "type": "object",  # Важливо для логіки переміщення
                "symbol": definition['symbol'],  # Для відображення на мапі
                "hp": definition['hp'],
                "max_hp": definition['hp']
            }
        }
        self.update_combat_state({"tokens": new_token})
        return uid

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
        self.is_host = True
        self.server_ip = "127.0.0.1"
        self.server_port = 5000
        self.server_url = f"http://{self.server_ip}:{self.server_port}"
        self._current_session_id = None

        self.start_server()

        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        self.db_path = os.path.join(project_root, "dnd_data.sqlite3")

        self.races = {};
        self.classes = {};
        self.skills_list = []
        self.subrace_map = {};
        self.subclass_map = {};
        self.spells_data = {};
        self.creature_bestiary = {}
        self._client_lock = threading.Lock()

        loaded = self._load_data_from_sqlite()
        if not loaded:
            self._seed_db_from_github()
            if not self._load_data_from_sqlite(): self._load_fallbacks()

        self.master_items = {
            "dagger": {"name": "Dagger", "type": "Weapon", "subtype": "Melee", "damage": "1d4"},
            "shortsword": {"name": "Shortsword", "type": "Weapon", "subtype": "Melee", "damage": "1d6"},
            "longsword": {"name": "Longsword", "type": "Weapon", "subtype": "Melee", "damage": "1d8"},
            "bow": {"name": "Shortbow", "type": "RangedWeapon", "subtype": "Ranged", "damage": "1d6"},
            "potion": {"name": "Potion of Healing", "type": "Consumable", "effect": "Heal 2d4+2"},
            "focus": {"name": "Arcane Focus", "type": "Focus", "desc": "Orb or Wand"}
        }
        self.combat_maneuvers = {
            "phys_pressure": {"name": "⚔️ Фізичний Тиск", "desc": "Силова атака зброєю.", "type": "physical",
                              "stat_options": ["str", "dex"], "effect_formula": "mod", "req_item_type": "Weapon"},
            "unarmed_strike": {"name": "👊 Рукопашний Бій", "desc": "Атака кулаками.", "type": "physical",
                               "stat_options": ["str", "dex"], "effect_formula": "mod", "req_item_type": None},
            "morale_break": {"name": "😱 Злам Духу", "desc": "Залякування.", "type": "morale", "stat_options": ["cha"],
                             "effect_formula": "mod", "req_item_type": None},
            "magic_assault": {"name": "✨ Магічний Постріл", "desc": "Закляття.", "type": "hybrid",
                              "stat_options": ["int", "wis"], "effect_formula": "half_mod_split",
                              "req_item_type": "Focus"},
            "precise_shot": {"name": "🎯 Точний Постріл", "desc": "Дистанційна атака.", "type": "physical",
                             "stat_options": ["dex"], "effect_formula": "mod", "req_item_type": "RangedWeapon"},
            "support": {"name": "❤️ Підтримка", "desc": "Допомога союзнику.", "type": "support",
                        "stat_options": ["int", "wis", "cha"], "effect_formula": "mod", "req_item_type": None}
        }
        self._local_combat_state = {"active": False, "round": 0, "turn_order": [], "current_turn_index": 0,
                                    "tokens": {}}

    # --- DB LOGIC (Condensed for brevity, logic same as before) ---
    def _seed_db_from_github(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except:
                pass
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for table_name in self.FILES_MAP.keys():
            cursor.execute(
                f'CREATE TABLE IF NOT EXISTS "{table_name}" (index_name TEXT PRIMARY KEY, name TEXT, data JSON)')
        for table_name, filename in self.FILES_MAP.items():
            url = f"{self.GITHUB_RAW_BASE}/{filename}"
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    for item in resp.json():
                        if item.get('index') and item.get('name'):
                            cursor.execute(f'INSERT OR REPLACE INTO "{table_name}" VALUES (?, ?, ?)',
                                           (item['index'], item['name'], json.dumps(item)))
            except:
                pass
        conn.commit();
        conn.close()

    def _load_data_from_sqlite(self):
        if not os.path.exists(self.db_path): return False
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing = {r[0] for r in cursor.fetchall()}
            if not {'races', 'classes', 'monsters'}.issubset(existing): conn.close(); return False

            # Subraces/Classes
            try:
                cursor.execute("SELECT data FROM subraces")
                for r in cursor.fetchall():
                    d = json.loads(r[0]);
                    self.subrace_map.setdefault(d.get('race', {}).get('index'), []).append(d['name'])
                cursor.execute("SELECT data FROM subclasses")
                for r in cursor.fetchall():
                    d = json.loads(r[0]);
                    self.subclass_map.setdefault(d.get('class', {}).get('index'), []).append(d['name'])
            except:
                pass

            # Races
            tbl = 'races' if 'races' in existing else 'species'
            cursor.execute(f"SELECT data FROM {tbl}")
            for r in cursor.fetchall():
                d = json.loads(r[0]);
                bns = {b['ability_score']['index']: b['bonus'] for b in d.get('ability_bonuses', [])}
                self.races[d['name']] = {"speed": d.get('speed', 30), "bonuses": bns,
                                         "subraces": self.subrace_map.get(d['index'], [])}

            # Classes
            cursor.execute("SELECT data FROM classes")
            skills_set = set()
            for r in cursor.fetchall():
                d = json.loads(r[0]);
                s_list = []
                if d.get('proficiency_choices'):
                    for o in d['proficiency_choices'][0]['from'].get('options', []):
                        if 'item' in o: nm = o['item']['name'].replace('Skill: ', ''); s_list.append(
                            nm); skills_set.add(nm)
                self.classes[d['name']] = {"hit_die": d.get('hit_die', 8), "skills_count": 2,
                                           "available_skills": s_list, "is_caster": 'spellcasting' in d,
                                           "specializations": self.subclass_map.get(d['index'], [])}
            self.skills_list = sorted(list(skills_set)) if skills_set else ["Athletics"]

            # Monsters
            self.creature_bestiary = {}
            cursor.execute("SELECT data FROM monsters")
            for r in cursor.fetchall():
                m = json.loads(r[0]);
                ac = 10
                if m.get('armor_class'):
                    raw = m['armor_class'];
                    ac = raw[0].get('value', 10) if isinstance(raw, list) else raw
                acts = [{"name": a['name'], "desc": a['desc'], "type": "physical"} for a in m.get('actions', [])]
                if not acts: acts = [{"name": "Attack", "desc": "Basic", "type": "physical"}]
                self.creature_bestiary[m['index']] = {"name": m['name'], "hp": m.get('hit_points', 10), "ac": ac,
                                                      "initiative_bonus": (m.get('dexterity', 10) - 10) // 2,
                                                      "symbol": m['name'][0], "actions": acts}

            # Spells
            self.spells_data = {}
            if 'spells' in existing:
                cursor.execute("SELECT data FROM spells")
                for r in cursor.fetchall():
                    s = json.loads(r[0]);
                    for c in s.get('classes', []): self.spells_data.setdefault(c['name'], []).append(s['name'])
                for k in self.spells_data: self.spells_data[k].sort()
            conn.close();
            return True
        except:
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
                "p1": {"name": "Potion", "type": "Consumable"}}

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

    # Server & Session
    def start_server(self):
        self.is_host = True
        threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False),
                         daemon=True).start()

    def set_host_address(self, ip):
        self.server_url = f"http://{ip}:5000"

    def start_new_session(self):
        sid = "SESS_" + str(uuid.uuid4())[:4].upper()
        with db_lock:
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
                self._current_session_id = sid;
                return True
        except:
            pass
        return False

    def get_session_players(self, sid):
        if self.is_host:
            with db_lock: return copy.deepcopy(db_store["sessions"].get(sid, {}).get("players", {}))
        try:
            return requests.get(f"{self.server_url}/session/{sid}", timeout=1).json().get("players", {})
        except:
            return {}

    def get_session_updates(self, sid):
        if self.is_host:
            with db_lock: return copy.deepcopy(db_store["sessions"].get(sid, {}).get("logs", []))
        try:
            return requests.get(f"{self.server_url}/session/{sid}", timeout=1).json().get("logs", [])
        except:
            return []

    def get_dm_id(self, sid):
        return "HOST" if self.is_host else None

    def save_character(self, data):
        if not self._current_session_id: return data
        try:
            requests.post(f"{self.server_url}/join",
                          json={"sid": self._current_session_id, "uid": self.user_id, "player_data": data}); return data
        except:
            return data

    def update_character_data(self, p):
        if self.is_host:
            with db_lock:
                db_store["sessions"].get(self._current_session_id, {}).get("players", {}).get(self.user_id, {}).update(
                    p)
        else:
            requests.post(f"{self.server_url}/player/update",
                          json={"sid": self._current_session_id, "uid": self.user_id, "data": p})

    def push_session_update(self, sid, c, t="MESSAGE", is_secret=False):
        if not sid: return
        l = {"type": t, "content": c, "timestamp": QDateTime.currentDateTime().toString("hh:mm"),
             "sender_id": self.user_id, "is_secret": is_secret}
        if self.is_host:
            with db_lock:
                db_store["sessions"].get(sid, {}).get("logs", []).append(l)
        else:
            requests.post(f"{self.server_url}/update/logs", json={"sid": sid, "log": l})

    def subscribe_to_players(self, s, cb):
        cb(self.get_session_players(s))

    def grant_item_to_player(self, t, i):
        return True

    def save_item(self, d):
        return True

    def save_scenario_tree(self, d):
        return True

    # --- COMBAT ---
    def get_bestiary(self):
        return self.creature_bestiary

    def get_combat_state(self):
        if not self._current_session_id: return copy.deepcopy(self._local_combat_state)
        if self.is_host:
            with db_lock: return copy.deepcopy(
                db_store["combat_state"].get(self._current_session_id, self._local_combat_state))
        try:
            return requests.get(f"{self.server_url}/combat/state/{self._current_session_id}", timeout=0.5).json()
        except:
            return copy.deepcopy(self._local_combat_state)

    def update_combat_state(self, p):
        if not self._current_session_id: return
        if self.is_host:
            with db_lock:
                st = db_store["combat_state"].get(self._current_session_id)
                if st:
                    if "tokens" in p:
                        st["tokens"].update(p["tokens"])
                        p_copy = p.copy();
                        del p_copy["tokens"];
                        st.update(p_copy)
                    else:
                        st.update(p)
        else:
            requests.post(f"{self.server_url}/combat/update", json={"sid": self._current_session_id, "state": p})

    def start_combat(self):
        self.update_combat_state({"active": True, "round": 1})

    def add_creature_to_combat(self, k, n=None):
        d = self.creature_bestiary.get(k);
        if not d: return
        uid = f"NPC_{str(uuid.uuid4())[:4]}"
        self.update_combat_state({"tokens": {
            uid: {"name": n or d['name'], "x": 0, "y": 0, "color": "#D32F2F", "type": "enemy",
                  "init_bonus": d['initiative_bonus'], "actions": d.get('actions', [])}}})
        return uid

    def roll_initiative(self):
        c = [];
        st = self.get_combat_state();
        t = st.get("tokens", {})
        for u, p in self.get_session_players(self._current_session_id).items():
            if u not in t: t[u] = {"x": 1, "y": 1, "color": "#388E3C", "name": p.get("name"), "type": "player"}
        for u, tok in t.items():
            mod = tok.get('init_bonus', 0)
            c.append({"uid": u, "name": tok["name"], "total": random.randint(1, 20) + mod,
                      "type": tok.get('type', 'unknown')})
        c.sort(key=lambda x: x['total'], reverse=True)
        self.update_combat_state({"turn_order": c, "current_turn_index": 0, "tokens": t})

    def move_token(self, u, x, y, is_dm=False):
        """
        Оновлена логіка переміщення.
        DM може рухати всіх ДО бою (active=False).
        Після початку бою (active=True): DM рухає тільки ворогів, Гравець - себе.
        """
        st = self.get_combat_state()
        if u not in st.get("tokens", {}): return False

        is_combat_active = st.get("active", False)
        token_type = st["tokens"][u].get("type", "unknown")

        # Якщо це ДМ
        if is_dm:
            # До бою: можна все
            if not is_combat_active:
                pass
            # У бою: тільки ворогів (або NPC)
            elif token_type == 'player':
                # УВАГА: Забороняємо ДМ рухати гравців під час бою за вашим запитом
                return False

                # Якщо це Гравець (is_dm=False)
        else:
            # Гравець може рухати тільки себе (перевірка my_uid робиться на рівні віджета,
            # тут ми довіряємо, що u == self.user_id, але можна перевірити)
            if u != self.user_id: return False

        # Виконуємо рух
        self.update_combat_state({"tokens": {u: {"x": x, "y": y}}})
        return True