"""
Mineflow 2D real time strategy game
"""
import arcade
import random

# Constants # 1920x1080
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = int(SCREEN_WIDTH * 9 / 16)
SCREEN_TITLE = "Mineflow"

# Constants used to scale our sprites from their original size
TILE_SCALING = 0.5
CHARACTER_SCALING = TILE_SCALING

MAP_WIDTH = 30
MAP_HEIGHT = 30
BORDER = 2
MAP_SURFACE = MAP_HEIGHT - BORDER - 9
HALF_TILE = 64 * TILE_SCALING
FULL_TILE = HALF_TILE * 2

DIG_TIME = 0.2


def x_to_px(x):
    return x * FULL_TILE + HALF_TILE


def y_to_px(y):
    return y * FULL_TILE + HALF_TILE


def px_to_x(px):
    return int(px/FULL_TILE)


def px_to_y(px):
    return int(px/FULL_TILE)


# Movement speed of player, in pixels per frame
PLAYER_MOVEMENT_SPEED = 5
GRAVITY = 1
PLAYER_JUMP_SPEED = 25

# How many pixels to keep as a minimum margin between the character
# and the edge of the screen.
LEFT_VIEWPORT_MARGIN = BORDER * FULL_TILE
RIGHT_VIEWPORT_MARGIN = BORDER * FULL_TILE
BOTTOM_VIEWPORT_MARGIN = BORDER * FULL_TILE
TOP_VIEWPORT_MARGIN = BORDER * FULL_TILE


class Tile:
    def __init__(self, kind, x, y):
        self.kind = kind
        self.hp = 4
        resource = ":resources:images/tiles/grassCenter.png"  # light_earth
        if kind == "stone":
            resource = ":resources:images/tiles/stoneCenter.png"
        if kind == "surface":
            resource = ":resources:images/tiles/grassMid.png"
            self.hp = 2
        if kind == "earth":
            resource = "images/earth.png"
            self.hp = 6
        if kind == "gold":
            resource = "images/gold.png"
            self.hp = 500
        self.sprite = arcade.Sprite(resource, TILE_SCALING)
        self.sprite.center_x = x_to_px(x)
        self.sprite.center_y = y_to_px(y)

    def can_dig(self):
        return self.kind != "stone"

    def is_gold(self):
        return self.kind == "gold"

    def dig(self):
        self.hp -= 1
        return self.hp <= 0


class MenuView(arcade.View):
    def on_show(self):
        arcade.set_background_color(arcade.color.WHITE)

    def on_draw(self):
        arcade.start_render()
        arcade.draw_text("Instructions", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + 150,
                         arcade.color.BLACK, font_size=40, anchor_x="center")
        arcade.draw_text("W - jump\nA - move/dig left\nD - move/dig right\nS - dig down\nF - full screen", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 50,
                         arcade.color.BLACK, font_size=20, anchor_x="center", align="center")
        arcade.draw_text("Click to start", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 150,
                         arcade.color.BLACK, font_size=30, anchor_x="center")

    def on_mouse_press(self, _x, _y, _button, _modifiers):
        game_view = GameView()
        game_view.setup()
        self.window.show_view(game_view)


class GameView(arcade.View):
    """
    Main game view.
    """

    def __init__(self):
        super().__init__()

        # These are 'lists' that keep track of our sprites. Each sprite should
        # go into a list.
        self.wall_list = None
        self.player_list = None
        self.tiles = [[None for y in range(MAP_HEIGHT)] for x in range(MAP_WIDTH)]

        # Separate variable that holds the player sprite
        self.player_sprite = None

        # Our physics engine
        self.physics_engine = None

        # Used to keep track of our scrolling
        self.view_bottom = 0
        self.view_left = 0

        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False
        self.digging = "no"

        self.dig_pause = 0
        self.gold = 100

        self.jump_sound = arcade.load_sound(":resources:sounds/jump1.wav")
        self.cannot_dig_sound = arcade.load_sound(":resources:sounds/error3.wav")
        self.dig_sound = arcade.load_sound(":resources:sounds/rockHit2.wav")
        self.gold_sound = arcade.load_sound(":resources:sounds/coin5.wav")
        self.success_dig_sound = arcade.load_sound(":resources:sounds/hit3.wav")

        self.background = None
        arcade.set_background_color(arcade.csscolor.BLACK)

    def setup(self):
        """ Set up the game here. Call this function to restart the game. """

        random.seed(30)

        self.gold = 100

        self.background = arcade.load_texture(":resources:images/backgrounds/abstract_2.jpg")

        self.player_list = arcade.SpriteList()
        self.wall_list = arcade.SpriteList()

        image_source = ":resources:images/animated_characters/robot/robot_idle.png"
        self.player_sprite = arcade.Sprite(image_source, CHARACTER_SCALING)
        self.player_sprite.center_x = x_to_px(3)
        self.player_sprite.center_y = y_to_px(MAP_SURFACE + 1)
        self.player_list.append(self.player_sprite)

        for x in range(0, MAP_WIDTH):
            for y in range(0, MAP_HEIGHT):
                if x < BORDER or x >= MAP_WIDTH - BORDER or y < BORDER or y >= MAP_HEIGHT - BORDER:
                    self.add_tile(x, y, "stone")
                elif y == MAP_SURFACE:
                    self.add_tile(x, y, "surface")
                elif y < MAP_SURFACE:
                    if y > MAP_SURFACE - 2:
                        self.add_tile(x, y)
                    elif random.randint(1, 8) == 1:
                        self.add_tile(x, y, "light earth")
                    elif random.randint(1, 8) == 1:
                        self.add_tile(x, y, "stone")
                    elif y < MAP_SURFACE - 8 and random.randint(1, 8) == 1:
                        self.add_tile(x, y, "gold")
                    elif random.randint(1, 8) > 1:
                        self.add_tile(x, y, "earth")

        self.physics_engine = arcade.PhysicsEnginePlatformer(self.player_sprite, self.wall_list, GRAVITY)

    def add_tile(self, x, y, kind="light earth"):
        tile = Tile(kind, x, y)
        self.tiles[x][y] = tile
        self.wall_list.append(tile.sprite)

    def remove_tile(self, x, y):
        tile = self.tiles[x][y]
        tile.sprite.remove_from_sprite_lists()
        self.tiles[x][y] = None

    def try_digging(self, x, y):
        if self.tiles[x][y] is not None:
            tile = self.tiles[x][y]
            if tile.can_dig():
                if tile.dig():
                    self.remove_tile(x, y)
                    arcade.play_sound(self.success_dig_sound)
                elif tile.is_gold():
                    self.gold += 1
                    arcade.play_sound(self.gold_sound)
                else:
                    arcade.play_sound(self.dig_sound)
            else:
                arcade.play_sound(self.cannot_dig_sound)

    def on_draw(self):
        """ Render the screen. """

        # Clear the screen to the background color
        arcade.start_render()

        arcade.draw_lrwh_rectangle_textured(self.view_left, self.view_bottom,
                                            SCREEN_WIDTH, SCREEN_HEIGHT, self.background)

        # Draw our sprites
        self.wall_list.draw()
        self.player_list.draw()

        x = px_to_x(self.player_sprite.center_x)
        y = px_to_y(self.player_sprite.center_y)
        arcade.draw_rectangle_outline(x_to_px(x), y_to_px(y), FULL_TILE, FULL_TILE, arcade.csscolor.GRAY)

    def process_key_change(self):
        """
        Called when we change a key up/down or we move on/off a ladder.
        """
        if self.up_pressed and not self.down_pressed:
            if self.physics_engine.can_jump():
                self.player_sprite.change_y = PLAYER_JUMP_SPEED
                arcade.play_sound(self.jump_sound)

        self.digging = "no"

        if self.right_pressed and not self.left_pressed:
            self.player_sprite.change_x = PLAYER_MOVEMENT_SPEED
            self.digging = "right"
        elif self.left_pressed and not self.right_pressed:
            self.player_sprite.change_x = -PLAYER_MOVEMENT_SPEED
            self.digging = "left"
        else:
            self.player_sprite.change_x = 0

        if self.down_pressed:
            self.digging = "down"

    def on_key_press(self, key, modifiers):
        """Called whenever a key is pressed. """

        if key == arcade.key.UP or key == arcade.key.W:
            self.up_pressed = True
        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.down_pressed = True
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = True
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = True

        self.process_key_change()

        if key == arcade.key.F:
            self.window.set_fullscreen(not self.window.fullscreen)
            width, height = self.window.get_size()
            self.window.set_viewport(0, width, 0, height)
            self.do_scrolling()

    def on_key_release(self, key, modifiers):
        """Called when the user releases a key. """

        if key == arcade.key.UP or key == arcade.key.W:
            self.up_pressed = False
        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.down_pressed = False
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = False
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = False

        self.process_key_change()

    def on_update(self, delta_time):
        """ Movement and game logic """

        # Move the player with the physics engine
        self.physics_engine.update()

        self.dig_pause -= delta_time

        if self.digging != "no" and self.dig_pause < 0:
            self.dig_pause = DIG_TIME
            x = px_to_x(self.player_sprite.center_x)
            y = px_to_y(self.player_sprite.center_y)
            if self.digging == "down":
                self.try_digging(x, y - 1)
            if self.digging == "left":
                self.try_digging(x - 1, y)
            if self.digging == "right":
                self.try_digging(x + 1, y)

        # --- Manage Scrolling ---

        # Track if we need to change the viewport

        changed = False

        # Scroll left
        left_boundary = self.view_left + LEFT_VIEWPORT_MARGIN
        if self.player_sprite.left < left_boundary:
            self.view_left -= left_boundary - self.player_sprite.left
            changed = True

        # Scroll right
        right_boundary = self.view_left + SCREEN_WIDTH - RIGHT_VIEWPORT_MARGIN
        if self.player_sprite.right > right_boundary:
            self.view_left += self.player_sprite.right - right_boundary
            changed = True

        # Scroll up
        top_boundary = self.view_bottom + SCREEN_HEIGHT - TOP_VIEWPORT_MARGIN
        if self.player_sprite.top > top_boundary:
            self.view_bottom += self.player_sprite.top - top_boundary
            changed = True

        # Scroll down
        bottom_boundary = self.view_bottom + BOTTOM_VIEWPORT_MARGIN
        if self.player_sprite.bottom < bottom_boundary:
            self.view_bottom -= bottom_boundary - self.player_sprite.bottom
            changed = True

        if changed:
            self.do_scrolling()

    def do_scrolling(self):
        self.view_bottom = int(self.view_bottom)
        self.view_left = int(self.view_left)
        arcade.set_viewport(self.view_left,  SCREEN_WIDTH + self.view_left,
                            self.view_bottom, SCREEN_HEIGHT + self.view_bottom)


def main():
    """ Main method """
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    menu_view = MenuView()
    window.show_view(menu_view)
    arcade.run()


if __name__ == "__main__":
    main()
