import pygame
import sys
import random
import os
from PIL import Image  # Requires Pillow

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
                # Get frame duration in milliseconds; default to 100 if not specified.
                d = im.info.get("duration", 100)
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
        # Save the initial position (center)
        self.initial_position = position
        self.color = color
        self.duration = duration  # milliseconds
        self.start_time = pygame.time.get_ticks()
        self.image = self.font.render(self.text, True, self.color)
        self.rect = self.image.get_rect(center=position)
        self.alpha = 255
        self.image.set_alpha(self.alpha)
        # Total upward movement in pixels during the entire duration.
        self.total_upward_movement = 30

    def update(self):
        elapsed = pygame.time.get_ticks() - self.start_time
        # Update alpha for fading effect.
        if elapsed >= self.duration:
            self.alpha = 0
        else:
            self.alpha = int(255 * (1 - elapsed / self.duration))
        self.image.set_alpha(self.alpha)
        # Calculate upward movement: as time passes, move upward.
        upward_offset = int((elapsed / self.duration) * self.total_upward_movement)
        # Update position: subtract upward_offset from the original y position.
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
        # Save and scale the original image
        self.original_image = pygame.transform.scale(image, (80, 80))
        self.image = self.original_image
        self.rect = self.image.get_rect()
        self.rect.midbottom = (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 20)
        self.speed = PLAYER_SPEED
        
        # Prepare eating sprite (to be set later)
        self.eating_image = None
        
        # Duration (in milliseconds) for which the eating sprite should persist
        self.eating_duration = 1000  
        self.eating_end_time = 0

    def set_eating_sprite(self, image):
        """Set the eating sprite image."""
        self.eating_image = pygame.transform.scale(image, (80, 80))

    def trigger_eating(self):
        """Trigger the eating sprite to persist for a set duration."""
        self.eating_end_time = pygame.time.get_ticks() + self.eating_duration

    def update(self, keys_pressed):
        # Update movement
        if keys_pressed[pygame.K_LEFT]:
            self.rect.x -= self.speed
        if keys_pressed[pygame.K_RIGHT]:
            self.rect.x += self.speed

        # Keep the player within screen bounds
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH

        # Update the sprite based on the eating timer.
        if pygame.time.get_ticks() < self.eating_end_time and self.eating_image:
            self.image = self.eating_image
        else:
            self.image = self.original_image

class FallingObject(pygame.sprite.Sprite):
    def __init__(self, image):
        super().__init__()
        # Scale image to a standard size (adjust as needed)
        self.image = pygame.transform.scale(image, (50, 50))
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, SCREEN_WIDTH - self.rect.width)
        self.rect.y = -self.rect.height
        self.speed = random.randint(FALLING_OBJECT_SPEED_MIN, FALLING_OBJECT_SPEED_MAX)

    def update(self):
        self.rect.y += self.speed
        # If the object goes off the bottom, post a MISSED_EVENT and remove it.
        if self.rect.top > SCREEN_HEIGHT:
            event = pygame.event.Event(MISSED_EVENT, {"position": self.rect.center})
            pygame.event.post(event)
            self.kill()

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Catcher Game")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 36)
    # A smaller font for floating text.
    small_font = pygame.font.SysFont(None, 24)

    # Sprite paths
    player_path = "./sprites/default.png" 
    falling_path = "./sprites/heart.png" 
    eating_path = "./sprites/noms.png"  # corrected path for eating sprite

    # Path for the ending image.
    # Change the filename extension to .gif if you want to use an animated GIF.
    ending_image_path = "./sprites/dog.gif"  

    # Load sprites (using fallback sizes and colors if needed)
    player_sprite = load_sprite(player_path, (80, 80), GREEN)
    falling_sprite = load_sprite(falling_path, (50, 50), RED)
    eating_sprite = load_sprite(eating_path, (80, 80), GREEN)
    
    # For the ending image, check if it is a GIF. If so, use AnimatedGif.
    if ending_image_path.lower().endswith('.gif'):
        ending_animation = AnimatedGif(ending_image_path, scale=(200, 200))
        ending_static = None
    else:
        ending_static = load_sprite(ending_image_path, (200, 200), (0, 0, 255))
        ending_animation = None

    # Create sprite groups
    all_sprites = pygame.sprite.Group()
    falling_objects = pygame.sprite.Group()

    # Create player instance, set its eating sprite, and add it to the group.
    player = Player(player_sprite)
    player.set_eating_sprite(eating_sprite)
    all_sprites.add(player)

    # List to store active floating texts.
    floating_texts = []

    # Set a timer to spawn falling objects.
    SPAWN_EVENT = pygame.USEREVENT + 1
    pygame.time.set_timer(SPAWN_EVENT, SPAWN_INTERVAL)

    score = 0
    game_over = False

    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            # Process events only if the game is not over.
            if not game_over:
                if event.type == SPAWN_EVENT:
                    falling_obj = FallingObject(falling_sprite)
                    all_sprites.add(falling_obj)
                    falling_objects.add(falling_obj)
                elif event.type == MISSED_EVENT:
                    pos = event.position
                    # Clamp the y coordinate if needed so it appears on-screen.
                    if pos[1] > SCREEN_HEIGHT - 50:
                        pos = (pos[0], SCREEN_HEIGHT - 50)
                    floating_texts.append(FloatingText("you hate me :(", small_font, pos, color=BLACK, duration=1000))
            # When game is over, allow any key press to exit.
            if game_over and event.type == pygame.KEYDOWN:
                pygame.quit()
                sys.exit()

        keys_pressed = pygame.key.get_pressed()

        if not game_over:
            player.update(keys_pressed)
            falling_objects.update()

            # Check if any falling object is near the player.
            for falling_obj in falling_objects:
                if player.rect.colliderect(falling_obj.rect.inflate(20, 20)):
                    player.trigger_eating()
                    break

            # Check for actual collisions (object caught).
            hits = pygame.sprite.spritecollide(player, falling_objects, True)
            if hits:
                score += len(hits)

            # Once the score reaches 25, trigger game over.
            if score >= 1:
                game_over = True
                # Clear sprites and texts to show the ending screen.
                falling_objects.empty()
                floating_texts.clear()

        # Update floating texts.
        for text in floating_texts[:]:
            text.update()
            if text.is_dead():
                floating_texts.remove(text)

        # Drawing.
        screen.fill(WHITE)
        if not game_over:
            all_sprites.draw(screen)
            for text in floating_texts:
                text.draw(screen)
            score_text = font.render(f"Score: {score}", True, BLACK)
            screen.blit(score_text, (10, 10))
        else:
            # Ending screen:
            # Get the current ending frame.
            if ending_animation:
                ending_frame = ending_animation.get_current_frame()
            else:
                ending_frame = ending_static
            if ending_frame:
                ending_rect = ending_frame.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 150))
                screen.blit(ending_frame, ending_rect)
            # Game over text below the image.
            end_text = font.render("Game Over! You Win!", True, BLACK)
            end_rect = end_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(end_text, end_rect)
            final_score_text = font.render(f"Final Score: {score}", True, BLACK)
            score_rect = final_score_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40))
            screen.blit(final_score_text, score_rect)
            prompt_text = small_font.render("Press any key to exit", True, BLACK)
            prompt_rect = prompt_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80))
            screen.blit(prompt_text, prompt_rect)

        pygame.display.flip()

if __name__ == "__main__":
    main()
