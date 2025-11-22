import json
import uuid
import threading
import socket
import requests
import math
from flask import Flask, request, jsonify
from PySide6.QtCore import QDateTime, QObject, Signal

# --- СЕРВЕРНА ЧАСТИНА ---
app = Flask(__name__)
# Вимикаємо зайві логи Flask
import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

db_store = {"sessions": {}, "active_session_id": None, "items": {}}


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
    return jsonify({"success": True})


@app.route('/join', methods=['POST'])
def join_player():
    data = request.json
    sid, uid, p_data = data.get("sid"), data.get("uid"), data.get("player_data")
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


# --- КЛІЄНТ ---
class DataManager(QObject):
    _instance = None

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
        self.is_host = False
        self.server_ip = "127.0.0.1"
        self.server_port = 5000
        self.server_url = None
        self._current_session_id = None

        # --- ПРЕДМЕТИ ---
        self.master_items = {
            "dagger": {"name": "Кинджал", "type": "Weapon", "damage": "1d4"},
            "shortsword": {"name": "Короткий меч", "type": "Weapon", "damage": "1d6"},
            "longsword": {"name": "Довгий меч", "type": "Weapon", "damage": "1d8"},
            "greatsword": {"name": "Дворучний меч", "type": "Weapon", "damage": "2d6"},
            "greataxe": {"name": "Велика сокира", "type": "Weapon", "damage": "1d12"},
            "handaxe": {"name": "Ручна сокира", "type": "Weapon", "damage": "1d6"},
            "bow_short": {"name": "Короткий лук", "type": "Weapon", "damage": "1d6"},
            "bow_long": {"name": "Довгий лук", "type": "Weapon", "damage": "1d8"},
            "staff": {"name": "Посох", "type": "Weapon", "damage": "1d6"},
            "wand": {"name": "Чарівна паличка", "type": "Weapon", "damage": "1d4"},
            "leather": {"name": "Шкіряна броня", "type": "Armor", "ac": 11},
            "chainmail": {"name": "Кольчуга", "type": "Armor", "ac": 16},
            "plate": {"name": "Лати", "type": "Armor", "ac": 18},
            "shield": {"name": "Щит", "type": "Armor", "ac": 2},
            "potion": {"name": "Зілля Лікування", "type": "Consumable", "effect": "Heal 2d4+2"},
            "rations": {"name": "Пайок", "type": "Gear"},
            "rope": {"name": "Мотузка", "type": "Gear"}
        }

        # --- СТАРТОВІ НАБОРИ ---
        self.starter_packs = {
            "Barbarian": ["greataxe", "handaxe", "rations"],
            "Bard": ["shortsword", "dagger", "leather"],
            "Cleric": ["staff", "chainmail", "shield"],
            "Druid": ["leather", "shield", "staff"],
            "Fighter": ["chainmail", "longsword", "shield"],
            "Monk": ["shortsword", "dagger"],
            "Paladin": ["chainmail", "longsword", "shield"],
            "Ranger": ["leather", "shortsword", "longbow"],
            "Rogue": ["leather", "dagger", "shortsword"],
            "Sorcerer": ["dagger", "wand"],
            "Warlock": ["leather", "dagger", "staff"],
            "Wizard": ["dagger", "staff"]
        }

        # --- ЗАКЛЯТТЯ (SPELLS) ---
        self.spells_data = {
            "Bard": ["Vicious Mockery", "Cure Wounds", "Healing Word", "Thunderwave"],
            "Cleric": ["Guidance", "Bless", "Cure Wounds", "Guiding Bolt", "Shield of Faith"],
            "Druid": ["Shillelagh", "Entangle", "Cure Wounds", "Thunderwave"],
            "Paladin": ["Divine Sense", "Lay on Hands", "Bless", "Cure Wounds"],
            "Ranger": ["Hunter's Mark", "Cure Wounds"],
            "Sorcerer": ["Fire Bolt", "Magic Missile", "Shield", "Burning Hands"],
            "Warlock": ["Eldritch Blast", "Hex", "Hellish Rebuke"],
            "Wizard": ["Fire Bolt", "Mage Hand", "Magic Missile", "Shield", "Sleep", "Burning Hands"]
        }

        # --- РАСИ ---
        self.races = {
            "Human": {"speed": 30, "bonuses": {"str": 1, "dex": 1, "con": 1, "int": 1, "wis": 1, "cha": 1},
                      "subraces": []},
            "Elf": {"speed": 30, "bonuses": {"dex": 2}, "subraces": ["High Elf", "Wood Elf", "Drow"]},
            "Dwarf": {"speed": 25, "bonuses": {"con": 2}, "subraces": ["Hill Dwarf", "Mountain Dwarf"]},
            "Halfling": {"speed": 25, "bonuses": {"dex": 2}, "subraces": ["Lightfoot", "Stout"]},
            "Dragonborn": {"speed": 30, "bonuses": {"str": 2, "cha": 1}, "subraces": ["Red", "Blue", "Green"]},
            "Tiefling": {"speed": 30, "bonuses": {"cha": 2, "int": 1}, "subraces": []}
        }

        self.skills_list = ["Athletics", "Acrobatics", "Stealth", "Insight", "Intimidation", "Deception", "Persuasion",
                            "Medicine", "History", "Religion", "Arcana", "Nature", "Survival", "Perception",
                            "Performance", "Sleight of Hand"]

        # --- КЛАСИ ---
        self.classes = {
            "Barbarian": {"hit_die": 12, "skills_count": 2, "specializations": ["Rage Damage +2"], "subclass_level": 3,
                          "available_skills": ["Athletics", "Intimidation", "Survival"]},
            "Bard": {"hit_die": 8, "skills_count": 3, "specializations": ["Bardic Inspiration (d6)"],
                     "subclass_level": 3, "available_skills": self.skills_list, "is_caster": True},
            "Cleric": {"hit_die": 8, "skills_count": 2, "specializations": ["Life Domain", "War Domain"],
                       "subclass_level": 1, "available_skills": ["History", "Medicine", "Religion"], "is_caster": True},
            "Druid": {"hit_die": 8, "skills_count": 2, "specializations": ["Wild Shape"], "subclass_level": 2,
                      "available_skills": ["Nature", "Survival", "Animal Handling"], "is_caster": True},
            "Fighter": {"hit_die": 10, "skills_count": 2,
                        "specializations": ["Defense", "Dueling", "Archery", "Great Weapon Fighting"],
                        "subclass_level": 3, "available_skills": ["Athletics", "Acrobatics", "Intimidation"]},
            "Monk": {"hit_die": 8, "skills_count": 2, "specializations": ["Unarmored Defense"], "subclass_level": 3,
                     "available_skills": ["Acrobatics", "Athletics", "Stealth"]},
            "Paladin": {"hit_die": 10, "skills_count": 2, "specializations": ["Defense", "Dueling"],
                        "subclass_level": 3, "available_skills": ["Athletics", "Intimidation", "Religion"],
                        "is_caster": True},
            "Ranger": {"hit_die": 10, "skills_count": 3, "specializations": ["Archery", "Two-Weapon Fighting"],
                       "subclass_level": 3, "available_skills": ["Nature", "Stealth", "Survival"], "is_caster": True},
            "Rogue": {"hit_die": 8, "skills_count": 4, "specializations": ["Sneak Attack"], "subclass_level": 3,
                      "available_skills": self.skills_list},
            "Sorcerer": {"hit_die": 6, "skills_count": 2, "specializations": ["Draconic Resilience"],
                         "subclass_level": 1, "available_skills": ["Arcana", "Deception"], "is_caster": True},
            "Warlock": {"hit_die": 8, "skills_count": 2, "specializations": ["Pact of the Chain", "Pact of the Blade"],
                        "subclass_level": 1, "available_skills": ["Arcana", "Intimidation"], "is_caster": True},
            "Wizard": {"hit_die": 6, "skills_count": 2, "specializations": ["Arcane Recovery"], "subclass_level": 2,
                       "available_skills": ["Arcana", "History"], "is_caster": True}
        }

        # --- МАНЕВРИ ---
        self.combat_maneuvers = {
            "phys_pressure": {"name": "⚔️ Фізичний Тиск", "desc": "Удар, що виснажує.", "type": "physical",
                              "stat_options": ["str", "dex"], "effect_formula": "mod"},
            "morale_break": {"name": "😱 Злам Духу", "desc": "Психологічна атака.", "type": "morale",
                             "stat_options": ["cha"], "effect_formula": "mod"},
            "magic_assault": {"name": "✨ Магічна Атака", "desc": "Шкода по Втомі та Моралі.", "type": "hybrid",
                              "stat_options": ["int", "wis"], "effect_formula": "half_mod_split"},
            "support": {"name": "❤️ Підтримка", "desc": "Відновлення.", "type": "support",
                        "stat_options": ["int", "wis", "cha"], "effect_formula": "mod"},
            "move_debuff": {"name": "🏃 Рух (Дебаф)", "desc": "+1 Втоми ворогу, +1 собі.", "type": "hybrid",
                            "stat_options": ["dex", "wis"], "effect_formula": "move_special"}
        }

    # --- ВІДНОВЛЕНІ МЕТОДИ ДОСТУПУ (ЩОБ ВИПРАВИТИ ПОМИЛКУ) ---

    def get_inventory(self, character_id=None):
        """Повертає інвентар персонажа. (Для MVP - порожній або тестовий)."""
        # В ідеалі треба робити запит до сервера, але для UI inventory_tab це має бути синхронно
        # Тому ми повертаємо те, що є в локальному кеші (якщо є) або пустий словник
        return {}

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

    def get_backgrounds(self):
        return ["Soldier", "Noble", "Criminal", "Sage", "Folk Hero", "Acolyte"]

    def get_starter_pack(self, char_class):
        keys = self.starter_packs.get(char_class, [])
        items = []
        for k in keys:
            if k in self.master_items:
                item = self.master_items[k].copy()
                item['id'] = str(uuid.uuid4())[:8]
                items.append(item)
        return items

    def get_spells_for_class(self, char_class):
        return self.spells_data.get(char_class, [])

    # Math
    def calculate_max_fatigue(self, hp):
        return min(int(hp * 1.5), 150)

    def get_potion_recovery(self, rarity):
        return "1d4" if rarity == "Common" else "1d8"

    def get_rest_recovery_formula(self, level):
        return f"{1 + (level // 4)}d4"

    # Server Logic
    def start_server(self):
        self.is_host = True
        thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False))
        thread.daemon = True
        thread.start()
        return socket.gethostbyname(socket.gethostname())

    def set_host_address(self, ip):
        self.server_url = f"http://{ip}:5000"

    def start_new_session(self):
        if not self.is_host: return None
        sid = "SESS_" + str(uuid.uuid4())[:4].upper()
        db_store["sessions"][sid] = {"status": "ACTIVE", "players": {}, "logs": [], "dm_id": self.user_id}
        self._current_session_id = sid
        return sid

    def join_session(self, connect_str):
        try:
            ip, sid = connect_str.split("/") if "/" in connect_str else ("127.0.0.1", connect_str)
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
        if self.is_host: return db_store["sessions"].get(sid, {}).get("dm_id")
        try:
            return requests.get(f"{self.server_url}/session/{sid}", timeout=1).json().get("dm_id")
        except:
            return None

    def save_character(self, data):
        if not self._current_session_id: return None
        if "conditions" not in data: data["conditions"] = {"physical_exhaustion": 0, "morale": 10}
        if "inventory" not in data: data["inventory"] = {}

        payload = {"sid": self._current_session_id, "uid": self.user_id, "player_data": data}
        try:
            if not self.server_url: self.server_url = "http://127.0.0.1:5000"
            requests.post(f"{self.server_url}/join", json=payload)
            return data
        except:
            return None

    def update_character_data(self, partial):
        if not self._current_session_id: return
        if self.is_host:
            db_store["sessions"][self._current_session_id]["players"][self.user_id].update(partial)
        else:
            requests.post(f"{self.server_url}/player/update",
                          json={"sid": self._current_session_id, "uid": self.user_id, "data": partial})

    def push_session_update(self, sid, content, type="MESSAGE", is_secret=False):
        log = {"type": type, "content": content, "timestamp": QDateTime.currentDateTime().toString("hh:mm"),
               "sender_id": self.user_id, "is_secret": is_secret}
        if self.is_host:
            db_store["sessions"][sid]["logs"].append(log)
        else:
            requests.post(f"{self.server_url}/update/logs", json={"sid": sid, "log": log})
        return True

    def subscribe_to_players(self, sid, cb):
        cb(self.get_session_players(sid))

    def grant_item_to_player(self, t, i):
        return True

    def save_item(self, d):
        return True

    def save_scenario_tree(self, d):
        return True