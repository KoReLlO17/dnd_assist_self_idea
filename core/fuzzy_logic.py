import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl


class FuzzyLogic:
    """
    Система нечіткого виведення на базі бібліотеки scikit-fuzzy.
    Визначає 'Спіраль Смерті' через нечіткі правила.
    """

    # Лінгвістичні константи для UI
    RES_CRIT_FAIL = "💀 КРИТИЧНИЙ ПРОВАЛ"
    RES_FAIL_FORWARD = "❌ Провал з наслідками"
    RES_COSTLY_SUCCESS = "⚠️ Успіх з ускладненням"
    RES_SUCCESS = "✅ Чистий Успіх"
    RES_HARD_SUCCESS = "🔥 Впевнений Успіх"
    RES_CRIT_SUCCESS = "🌟 ЛЕГЕНДАРНО"

    # Зберігаємо систему, щоб не перебудовувати при кожному виклику
    _sim = None

    @classmethod
    def _init_fuzzy_system(cls):
        """Ініціалізація правил scikit-fuzzy (виконується один раз)."""
        if cls._sim is not None: return

        # --- 1. Змінні (Antecedents & Consequents) ---

        # Вхід: Відсоток ресурсу (0..100)
        # Ми фокусуємось на зоні 0-40%, бо там найцікавіше
        res_pct = ctrl.Antecedent(np.arange(0, 101, 1), 'resource_pct')

        # Вихід 1: Поріг Провалу (1..10)
        fumble_limit = ctrl.Consequent(np.arange(1, 11, 1), 'fumble_limit')

        # Вихід 2: DC Паніки (0..20)
        panic_dc = ctrl.Consequent(np.arange(0, 21, 1), 'panic_dc')

        # --- 2. Функції приналежності (Membership Functions) ---

        # Для Ресурсу:
        # "Смертельна небезпека" (0-5%)
        res_pct['deadly'] = fuzz.trapmf(res_pct.universe, [0, 0, 3, 5])
        # "Критичний стан" (3-15%) - використовуємо сигмоїду, що спадає (zmf)
        res_pct['critical'] = fuzz.trimf(res_pct.universe, [3, 10, 20])
        # "Ризик" (15-35%)
        res_pct['risky'] = fuzz.trimf(res_pct.universe, [15, 30, 45])
        # "Безпека" (35-100%) - сигмоїда, що зростає (smf)
        res_pct['safe'] = fuzz.smf(res_pct.universe, 30, 50)

        # Для Провалу (Fumble):
        fumble_limit['normal'] = fuzz.trimf(fumble_limit.universe, [1, 1, 1])  # Тільки 1
        fumble_limit['elevated'] = fuzz.trimf(fumble_limit.universe, [1, 3, 5])  # 1-3
        fumble_limit['extreme'] = fuzz.trapmf(fumble_limit.universe, [4, 8, 10, 10])  # 1-10

        # Для Паніки (DC):
        panic_dc['none'] = fuzz.trimf(panic_dc.universe, [0, 0, 5])
        panic_dc['medium'] = fuzz.trimf(panic_dc.universe, [5, 10, 15])
        panic_dc['high'] = fuzz.trapmf(panic_dc.universe, [10, 15, 20, 20])

        # --- 3. Правила (Rules) ---

        # Якщо Безпечно -> Провал 1, Паніки немає
        rule1 = ctrl.Rule(res_pct['safe'], (fumble_limit['normal'], panic_dc['none']))

        # Якщо Ризик -> Провал трохи вищий (2), Паніка середня (DC 5-10)
        rule2 = ctrl.Rule(res_pct['risky'], (fumble_limit['elevated'], panic_dc['medium']))

        # Якщо Критично -> Провал високий (3-5), Паніка висока (DC 15)
        rule3 = ctrl.Rule(res_pct['critical'], (fumble_limit['extreme'], panic_dc['high']))

        # Якщо Смертельно -> Провал екстремальний (до 10), Паніка максимальна
        rule4 = ctrl.Rule(res_pct['deadly'], (fumble_limit['extreme'], panic_dc['high']))

        # Створення системи контролю
        system = ctrl.ControlSystem([rule1, rule2, rule3, rule4])
        cls._sim = ctrl.ControlSystemSimulation(system)

    @staticmethod
    def calculate_game_state(hp, max_hp, fatigue, max_fatigue, morale, max_morale=20):
        # Ініціалізація системи при першому виклику
        FuzzyLogic._init_fuzzy_system()

        # 1. Підготовка даних
        hp_pct = (hp / max_hp) * 100 if max_hp > 0 else 0
        fat_pct = (1.0 - (fatigue / max_fatigue)) * 100 if max_fatigue > 0 else 0
        mor_pct = (morale / max_morale) * 100 if max_morale > 0 else 0

        # "Найслабша ланка"
        worst_pct = min(hp_pct, fat_pct, mor_pct)

        # Перевірка 0% (Absolute Fail)
        fail_condition = None
        if hp_pct <= 0:
            fail_condition = "DEAD"
        elif fat_pct <= 0:
            fail_condition = "FAINTED"
        elif mor_pct <= 0:
            fail_condition = "FLEEING"

        if fail_condition:
            return {
                "condition": fail_condition,
                "fumble_thresh": 20,
                "crit_thresh": 20,
                "status_text": f"❌ ВИБУВ ({fail_condition})",
                "worst_pct": 0.0,
                "panic_needed": True, "auto_fail": True, "panic_dc": 99
            }

        # 2. Обчислення через Scikit-Fuzzy
        try:
            FuzzyLogic._sim.input['resource_pct'] = worst_pct
            FuzzyLogic._sim.compute()

            # Отримання результатів (дефазифікація відбувається автоматично методом центроїда)
            calc_fumble = FuzzyLogic._sim.output['fumble_limit']
            calc_dc = FuzzyLogic._sim.output['panic_dc']

            # Округлення до ігрових цілих чисел
            fumble_range = max(1, int(round(calc_fumble)))
            panic_dc = int(round(calc_dc))

        except Exception as e:
            print(f"Fuzzy Error: {e}")
            fumble_range = 1
            panic_dc = 0

        # 3. Інтерпретація результатів
        panic_needed = False
        status_text = "Стабільний"

        if worst_pct <= 30:
            panic_needed = True
            status_text = f"⚠️ РИЗИК (DC {panic_dc})"

            if worst_pct <= 10:
                status_text = f"💀 КРИТИЧНО (Провал 1-{fumble_range})"

        return {
            "condition": "ACTIVE",
            "fumble_thresh": fumble_range,
            "crit_thresh": 20,
            "status_text": status_text,
            "worst_pct": round(worst_pct, 1),
            "panic_needed": panic_needed,
            "auto_fail": False,
            "panic_dc": panic_dc
        }

    @staticmethod
    def calculate_outcome(roll_val: int, modifier: int, fumble_range=1, crit_range=20):
        # Цей метод залишається стандартним для обробки кидка
        is_fumble = roll_val <= fumble_range
        is_crit = roll_val >= crit_range
        is_poor = roll_val <= 7
        is_avg = 8 <= roll_val <= 12
        is_bad_mod = modifier < 0
        is_ok_mod = 0 <= modifier <= 2
        is_good_mod = modifier > 2

        if is_fumble: return FuzzyLogic.RES_CRIT_FAIL, f"Провал (поріг {fumble_range})."
        if is_crit: return FuzzyLogic.RES_CRIT_SUCCESS, "Героїчно!"

        if is_good_mod:
            if is_poor: return FuzzyLogic.RES_COSTLY_SUCCESS, "Успіх з ускладненням."
            return FuzzyLogic.RES_SUCCESS, "Професійно."
        if is_ok_mod:
            if is_poor: return FuzzyLogic.RES_FAIL_FORWARD, "Провал, що рухає сюжет."
            if is_avg: return FuzzyLogic.RES_COSTLY_SUCCESS, "На межі."
            return FuzzyLogic.RES_SUCCESS, "Вдалося."
        if is_bad_mod:
            if is_poor: return FuzzyLogic.RES_FAIL_FORWARD, "Брак сил."
            if is_avg: return FuzzyLogic.RES_FAIL_FORWARD, "Майже..."
            return FuzzyLogic.RES_COSTLY_SUCCESS, "Дивом вдалося."

        return FuzzyLogic.RES_COSTLY_SUCCESS, "???"