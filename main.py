import pygame
import sys
import random
import os
from PIL import Image  # Requires Pillow
import sys

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Constants
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 800
FPS = 60
PLAYER_SPEED = 7
FALLING_OBJECT_SPEED_MIN = 3
FALLING_OBJECT_SPEED_MAX = 7
SPAWN_INTERVAL = 1000  # in milliseconds

# Colors
WHITE = (255, 255, 255)
GREEN = (0, 200, 0)
RED = (200, 0, 0)
BLACK = (0, 0, 0)

WIN_SCORE = 25

# Custom event for a missed falling object
MISSED_EVENT = pygame.USEREVENT + 2

def load_sprite(path, fallback_size, fallback_color):
    """
    Tries to load an image from the given path.
    If the path is invalid or empty, returns a fallback surface.
    """
    if path and os.path.exists(path):
        try:
            image = pygame.image.load(path).convert_alpha()
            return image
        except Exception as e:
            print(f"Error loading image from {path}: {e}")
    # Create a fallback surface
    surface = pygame.Surface(fallback_size)
    surface.fill(fallback_color)
    return surface

class AnimatedGif:
    """
    Loads an animated GIF using Pillow and converts its frames to Pygame surfaces.
    The animation cycles through frames based on their duration.
    """
    def __init__(self, filename, scale=None):
        self.frames = []
        self.durations = []
        self.cumulative_durations = []
        total = 0
        try:
            im = Image.open(filename)
        except Exception as e:
            print(f"Error loading GIF from {filename}: {e}")
            return

        # Use the appropriate resampling filter:
        resample = getattr(Image, 'Resampling', Image).LANCZOS

        try:
            while True:
                d = im.info.get("duration", 100)  # duration in ms; default to 100
                total += d
                self.durations.append(d)
                self.cumulative_durations.append(total)
                frame = im.convert("RGBA")
                if scale:
                    frame = frame.resize(scale, resample)
                data = frame.tobytes()
                surface = pygame.image.fromstring(data, frame.size, "RGBA")
                self.frames.append(surface)
                im.seek(im.tell() + 1)
        except EOFError:
            pass

        self.total_duration = total
        self.start_time = pygame.time.get_ticks()

    def get_current_frame(self):
        if not self.frames:
            return None
        now = pygame.time.get_ticks()
        elapsed = (now - self.start_time) % self.total_duration
        for i, cum_d in enumerate(self.cumulative_durations):
            if elapsed < cum_d:
                return self.frames[i]
        return self.frames[-1]

class FloatingText:
    """A small text that appears, fades, and moves upward before disappearing."""
    def __init__(self, text, font, position, color=BLACK, duration=1000):
        self.text = text
        self.font = font
        self.initial_position = position  # center position
        self.color = color
        self.duration = duration  # milliseconds
        self.start_time = pygame.time.get_ticks()
        self.image = self.font.render(self.text, True, self.color)
        self.rect = self.image.get_rect(center=position)
        self.alpha = 255
        self.image.set_alpha(self.alpha)
        self.total_upward_movement = 30

    def update(self):
        elapsed = pygame.time.get_ticks() - self.start_time
        if elapsed >= self.duration:
            self.alpha = 0
        else:
            self.alpha = int(255 * (1 - elapsed / self.duration))
        self.image.set_alpha(self.alpha)
        upward_offset = int((elapsed / self.duration) * self.total_upward_movement)
        x, y = self.initial_position
        new_y = y - upward_offset
        self.rect = self.image.get_rect(center=(x, new_y))

    def is_dead(self):
        return self.alpha <= 0

    def draw(self, surface):
        surface.blit(self.image, self.rect)

class Player(pygame.sprite.Sprite):
    def __init__(self, image):
        super().__init__()
        self.original_image = pygame.transform.scale(image, (80, 80))
        self.image = self.original_image
        self.rect = self.image.get_rect()
        self.rect.midbottom = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 20)
        self.speed = PLAYER_SPEED
        self.eating_image = None
        self.eating_duration = 1000  
        self.eating_end_time = 0

    def set_eating_sprite(self, image):
        self.eating_image = pygame.transform.scale(image, (80, 80))

    def trigger_eating(self):
        self.eating_end_time = pygame.time.get_ticks() + self.eating_duration

    def update(self, keys_pressed):
        if keys_pressed[pygame.K_LEFT]:
            self.rect.x -= self.speed
        if keys_pressed[pygame.K_RIGHT]:
            self.rect.x += self.speed
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH
        if pygame.time.get_ticks() < self.eating_end_time and self.eating_image:
            self.image = self.eating_image
        else:
            self.image = self.original_image

class FallingObject(pygame.sprite.Sprite):
    def __init__(self, image):
        super().__init__()
        self.image = pygame.transform.scale(image, (50, 50))
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, SCREEN_WIDTH - self.rect.width)
        self.rect.y = -self.rect.height
        self.speed = random.randint(FALLING_OBJECT_SPEED_MIN, FALLING_OBJECT_SPEED_MAX)

    def update(self):
        self.rect.y += self.speed
        if self.rect.top > SCREEN_HEIGHT:
            event = pygame.event.Event(MISSED_EVENT, {"position": self.rect.center})
            pygame.event.post(event)
            self.kill()

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("BE MY VALENTINEEE :D")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)
    small_font = pygame.font.SysFont(None, 24)

    # Sprite paths
    player_path = resource_path("sprites/default.png")
    falling_path = resource_path("sprites/heart.png")
    eating_path = resource_path("sprites/noms.png") # eating sprite
    ending_image_path = resource_path("sprites/dog.gif")  # ending screen image/gif
    final_gif_path = resource_path("sprites/yippee.gif")  # final screen animated gif

    # Load sprites
    player_sprite = load_sprite(player_path, (80, 80), GREEN)
    falling_sprite = load_sprite(falling_path, (50, 50), RED)
    eating_sprite = load_sprite(eating_path, (80, 80), GREEN)
    
    if ending_image_path.lower().endswith('.gif'):
        ending_animation = AnimatedGif(ending_image_path, scale=(200, 200))
        ending_static = None
    else:
        ending_static = load_sprite(ending_image_path, (200, 200), (0, 0, 255))
        ending_animation = None

    # Load final animated gif for final screen.
    if final_gif_path.lower().endswith('.gif'):
        final_animation = AnimatedGif(final_gif_path, scale=(300, 300))
    else:
        final_animation = load_sprite(final_gif_path, (300, 300), (50, 50, 50))

    # Create sprite groups
    all_sprites = pygame.sprite.Group()
    falling_objects = pygame.sprite.Group()

    # Create the player sprite.
    player = Player(player_sprite)
    player.set_eating_sprite(eating_sprite)
    all_sprites.add(player)

    floating_texts = []

    SPAWN_EVENT = pygame.USEREVENT + 1
    pygame.time.set_timer(SPAWN_EVENT, SPAWN_INTERVAL)

    score = 0
    game_over = False
    final_screen = False  # becomes True after button click

    # Define the "click me!" button properties with rounded edges.
    button_width, button_height = 150, 50
    button_rect = pygame.Rect(0, 0, button_width, button_height)
    button_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 140)
    button_color = RED
    button_text = small_font.render("Yes :)", True, WHITE)

    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if not game_over:
                if event.type == SPAWN_EVENT:
                    falling_obj = FallingObject(falling_sprite)
                    all_sprites.add(falling_obj)
                    falling_objects.add(falling_obj)
                elif event.type == MISSED_EVENT:
                    pos = event.position
                    if pos[1] > SCREEN_HEIGHT - 50:
                        pos = (pos[0], SCREEN_HEIGHT - 50)
                    floating_texts.append(FloatingText("you hate me :(", small_font, pos, color=BLACK, duration=1000))
            elif game_over and not final_screen:
                # On ending screen, check for button click.
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if button_rect.collidepoint(event.pos):
                        final_screen = True
            if final_screen and event.type == pygame.KEYDOWN:
                pygame.quit()
                sys.exit()

        keys_pressed = pygame.key.get_pressed()
        if not game_over:
            player.update(keys_pressed)
            falling_objects.update()

            for falling_obj in falling_objects:
                if player.rect.colliderect(falling_obj.rect.inflate(20, 20)):
                    player.trigger_eating()
                    break

            hits = pygame.sprite.spritecollide(player, falling_objects, True)
            if hits:
                score += len(hits)

            if score >= WIN_SCORE:
                game_over = True
                falling_objects.empty()
                floating_texts.clear()

        for text in floating_texts[:]:
            text.update()
            if text.is_dead():
                floating_texts.remove(text)

        if not game_over:
            screen.fill(WHITE)
            all_sprites.draw(screen)
            for text in floating_texts:
                text.draw(screen)
            # Add a heart emoji to the score text.
            score_text = font.render(f"Ebby Love Captured <3: {score}", True, BLACK)
            screen.blit(score_text, (10, 10))
        else:
            if not final_screen:
                # Ending screen with ending image, text, and button.
                screen.fill(WHITE)
                if ending_animation:
                    ending_frame = ending_animation.get_current_frame()
                else:
                    ending_frame = ending_static
                if ending_frame:
                    ending_rect = ending_frame.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 150))
                    screen.blit(ending_frame, ending_rect)
                end_text = font.render("WOOOO you caught my love for u <3", True, BLACK)
                end_rect = end_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                screen.blit(end_text, end_rect)
                # Draw the "click me!" button with rounded edges.
                pygame.draw.rect(screen, button_color, button_rect, border_radius=15)
                btn_text_rect = button_text.get_rect(center=button_rect.center)
                screen.blit(button_text, btn_text_rect)
                prompt_text = small_font.render("WAIT, before you leave...Will you be my valentine? :3", True, BLACK)
                prompt_rect = prompt_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100))
                screen.blit(prompt_text, prompt_rect)
            else:
                # Final screen: display the final animated GIF centered with text below.
                screen.fill(WHITE)
                if final_animation and hasattr(final_animation, "get_current_frame"):
                    final_frame = final_animation.get_current_frame()
                else:
                    final_frame = final_animation
                if final_frame:
                    final_rect = final_frame.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
                    screen.blit(final_frame, final_rect)
                love_text = font.render("YAY!!!!!! WOOOOOOOOOOO", True, BLACK)
                love_rect = love_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 150))
                screen.blit(love_text, love_rect)
                exit_prompt = small_font.render("Press any key to exit", True, BLACK)
                exit_rect = exit_prompt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 50))
                screen.blit(exit_prompt, exit_rect)

        pygame.display.flip()

if __name__ == "__main__":
    main()
