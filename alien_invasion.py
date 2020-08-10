import sys
from time import sleep
import pygame

from settings import Settings
from game_stats import GameStats
from scoreboard import Scoreboard
from button import Button
from ship import Ship
from bullet import Bullet
from alien import Alien


class AlienInvasion:
    """Класс для управления рессурсами и поведением игры."""

    def __init__(self):
        """Инициализирует игру и создаёт игровые рессурсы."""
        pygame.init()
        self.settings = Settings()

        # self.screen = pygame.display.set_mode((self.settings.screen_width, self.settings.screen_height))
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.settings.screen_width = self.screen.get_rect().width
        self.settings.screen_height = self.screen.get_rect().height
        pygame.display.set_caption("Alien Invasion")

        # Создание экземпляров для хранения игровой статистики и панели результатов.
        self.stats = GameStats(self)
        self.sb = Scoreboard(self)

        self.ship = Ship(self)
        self.bullets = pygame.sprite.Group()
        self.aliens = pygame.sprite.Group()

        self._create_fleet()

        # Создание кнопок меню.
        self.play_button = Button(ai_game=self, msg="Play", position=0, color=(0, 180, 180))
        self._create_difficult_buttons()

        self.difficult_changed = False

    def _create_difficult_buttons(self):
        """Создаёт кнопки для выбора сложности"""
        self.difficult_easy_button = Button(ai_game=self, msg="EASY", position=1, color=self._get_button_color('EASY'))
        self.difficult_medium_button = Button(ai_game=self, msg="MEDIUM", position=2,
                                              color=self._get_button_color('MEDIUM'))
        self.difficult_hard_button = Button(ai_game=self, msg="HARD", position=3, color=self._get_button_color('HARD'))

    def _get_button_color(self, difficult):
        """Возвращает цвет для кнопки."""
        if difficult == self.settings.difficult:
            return self.settings.active_difficult_button_color
        return self.settings.difficult_button_color

    def _create_fleet(self):
        """Создание флота вторжения."""
        # Создание прищельца и вычисление количества пришельцев в ряду.
        # Интервал между соседними пришельцами равен ширине пришельца.
        alien = Alien(self)
        alien_width, alien_height = alien.rect.size
        available_space_x = self.settings.screen_width - 2 * alien_width
        number_aliens_x = available_space_x // (2 * alien_width)

        # Определяет количество рядов, помешающихся на экране.
        ship_height = self.ship.rect.height
        available_space_y = self.settings.screen_height - 3 * alien_height - ship_height
        number_rows = available_space_y // (2 * alien_height)

        # Создание первого ряда пришельцев.
        for row_number in range(number_rows):
            for alien_number in range(number_aliens_x):
                self._create_alien(row_number, alien_number, alien_width, alien_height)

    def _create_alien(self, row_number, alien_number, alien_width, alien_height):
        """Создание пришельца и размещение его в ряду."""
        alien = Alien(self)
        alien.x = alien_width + 2 * alien_width * alien_number
        alien.rect.x = alien.x
        alien.rect.y = alien_height + 2 * alien_height * row_number
        self.aliens.add(alien)

    def _check_fleet_edges(self):
        """Реагирует на достижение пришельцем края экрана."""
        for alien in self.aliens.sprites():
            if alien.check_edges():
                self._change_fleet_direction()
                break

    def _change_fleet_direction(self):
        """Опускает весь флот и меняет направление флота."""
        for alien in self.aliens.sprites():
            alien.rect.y += self.settings.fleet_drop_speed
        self.settings.fleet_direction *= -1

    def run_game(self):
        """Запуск основного цикла игры."""
        while True:
            self._check_events()

            if self.stats.game_active:
                self.ship.update()
                self._update_bullets()
                self._update_aliens()

            self._update_screen()

    def _update_bullets(self):
        """Обновляет позиции снарядов и уничтожает старые снаряды."""
        # Обновляет позиции снарядов.
        self.bullets.update()

        # Удаление снарядов, вышедших за край экрана.
        for bullet in self.bullets.copy():
            if bullet.rect.bottom <= 0:
                self.bullets.remove(bullet)

        self._check_bullet_alien_collisions()

    def _check_bullet_alien_collisions(self):
        """Обработка коллизий снарядов с пришельцами."""
        # Удаление снарядов и пришельцев, участвующих в коллизиях.
        collisions = pygame.sprite.groupcollide(self.bullets, self.aliens, True, True)
        if collisions:
            for alien in collisions.values():
                self.stats.score += self.settings.alien_points * len(alien)
            self.sb.prep_score()
            self.sb.check_high_score()

        if not self.aliens:
            # Уничтожение существующих снарядов и создание нового флота.
            self.bullets.empty()
            self._create_fleet()
            self._start_next_level()

    def _start_next_level(self):
        """Переопределение параметров для увеличения сложности."""
        self.settings.increase_speed()
        # Увеличение уровня.
        self.stats.level += 1
        self.sb.prep_level()

    def _update_aliens(self):
        """Проверяет, достиг ли флот края экрана, с последующим обновлением позиций всех пришельцев во флоте."""
        self._check_fleet_edges()
        self.aliens.update()

        # Проверка коллизий "пришелец - корабль".
        if pygame.sprite.spritecollide(self.ship, self.aliens, False):
            self._ship_hit()

        # Проверка добрались ли пришельцы до нижнего края экрана.
        self._check_aliens_bottom()

    def _check_events(self):
        """Обрабатывает нажатия кклавиш и события мыши."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._kill_the_game()
            elif event.type == pygame.KEYDOWN:
                self._check_keydown_events(event)
            elif event.type == pygame.KEYUP:
                self._check_keyup_events(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                self._check_button(mouse_pos)

    def _check_button(self, mouse_pos):
        """Запускает новую игру и изменяет сложность."""
        if not self.stats.game_active:
            play_button_clicked = self.play_button.rect.collidepoint(mouse_pos)
            difficult_easy_button_clicked = self.difficult_easy_button.rect.collidepoint(mouse_pos)
            difficult_medium_button_clicked = self.difficult_medium_button.rect.collidepoint(mouse_pos)
            difficult_hard_button_clicked = self.difficult_hard_button.rect.collidepoint(mouse_pos)
            if play_button_clicked:
                self._start_game()
            elif difficult_easy_button_clicked:
                self._change_difficult(difficult='EASY', level=0)
                self.sb.prep_level()
            elif difficult_medium_button_clicked:
                self._change_difficult(difficult='MEDIUM', level=3)
            elif difficult_hard_button_clicked:
                self._change_difficult(difficult='HARD', level=6)
            self._create_difficult_buttons()

    def _change_difficult(self, difficult, level):
        """Изменяет сложность игры"""
        self.settings.initialize_dynamic_settings()
        self.stats.reset_stats()
        self.difficult_changed = True
        for _ in range(level):
            self._start_next_level()
        self.settings.difficult = difficult

    def _start_game(self):
        """Начинает новый сеанс игры"""
        # Сброс игровой статистики.
        if self.difficult_changed:
            self.stats.reset_stats(reset_level=False)
            self.difficult_changed = False
        else:
            self.stats.reset_stats()
        self.stats.game_active = True
        self.sb.prep_score()
        self.sb.prep_level()
        self.sb.prep_ships()
        # Очистка списков пришельцев и снарядов.
        self.aliens.empty()
        self.bullets.empty()
        # Создание нового флота и размещение корабля в центре.
        self._create_fleet()
        self.ship.center_ship()
        # Указатель мыши скрывается
        pygame.mouse.set_visible(False)

    def _check_keyup_events(self, event):
        """Реагирует на отпускание клавиш."""
        if event.key == pygame.K_RIGHT:
            self.ship.moving_right = False
        elif event.key == pygame.K_LEFT:
            self.ship.moving_left = False

    def _check_keydown_events(self, event):
        """Реагирует на нажатие клавиш."""
        if event.key == pygame.K_RIGHT:
            self.ship.moving_right = True
        elif event.key == pygame.K_LEFT:
            self.ship.moving_left = True
        elif event.key == pygame.K_q:
            self._kill_the_game()
        elif event.key == pygame.K_SPACE:
            self._fire_bullet()
        elif event.key == pygame.K_p:
            if not self.stats.game_active:
                self._start_game()
        elif event.key == pygame.K_b:
            self._game_over()

    def _kill_the_game(self):
        """Завершение процесса игры"""
        with open('high_score.txt',  'w') as file:
            file.write(str(self.stats.high_score))
        sys.exit()

    def _fire_bullet(self):
        """Создание нового снаряда и включение его в группу bullets."""
        if len(self.bullets) < self.settings.bullet_allowed:
            new_bullet = Bullet(self)
            self.bullets.add(new_bullet)

    def _check_aliens_bottom(self):
        """Проверяет, добрались ли пришельцы до нижнего края экрана."""
        screen_rect = self.screen.get_rect()
        for alien in self.aliens.sprites():
            if alien.rect.bottom >= screen_rect.bottom:
                # Происходит то же, что при столкновении с кораблём.
                self._ship_hit()
                break

    def _ship_hit(self):
        """Обрабатывает столкновение корабля с пришельцем."""
        if self.stats.ships_left > 0:
            # Уменьшение ships_left и обновление панели счёта.
            self.stats.ships_left -= 1
            self.sb.prep_ships()

            # Очистка списков пришельцев и снарядов.
            self.aliens.empty()
            self.bullets.empty()

            # Создание нового флота и размещение корабля в центре.
            self._create_fleet()
            self.ship.center_ship()

            # Пауза
            sleep(0.5)
        else:
            self._game_over()

    def _game_over(self):
        """Конец игры"""
        self.stats.game_active = False
        # Сброс игровых настроек скорости игры.
        self.settings.initialize_dynamic_settings()
        pygame.mouse.set_visible(True)

    def _update_screen(self):
        """Обновляет изображения на экране и отображает новый экран"""
        self.screen.fill(self.settings.bg_color)
        self.ship.blitme()
        for bullet in self.bullets.sprites():
            bullet.draw_bullet()
        self.aliens.draw(self.screen)

        # Вывод информации о счёте.
        self.sb.show_score()

        # Кнопка Play и кнопки выбора сложности отображаются в том случае, если игра не активна
        if not self.stats.game_active:
            self.play_button.draw_button()
            self.difficult_easy_button.draw_button()
            self.difficult_medium_button.draw_button()
            self.difficult_hard_button.draw_button()

        pygame.display.flip()


if __name__ == '__main__':
    # Создание экземпляра и запуск игры.
    ai = AlienInvasion()
    ai.run_game()
