import random
import re


class DiceLogic:
    """
    Клас для обробки кидків кубиків.
    Підтримує формули типу '1d20+5', '2d6', '1d8-1'.
    """

    @staticmethod
    def roll(formula: str):
        """
        Парсить формулу та повертає результат і деталі.
        Повертає: (total, details_string)
        """
        formula = formula.lower().replace(" ", "")

        # Регулярка для пошуку патернів: XdY+Z
        match = re.match(r"(\d*)d(\d+)([+-]\d+)?", formula)

        if not match:
            # Якщо це просто число
            try:
                return int(formula), f"Flat {formula}"
            except:
                return 0, "Error"

        count_str, die_str, mod_str = match.groups()

        count = int(count_str) if count_str else 1
        die = int(die_str)
        mod = int(mod_str) if mod_str else 0

        rolls = [random.randint(1, die) for _ in range(count)]
        total = sum(rolls) + mod

        # Формування красивого рядка деталей: [5, 2] + 3
        rolls_str = ", ".join(map(str, rolls))
        mod_display = f" {'+' if mod >= 0 else '-'} {abs(mod)}" if mod != 0 else ""

        details = f"[{rolls_str}]{mod_display} (d{die})"

        return total, details