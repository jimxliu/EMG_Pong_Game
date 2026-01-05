# EMG-Controlled Pong Game Design

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     EMG Data Source                             │
│              (OpenBCI GUI / NeuroFly App)                       │
│                                                                 │
│  Sends UDP packets:                                             │
│  { "type": "emgJoystick", "data": [x, y] }                      │
└──────────────────────────────┬──────────────────────────────────┘
                               │ UDP Port 12345
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   neurofly.py                                   │
│              UDPClientListener Class                            │
│                                                                 │
│  • Listens on 0.0.0.0:12345                                     │
│  • Parses JSON packets in background thread                     │
│  • Calls registered callback with packet data                   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│           pong_simple_terminal.py - Main Game Loop              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Global State                                             │   │
│  │  • cmd: paddle direction (-1/+1/0)                       │   │
│  │  • score: current score                                  │   │
│  │  • EMG_THRESHOLD: 0.1                                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ emg_joystick_callback()                                  │   │
│  │  Input: UDP packet { "data": [x, y] }                    │   │
│  │  • Extract data[1] (Y value)                             │   │
│  │  • If y > 0.1: cmd = -1 (move up)                        │   │
│  │  • If y < -0.1: cmd = +1 (move down)                     │   │
│  │  • Else: cmd = 0 (no movement)                           │   │
│  │  Output: Update global cmd variable                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ countdown_sequence()                                     │   │
│  │  Display: 3 → 2 → 1 → GO!                                │   │
│  │  Duration: 4 seconds total                               │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Main Game Loop (60 FPS)                                  │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │                                                          │   │
│  │  Timer Check:                                            │   │
│  │    elapsed_time = (current - start) / 1000               │   │
│  │    remaining_time = 60 - elapsed_time                    │   │
│  │    if remaining_time ≤ 0: exit loop                      │   │
│  │                                                          │   │
│  │  Paddle Logic:                                           │   │
│  │    if cmd ≠ 0:                                           │   │
│  │      paddle.y += cmd * STEP (5 pixels/frame)             │   │
│  │      clamp paddle within screen bounds                   │   │
│  │                                                          │   │
│  │  Ball Physics:                                           │   │
│  │    ball.x += vx                                          │   │
│  │    ball.y += vy                                          │   │
│  │                                                          │   │
│  │    if ball hits top/bottom wall:                         │   │
│  │      vy *= -1 (bounce)                                   │   │
│  │      vy += random(-0.01, 0.01) (slight variation)        │   │
│  │                                                          │   │
│  │    if ball exits left/right:                             │   │
│  │      vx *= -1                                            │   │
│  │                                                          │   │
│  │    if ball collides with paddle AND vx < 0:              │   │
│  │      vx *= -1 (bounce)                                   │   │
│  │      score += 1                                          │   │
│  │                                                          │   │
│  │  Rendering (Pygame):                                     │   │
│  │    • Clear screen (black)                                │   │
│  │    • Draw paddle (white rectangle)                       │   │
│  │    • Draw ball (white circle, radius=8)                  │   │
│  │    • Render score text (top center)                      │   │
│  │    • Render timer text (top right)                       │   │
│  │    • Flip display                                        │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ game_over_screen()                                       │   │
│  │  Display: "GAME OVER" + "Final Score: {score}"           │   │
│  │  Wait for window close                                   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Cleanup (finally block)                                  │   │
│  │  • pygame.quit()                                         │   │
│  │  • listener.stop()                                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
EMG Signal (OpenBCI)
        ↓
   UDP JSON Packet
   { "type": "emgJoystick", 
     "data": [emg_x, emg_y] }
        ↓
   UDPClientListener (background thread)
   └─→ Parse JSON
   └─→ Call emg_joystick_callback()
        ↓
   emg_joystick_callback()
   └─→ Extract emg_y (data[1])
   └─→ Compare to EMG_THRESHOLD (0.1)
   └─→ Set global cmd (-1, 0, or +1)
        ↓
   Main Game Loop
   └─→ Read cmd variable
   └─→ Move paddle accordingly
   └─→ Update physics
   └─→ Render frame
   └─→ Update score
        ↓
   Display (Pygame)
   └─→ Paddle, ball, score, timer
```

## Game States

```
┌─────────────┐
│   START     │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ COUNTDOWN (3-2-1)│
│ Duration: 3 sec  │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  GO MESSAGE      │
│  Duration: 1 sec │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│  PLAYING         │
│  Duration: 60 sec│
│  FPS: 60         │
└──────┬───────────┘
       │ (timer expires)
       ▼
┌──────────────────┐
│  GAME OVER       │
│  Show final score│
│  Wait for close  │
└──────┬───────────┘
       │
       ▼
┌─────────────┐
│     END     │
└─────────────┘
```

## Key Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `DEFAULT_UDP_PORT` | 12345 | UDP listener port |
| `EMG_THRESHOLD` | 0.1 | Minimum EMG magnitude to trigger movement |
| `STEP` | 5 | Paddle pixels per frame |
| `game_duration` | 60 | Game length in seconds |
| `ball_radius` | 8 | Ball display radius in pixels |
| `FPS` | 60 | Game loop frame rate |
| `Screen W × H` | 800 × 500 | Display resolution |
| `Paddle size` | 12 × 100 | Paddle width × height (pixels) |

## Threading Model

```
Main Thread (Pygame)          Background Thread (UDP Listener)
─────────────────────         ─────────────────────────────────
│                             │
├─ pygame.init()              │
├─ Start listener ────────────┼──→ UDPClientListener.start()
│                             │       │
│ Main Game Loop              │       ├─ Bind socket to :12345
│ ├─ Poll events              │       ├─ Loop: recvfrom()
│ ├─ Update game state        │       │   ├─ Parse JSON
│ ├─ Render frame             │       │   └─ Call callback()
│ ├─ Sleep to 60 FPS          │       │
│ └─ Check timer/quit         │       │ (Daemon thread)
│                             │       │
├─ Game Over screen           │ (continues in background)
│                             │
├─ listener.stop() ──────────→├─ Break loop, close socket
├─ pygame.quit()              │
│                             │
└─ Exit                       └─ Exit
```

## Ball Collision Detection

```
Ball Rect (32×32) used for collision checks
but rendered as circle (radius 8)

┌─ Top/Bottom Wall Check
│  if ball.top <= 0 or ball.bottom >= 500:
│      vy *= -1
│      vy += random(-0.01, 0.01)
│
├─ Left/Right Boundary Check
│  if ball.left <= 0 or ball.right >= 800:
│      vx *= -1
│      print("Ball escaped!")
│
└─ Paddle Collision Check
   if ball.colliderect(paddle) and vx < 0:
       vx *= -1
       score += 1
```

## Control Mapping

```
EMG Signal (data[1]) → Paddle Direction

  emg_y ≈ +0.7  (flexed)    →  cmd = -1  →  paddle.y -= 5  (move up)
  emg_y ≈  0.0  (neutral)   →  cmd =  0  →  paddle.y +=  0  (stay)
  emg_y ≈ -0.7  (relaxed)   →  cmd = +1  →  paddle.y += 5  (move down)

Threshold: ±0.1
  If -0.1 < emg_y < 0.1: cmd = 0 (dead zone)
```

## Performance Notes

- **Latency**: UDP callback → global cmd update (< 1ms)
- **Paddle responsiveness**: 60 FPS game loop reads cmd every frame (16.7ms max latency)
- **Ball physics**: Simple linear motion with collision checks
- **Thread safety**: Global `cmd` variable accessed without locking (acceptable for single producer/consumer)

