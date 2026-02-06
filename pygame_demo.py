#!/usr/bin/env python3
"""
Simple Pygame Demo - A bouncing ball with keyboard controls.
Use arrow keys to control the ball, SPACE to change color, ESC to quit.
"""

import pygame
import random
import sys

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60
BALL_RADIUS = 20
PADDLE_WIDTH = 100
PADDLE_HEIGHT = 10

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
PURPLE = (255, 0, 255)
CYAN = (0, 255, 255)

class Ball:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.choice([-5, 5])
        self.vy = random.choice([-5, 5])
        self.radius = BALL_RADIUS
        self.color = WHITE
        self.trail = []
        
    def update(self):
        # Add current position to trail
        self.trail.append((self.x, self.y))
        if len(self.trail) > 10:
            self.trail.pop(0)
        
        # Update position
        self.x += self.vx
        self.y += self.vy
        
        # Bounce off walls
        if self.x - self.radius <= 0 or self.x + self.radius >= SCREEN_WIDTH:
            self.vx = -self.vx
            self.x = max(self.radius, min(SCREEN_WIDTH - self.radius, self.x))
            
        if self.y - self.radius <= 0 or self.y + self.radius >= SCREEN_HEIGHT:
            self.vy = -self.vy
            self.y = max(self.radius, min(SCREEN_HEIGHT - self.radius, self.y))
    
    def draw(self, screen):
        # Draw trail
        for i, pos in enumerate(self.trail):
            alpha = i * 25
            color = (*self.color, alpha) if len(self.color) == 3 else self.color
            pygame.draw.circle(screen, color[:3], (int(pos[0]), int(pos[1])), 
                             self.radius // 2 + i // 2)
        
        # Draw ball
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), self.radius, 2)
    
    def change_color(self):
        colors = [RED, GREEN, BLUE, YELLOW, PURPLE, CYAN, WHITE]
        self.color = random.choice(colors)
    
    def control(self, keys):
        # Arrow key controls
        if keys[pygame.K_LEFT]:
            self.vx -= 0.5
        if keys[pygame.K_RIGHT]:
            self.vx += 0.5
        if keys[pygame.K_UP]:
            self.vy -= 0.5
        if keys[pygame.K_DOWN]:
            self.vy += 0.5
        
        # Limit speed
        max_speed = 10
        self.vx = max(-max_speed, min(max_speed, self.vx))
        self.vy = max(-max_speed, min(max_speed, self.vy))

class Paddle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = PADDLE_WIDTH
        self.height = PADDLE_HEIGHT
        self.color = GREEN
        
    def update(self, mouse_x):
        self.x = mouse_x - self.width // 2
        self.x = max(0, min(SCREEN_WIDTH - self.width, self.x))
    
    def draw(self, screen):
        pygame.draw.rect(screen, self.color, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(screen, WHITE, (self.x, self.y, self.width, self.height), 2)
    
    def check_collision(self, ball):
        if (ball.y + ball.radius >= self.y and 
            ball.y - ball.radius <= self.y + self.height and
            ball.x >= self.x and 
            ball.x <= self.x + self.width):
            ball.vy = -abs(ball.vy)
            return True
        return False

def main():
    # Set up the display
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Pygame Demo - Bouncing Ball")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 36)
    small_font = pygame.font.Font(None, 24)
    
    # Create game objects
    ball = Ball(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
    paddle = Paddle(SCREEN_WIDTH // 2 - PADDLE_WIDTH // 2, SCREEN_HEIGHT - 50)
    
    # Game variables
    score = 0
    running = True
    show_instructions = True
    instruction_timer = 180  # Show instructions for 3 seconds
    
    while running:
        # Handle events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    ball.change_color()
                elif event.key == pygame.K_r:
                    # Reset ball position
                    ball = Ball(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
                elif event.key == pygame.K_h:
                    # Toggle instructions
                    show_instructions = not show_instructions
                    instruction_timer = 180
        
        # Get keyboard state
        keys = pygame.key.get_pressed()
        
        # Update game objects
        ball.control(keys)
        ball.update()
        
        # Update paddle with mouse
        mouse_x, mouse_y = pygame.mouse.get_pos()
        paddle.update(mouse_x)
        
        # Check collision
        if paddle.check_collision(ball):
            score += 10
        
        # Clear screen
        screen.fill(BLACK)
        
        # Draw game objects
        ball.draw(screen)
        paddle.draw(screen)
        
        # Draw UI
        score_text = font.render(f"Score: {score}", True, WHITE)
        screen.blit(score_text, (10, 10))
        
        # Draw instructions
        if show_instructions and instruction_timer > 0:
            instructions = [
                "Arrow Keys: Control ball",
                "SPACE: Change color", 
                "R: Reset ball",
                "H: Toggle help",
                "ESC: Quit"
            ]
            y_offset = 50
            for instruction in instructions:
                text = small_font.render(instruction, True, WHITE)
                screen.blit(text, (SCREEN_WIDTH - 250, y_offset))
                y_offset += 25
            instruction_timer -= 1
        
        # Draw FPS
        fps_text = small_font.render(f"FPS: {int(clock.get_fps())}", True, WHITE)
        screen.blit(fps_text, (10, 50))
        
        # Update display
        pygame.display.flip()
        clock.tick(FPS)
    
    # Quit
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
