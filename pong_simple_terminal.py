import pygame
import random
from neurofly import UDPClientListener, DEFAULT_UDP_PORT

# Shared paddle command from UDP EMG input: -1 (up), +1 (down), 0 (none)
cmd = 0
GAME_DURATION = 40  # seconds
EMG_UP_THRESHOLD = 0.15  # Threshold to trigger movement
EMG_DOWN_THRESHOLD = 0.05  # Threshold to trigger movement

def emg_joystick_callback(packet, addr):
    """UDP callback: extract EMG joystick X and map to paddle direction."""
    global cmd
    if packet.get("type") == "emgJoystick" and isinstance(packet.get("data"), list):
        data = packet["data"]
        # print(f"EMG Joystick Data: {data} from {addr}")
        if len(data) >= 1:
            emg_y = data[1]
            # print(f"EMG Joystick Y: {emg_y} from {addr}")
            # If y > threshold, move up (cmd = -1); if y < -threshold, move down (cmd = +1)
            if emg_y > EMG_DOWN_THRESHOLD:
                cmd = -1
            elif emg_y < -EMG_DOWN_THRESHOLD:
                cmd = +1
            else:
                cmd = 0

def countdown_sequence(screen, W, H, large_font, listener):
    """Wait for Space key press, then display countdown sequence before game starts."""
    # Wait for Space key to start countdown
    waiting = True
    while waiting:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                listener.stop()
                return False  # Signal to exit
            if e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE:
                # Space pressed: start countdown
                waiting = False
                break
        
        screen.fill((0, 0, 0))
        start_text = large_font.render("Press SPACE to Start", True, (255, 255, 255))
        screen.blit(start_text, (W // 2 - start_text.get_width() // 2, H // 2 - start_text.get_height() // 2))
        pygame.display.flip()
        pygame.time.delay(100)  # Small delay to prevent excessive CPU usage
    
    # Countdown sequence
    countdown = 3
    countdown_clock = pygame.time.Clock()
    while countdown > 0:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                listener.stop()
                return False  # Signal to exit
        
        screen.fill((0, 0, 0))
        countdown_text = large_font.render(str(countdown), True, (255, 255, 255))
        screen.blit(countdown_text, (W // 2 - countdown_text.get_width() // 2, H // 2 - countdown_text.get_height() // 2))
        pygame.display.flip()
        countdown_clock.tick(1)  # 1 FPS, so each frame is 1 second
        countdown -= 1
    
    # Show "GO!" message
    screen.fill((0, 0, 0))
    go_text = large_font.render("GO!", True, (255, 255, 255))
    screen.blit(go_text, (W // 2 - go_text.get_width() // 2, H // 2 - go_text.get_height() // 2))
    pygame.display.flip()
    pygame.time.delay(1000)  # Show GO for 1 second
    return True  # Signal to continue

def game_over_screen(screen, W, H, score, font, large_font, clock):
    """Display game over screen and wait for window close."""
    game_over = True
    while game_over:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                game_over = False
        
        screen.fill((0, 0, 0))
        
        # Draw "GAME OVER" text
        game_over_text = large_font.render("GAME OVER", True, (255, 0, 0))
        screen.blit(game_over_text, (W // 2 - game_over_text.get_width() // 2, H // 2 - 100))
        
        # Draw final score
        final_score_text = font.render(f"Final Score: {score}", True, (255, 255, 255))
        screen.blit(final_score_text, (W // 2 - final_score_text.get_width() // 2, H // 2))
        
        pygame.display.flip()
        clock.tick(60)

def main():
    global cmd

    # Start UDP listener in the background
    listener = UDPClientListener(listen_port=DEFAULT_UDP_PORT)
    listener.set_callback(emg_joystick_callback)
    print(f"Starting pong with EMG joystick input on port {DEFAULT_UDP_PORT}")
    listener.start()

    pygame.init()
    W, H = 800, 500
    screen = pygame.display.set_mode((W, H))
    clock = pygame.time.Clock()

    paddle = pygame.Rect(30, H // 2 - 50, 12, 100)
    ball_radius = 8
    ball = pygame.Rect(W // 2 - ball_radius, H // 2 - ball_radius, ball_radius * 2, ball_radius * 2)
    vx, vy = random.choice([-6, 6]), random.uniform(-4, 4)

    score = 0
    font = pygame.font.Font(None, 36)
    large_font = pygame.font.Font(None, 72)

    STEP = 5  # how much the paddle moves per frame when EMG is active

    # Run countdown sequence
    if not countdown_sequence(screen, W, H, large_font, listener):
        return

    # Game timer
    start_time = pygame.time.get_ticks()  # Get start time in milliseconds

    try:
        running = True
        exited_by_quit = False
        while running:
            # Check if game time has exceeded duration
            elapsed_time = (pygame.time.get_ticks() - start_time) / 1000  # Convert to seconds
            remaining_time = max(0, GAME_DURATION - elapsed_time)
            
            if remaining_time <= 0:
                running = False
                break

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    # Mark that the user requested quit so we skip the game-over screen
                    exited_by_quit = True
                    running = False

            # Apply continuous movement based on EMG input
            if cmd != 0:
                paddle.y += cmd * STEP
                # Do not reset cmd here; it persists until EMG input changes
                if paddle.y < 0:
                    paddle.y = 0
                if paddle.y > H - paddle.height:
                    paddle.y = H - paddle.height

            # Ball movement
            ball.x += vx
            ball.y += vy

            if ball.top <= 0 or ball.bottom >= H:
                vy *= -1
                # Add randomness to prevent predictable bounces
                vx += random.uniform(-0.01, 0.01)

            if ball.left <= 0 or ball.right >= W:
                vx *= -1
                # Add randomness to vertical velocity on reset
                vy += random.uniform(-0.01, 0.01)

            if ball.colliderect(paddle) and vx < 0:
                vx *= -1
                score += 1  # Increment score when paddle hits ball
                print(f"Paddle hit! Score: {score}")

            # Draw
            screen.fill((0, 0, 0))
            pygame.draw.rect(screen, (255, 255, 255), paddle)
            pygame.draw.circle(screen, (255, 255, 255), ball.center, ball_radius)
            
            # Draw score
            score_text = font.render(f"Score: {score}", True, (255, 255, 255))
            screen.blit(score_text, (W // 2 - score_text.get_width() // 2, 20))
            
            # Draw timer
            timer_text = font.render(f"Time: {int(remaining_time)}s", True, (255, 255, 255))
            screen.blit(timer_text, (W - timer_text.get_width() - 20, 20))
            
            pygame.display.flip()
            clock.tick(60)

        # Display game over screen only if the user didn't quit manually
        if not exited_by_quit:
            game_over_screen(screen, W, H, score, font, large_font, clock)

    finally:
        pygame.quit()
        listener.stop()

if __name__ == "__main__":
    main()
