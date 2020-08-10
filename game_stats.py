class GameStats:
    """Отслеживание статистики для игры Alien Invasion."""

    def __init__(self, ai_game):
        """Иницифлизирует статитстику."""
        self.settings = ai_game.settings
        self.reset_stats()

        # Игра Alien Invasion запускается в неактивном состоянии.
        self.game_active = False
        try:
            with open('high_score.txt', 'r') as file:
                self.high_score = int(file.read())
        except FileNotFoundError:
            self.high_score = 0

    def reset_stats(self, reset_level=True):
        """Инициализирует статистику, изменяющуюся в ходе игры."""
        self.ships_left = self.settings.ship_limit
        self.score = 0
        if reset_level:
            self.level = 1
