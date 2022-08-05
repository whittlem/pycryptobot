from rich.table import Text


class RichText:
    @staticmethod
    def action_text(
        action: str = "WAIT"
    ) -> Text:
        if action == "":
            return None

        action_msg = f"Action: {action}"

        text = Text(action_msg)
        text.stylize("white", 0, 7)
        text.stylize("cyan", 8, len(action_msg))
        return text

    @staticmethod
    def last_action_text(
        action: str = "WAIT"
    ) -> Text:
        if action == "":
            return None

        action_msg = f"Last Action: {action}"

        text = Text(action_msg)
        text.stylize("white", 0, 12)
        text.stylize("cyan", 13, len(action_msg))
        return text

    @staticmethod
    def styled_text(
        input: str = "",
        color: str = "white",
        disabled: bool = False
    ) -> Text:
        if disabled or input == "":
            return None

        text = Text(input)
        text.stylize(color, 0, len(input))
        return text

    @staticmethod
    def bull_bear(
        golden_cross: bool = False,
        adjust_total_periods: int = 300
    ) -> Text:
        if adjust_total_periods < 200:
            return None

        if golden_cross:
            text = Text("BULL")
            text.stylize("green", 0, 4)
        else:
            text = Text("BEAR")
            text.stylize("red", 0, 4)
        return text

    @staticmethod
    def elder_ray(
        elder_ray_buy: bool = False,
        elder_ray_sell: bool = False,
        disabled: bool = False
    ) -> Text:
        if disabled:
            return None

        if elder_ray_buy:
            text = Text("Elder-Ray: buy")
            text.stylize("white", 0, 10)
            text.stylize("green", 11, 14)
        elif elder_ray_sell:
            text = Text("Elder-Ray: sell")
            text.stylize("white", 0, 10)
            text.stylize("red", 11, 15)
        else:
            return None

        return text

    @staticmethod
    def on_balance_volume(
        obv: float = 0.0,
        obv_pc: int = 0,
        disabled: bool = False
    ) -> Text:
        if disabled:
            return None

        obv_msg = f"OBV: {obv:.2f} ({obv_pc}%)"

        if obv >= 0:
            text = Text(obv_msg)
            text.stylize("white", 0, 4)
            text.stylize("green", 5, len(obv_msg))
        else:
            text = Text(f"OBV: {obv:.2f} ({obv_pc}%)")
            text.stylize("white", 0, 4)
            text.stylize("red", 5, len(obv_msg))

        return text

    @staticmethod
    def number_comparison(
        label: str = "",
        value1: float = 0.0,
        value2: float = 0.0,
        highlight: bool = False,
        disabled: bool = False
    ) -> Text:
        if disabled:
            return None

        color = "white"
        operator = "="
        if value1 > value2:
            if highlight:
                color = "white on green"
            else:
                color = "green"
            operator = ">"
        elif value1 < value2:
            if highlight:
                color = "white on red"
            else:
                color = "red"
            operator = "<"

        text = Text(f"{label} {value1} {operator} {value2}")
        text.stylize("white", 0, len(label))
        text.stylize(color, len(label) + 1, len(text))
        return text
