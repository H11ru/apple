from dataclasses import dataclass
import pygame
import sys
import numpy as np
import helpers
import random
seed = 13 # Put world seed here
helpers.setseed(seed)
random.seed(seed)

GRID_WIDTH, GRID_HEIGHT = 800, 400
VIEWPORT_WIDTH, VIEWPORT_HEIGHT = 80, 40
TILE_SIZE = 16
SCREEN_WIDTH = TILE_SIZE * VIEWPORT_WIDTH
SCREEN_HEIGHT = TILE_SIZE * VIEWPORT_HEIGHT

class Tile:
    def __init__(self, id, name, color, solid):
        self.id = id
        self.name = name
        self.color = color
        self.solid = solid

    def __int__(self):
        return self.id
    
    def __eq__(self, other):
        if isinstance(other, Tile):
            return self.id == other.id
        elif isinstance(other, int):
            return self.id == other
        return False

class Tiles:
    def __init__(self, tile_dict):
        # Convert all tiles to Tile instances
        self.tileinstances = {name: Tile(id, name, color, solid) for name, (id, color, solid) in tile_dict.items()}
    def __getattribute__(self, name):
        if name == 'tileinstances':
            return object.__getattribute__(self, 'tileinstances')
        if name in self.tileinstances:
            return self.tileinstances[name]
        else:
            return object.__getattribute__(self, name)

TILES = Tiles({
    "DEBUGBLOCK": [-1, (255, 0, 255), 1],
    "AIR": [0, (171, 205, 239), 0],
    "STONE": [1, (128, 128, 128), 1],
    "DIRT": [2, (139, 69, 19), 1],
    "GRASS": [3, (34, 139, 34), 1],
    "WATER": [4, (15, 15, 238), 0],
    "LOG": [5, (150, 75, 0), 0],
    "LEAVES": [6, (0, 215, 0), 0],
})




JUMP_POWER = 1

camera_x, camera_y = 0, 0
grid = np.zeros((GRID_WIDTH, GRID_HEIGHT), dtype=int)
MOUNTAIN_FACTOR = 3
noise_vals = (np.array([helpers.perlin(i / 100) for i in range(GRID_WIDTH)]) * MOUNTAIN_FACTOR) ** 2 / MOUNTAIN_FACTOR
# Generate three noise maps:
lake_noise = np.array([helpers.perlin(i / 40 + 200) for i in range(GRID_WIDTH)])       # Small scale, hilly
blend_noise = np.array([helpers.perlin(i / 200 + 300) for i in range(GRID_WIDTH)])     # Very large scale

# Scale and offset
lake_height = (lake_noise) * 0.5 - 0.3    # Lower and more rolling

blend = (blend_noise + 1) / 2  # Normalize to [0, 1] range

# Final noise: blend between lake and mountain
noise_vals = lake_height * (1 - blend) + noise_vals * blend

HILL_HEIGHT = 50
# calcialte sea level
SEA_LEVEL = int(GRID_HEIGHT * 0.3 - HILL_HEIGHT) + (HILL_HEIGHT // 3) * 2 + 12 # What ever this is it works for some reason and idk

for x in range(GRID_WIDTH):
    height = int(noise_vals[x] * HILL_HEIGHT) + int(SCREEN_HEIGHT * 0.2 - HILL_HEIGHT)
    grid[x, height+1:] = TILES.DIRT
    # Place stone deeeper down
    dirt_depth = random.randint(4,5) if height < SEA_LEVEL else 3
    grid[x, (height + dirt_depth):] = TILES.STONE
    if height < SEA_LEVEL:
        # Grass toplayer
        grid[x, height] = TILES.GRASS
    else:
        # Fill from grass's y pos UP to sea level with water
        # Usiong NUMPY
        grid[x, SEA_LEVEL:height+1] = TILES.WATER

PLAYER_COLLISION_WIDTH = 1.8
PLAYER_COLLISION_HEIGHT = 2.8
PLAYER_WIDTH = 2
PLAYER_HEIGHT = 3

tree_timer = 0
for x in range(GRID_WIDTH):
    tree_timer -= 1
    # Find the highest grass tile in this column
    for y in range(GRID_HEIGHT):
        if grid[x, y] == TILES.GRASS:
            if tree_timer <= 0 and random.random() < 0.2:  # 20% chance, adjust as needed
                tree_height = random.randint(6, 9)
                # Place trunk
                for h in range(tree_height):
                    if y-h-1 >= 0:
                        grid[x, y-h-1] = TILES.LOG
                leaf = [
                    [0, 0.6, 1, 0.6, 0],
                    [0.1, 0.9, 1, 0.9, 0.1],
                    [0.6, 1, -1, 1, 0.6],
                    [0.8, 1, 0, 1, 0.8]
                ]
                # NOTE: -1 is the spot where the top of the trunk is. all other values are probabilities for leaves
                # Add leaves
                # Add leaves
                for dy in range(-2, 2):
                    for dx in range(-2, 3):
                        lx = x + dx
                        ly = (y - tree_height) + dy
                        if 0 <= lx < GRID_WIDTH and 0 <= ly < GRID_HEIGHT:
                            if leaf[dy+2][dx+2] > random.random():
                                grid[lx, ly] = TILES.LEAVES
                # FIX FLOATING LEAVES
                # Foe each leaf, if its not touching adjacent to another leaf or a log, remove it
                for ly in range(y - tree_height - 2, y + 2):
                    for lx in range(x - 2, x + 3):
                        if 0 <= lx < GRID_WIDTH and 0 <= ly < GRID_HEIGHT:
                            if grid[lx, ly] == TILES.LEAVES:
                                # Check adjacent tiles
                                has_adjacent = False
                                for dy in range(-1, 2):
                                    for dx in range(-1, 2):
                                        if dx == 0 and dy == 0:
                                            continue
                                        ax, ay = lx + dx, ly + dy
                                        if 0 <= ax < GRID_WIDTH and 0 <= ay < GRID_HEIGHT:
                                            if grid[ax, ay] == TILES.LEAVES or grid[ax, ay] == TILES.LOG:
                                                has_adjacent = True
                                                break
                                    if has_adjacent:
                                        break
                                if not has_adjacent:
                                    grid[lx, ly] = TILES.AIR


                tree_timer = random.randint(5, 10)
            break  # Only one tree per column
        
def Tile_from_id(tile_id):
    for tile in TILES.tileinstances.values():
        if int(tile) == tile_id:
            return tile
    raise ValueError(f"Tile with id {tile_id} not found")
def Tile_from_name(tile_name):
    if tile_name in TILES.tileinstances:
        return TILES.tileinstances[tile_name]
    raise ValueError(f"Tile with name {tile_name} not found")

# Move camera down until a non-air is in the middle of the screen
center_x = GRID_WIDTH // 2
stone_y = 0
for y in range(0, GRID_HEIGHT, 1): # Fixed: positive step size 1
    if Tile_from_id(grid[center_x, y]).solid:
        stone_y = y
        break

# Set camera so stone is in the vertical center of the viewport
camera_x = center_x - VIEWPORT_WIDTH // 2
camera_y = stone_y
player_x = center_x
player_y = stone_y - 5
# Replace your stars initialization with:
star_colors = [
    (255, 255, 255),  # White
    (255, 244, 232),  # Warm white
    (202, 216, 255),  # Blue-white
    (255, 204, 229),  # Pinkish
    (255, 255, 204),  # Yellowish
]
stars = [
    [
        random.randint(0, SCREEN_WIDTH),
        random.randint(0, SCREEN_HEIGHT),
        random.uniform(-0.01, 0.01),
        random.uniform(-0.01, 0.01),
        random.choices([1, 2, 3], [0.5, 0.3, 0.2])[0],
        random.randint(0, 60),  # twinkle timer
        random.choice(star_colors)
    ]
    for _ in range(100)
]
pygame.init()
player_vx = 0
player_vy = 0
update = [] # (x, y)
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('Appleraria')
pygame.display.set_icon(pygame.image.load("icon.png")) # Apple icon!!!
clock = pygame.time.Clock()
# Check horizontal collisions at all 4 corners
def is_solid_at(x, y):
    if 0 <= int(x) < GRID_WIDTH and 0 <= int(y) < GRID_HEIGHT:
        return Tile_from_id(grid[int(x), int(y)]).solid
    return False


def player_collides_at(x, y):
    # Center the hitbox inside the sprite
    x += (PLAYER_WIDTH - PLAYER_COLLISION_WIDTH) / 2
    y += (PLAYER_HEIGHT - PLAYER_COLLISION_HEIGHT)

    points = []
    steps = 5  # Increase for more precision

    # Top and bottom edges
    for i in range(steps + 1):
        fx = x + i * (PLAYER_COLLISION_WIDTH - 0.001) / steps
        points.append((fx, y))  # Top
        points.append((fx, y + PLAYER_COLLISION_HEIGHT - 0.001))  # Bottom

    # Left and right edges
    for i in range(1, steps):  # skip corners (already checked)
        fy = y + i * (PLAYER_COLLISION_HEIGHT - 0.001) / steps
        points.append((x, fy))  # Left
        points.append((x + PLAYER_COLLISION_WIDTH - 0.001, fy))  # Right

    return any(is_solid_at(px, py) for px, py in points)

# At start,u pdate everything
for x in range(GRID_WIDTH):
    for y in range(GRID_HEIGHT):
        update.append((x, y))
f3 = False
commandconsole = False
input_text = ""
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F3:
                f3 = not f3
            if event.key == pygame.K_RETURN:
                commandconsole = True
            if event.key == pygame.K_ESCAPE:
                commandconsole = False
                input_text = ""
            if commandconsole:
                if event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.key == pygame.K_RETURN:
                    # Process command
                    if input_text == "h":
                        player_x = GRID_WIDTH // 2
                        player_y = 0
                    elif input_text == "b":
                        player_vy = -15
                    elif input_text == "s":
                        hgrid = np.random.choice([int(t) for t in TILES.tileinstances.values()], size=(GRID_WIDTH, GRID_HEIGHT))
                        # Randomly interleave grid and hgrid (50% chance)
                        for x in range(GRID_WIDTH):
                            for y in range(GRID_HEIGHT):
                                if random.random() < 0.2:
                                    grid[x, y] = hgrid[x, y]
                                elif random.random() < 0.2:
                                    grid[x, y] = TILES.AIR
                                elif random.random() < 0.6:
                                    grid[x, y] = grid[x, y-1] if not grid[x, y-1] == TILES.AIR else TILES.WATER
                else:
                    input_text += event.unicode


    keys = pygame.key.get_pressed()
    on_ground = False

    mouse_x, mouse_y = pygame.mouse.get_pos()  
    if pygame.mouse.get_pressed()[0]:  # Left mouse button
        # Convert mouse position to world tile coordinates
        tile_x = int(camera_x + mouse_x / TILE_SIZE)
        tile_y = int(camera_y + mouse_y / TILE_SIZE)
        if 0 <= tile_x < GRID_WIDTH and 0 <= tile_y < GRID_HEIGHT:
            grid[tile_x, tile_y] = TILES.AIR
            # Add surrounding tiles to update list
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    nx, ny = tile_x + dx, tile_y + dy
                    if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                        if (nx, ny) not in update:
                            update.append((nx, ny))

    """# WATER SPILL
    for x in range(GRID_WIDTH):
        for y in range(GRID_HEIGHT - 1, -1, -1):
            if grid[x, y] == TILES.WATER:
                # Check if the tile below is air
                if y + 1 < GRID_HEIGHT and grid[x, y + 1] == TILES.AIR:
                    grid[x, y + 1] = TILES.WATER
                # Check if the tile to the left is air
                if x - 1 >= 0 and grid[x - 1, y] == TILES.AIR:
                    grid[x - 1, y] = TILES.WATER
                # Check if the tile to the right is air
                if x + 1 < GRID_WIDTH and grid[x + 1, y] == TILES.AIR:
                    grid[x + 1, y] = TILES.WATER"""
    
    # UPDATES
    new_updates = []
    random.shuffle(update)
    for x, y in update:
        tile_id = grid[x, y]

                
    update = new_updates
                    
            
    # --- Horizontal movement and wall collision ---
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        player_vx += -0.1
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        player_vx += 0.1

    
    next_x = player_x + player_vx
    # Horizontal collision using collision box
    if not player_collides_at(next_x, player_y):
        player_x = next_x
    else:
        # Move as close as possible to the wall
        step = 0.05 if player_vx > 0 else -0.05
        while abs(step) < abs(player_vx):
            test_x = player_x + step
            if player_collides_at(test_x, player_y):
                break
            player_x = test_x
            step += 0.05 if player_vx > 0 else -0.05


    # --- Gravity and jumping ---
    player_vy = (player_vy + 0.05) * 0.95  # Gravity and air friction

    # --- Vertical movement ---
    next_y = player_y + player_vy
    if not player_collides_at(player_x, next_y):
        player_y = next_y
        on_ground = False
    else:
        # Move as close as possible to the floor/ceiling
        step = 0.05 if player_vy > 0 else -0.05
        while abs(step) < abs(player_vy):
            test_y = player_y + step
            if player_collides_at(player_x, test_y):
                break
            player_y = test_y
            step += 0.05 if player_vy > 0 else -0.05
        player_vy = 0
        if player_vy > 0:
            on_ground = True

    # --- Jumping (only if on ground) ---
    if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and abs(player_vy) < 0.2:
        # Check if standing on ground (bottom corners of collision box)
        if player_collides_at(player_x, player_y + 0.05):
            player_vy = -JUMP_POWER

    if on_ground:
        player_vx *= 0.8
    else:
        player_vx *= 0.8


    # --- Camera follows player (centered) ---
    camera_x = player_x + PLAYER_WIDTH / 2 - VIEWPORT_WIDTH / 2
    camera_y = player_y + PLAYER_HEIGHT / 2 - VIEWPORT_HEIGHT / 2


    screen.fill((0, 0, 0))
    # EFficientyc featuire: only draw stars if any part of the viewport is outside the grid
    if camera_x < 0 or camera_x + VIEWPORT_WIDTH > GRID_WIDTH or camera_y < 0 or camera_y + VIEWPORT_HEIGHT > GRID_HEIGHT:
        # --- Draw star halos (glow) ---
        for star in stars:
            x, y, vx, vy, size, twinkle, color = star
            pygame.draw.circle(screen, tuple(int(c*0.7) for c in color), (int(x), int(y)), size + 1)

        # --- Draw star cores and cross shapes, update twinkle and position ---
        for star in stars:
            x, y, vx, vy, size, twinkle, color = star

            # Twinkle: randomly change size every so often
            if twinkle <= 0:
                star[4] = max(1, min(3, size + random.choice([-1, 0, 1])))
                star[5] = random.randint(10, 60)
            else:
                star[5] -= 1

            # Draw colored core
            pygame.draw.circle(screen, color, (int(x), int(y)), size - 1)

            # Move star
            star[0] = (x + vx) % SCREEN_WIDTH
            star[1] = (y + vy) % SCREEN_HEIGHT

    # Draw grid EFFUCUENTLY (rememebr: cam pos is a floatinger so we need to NOT use int(), as if you walk half a block they should be ofset)
    for x in range(VIEWPORT_WIDTH+1):
        for y in range(VIEWPORT_HEIGHT+1):
            if 0 <= camera_x + x < GRID_WIDTH and 0 <= camera_y + y < GRID_HEIGHT:
                # NO int() ALLOWED. WE DONT WANT TO ROUND IT
                tile_id = grid[int(camera_x + x), int(camera_y + y)]
                tile = Tile_from_id(tile_id)
                pygame.draw.rect(
                    screen,
                    tile.color if not keys[pygame.K_F5] else ((255, 0, 0) if tile.solid else (0, 255, 0)),
                    (
                        int(x * TILE_SIZE - (camera_x % 1) * TILE_SIZE),
                        int(y * TILE_SIZE - (camera_y % 1) * TILE_SIZE),
                        TILE_SIZE,
                        TILE_SIZE
                    )
                )
                if keys[pygame.K_F2]:
                    # DRAW TYELLOW SQURE IF UPDATE
                    if (int(camera_x + x), int(camera_y + y)) in update:
                        pygame.draw.rect(
                            screen,
                            (255, 255, 0),
                            (
                                int(x * TILE_SIZE - (camera_x % 1) * TILE_SIZE),
                                int(y * TILE_SIZE - (camera_y % 1) * TILE_SIZE),
                                TILE_SIZE,
                                TILE_SIZE
                            ),
                            1
                        )
                
    # Debug renderers
    if keys[pygame.K_F1]:
        # render sea level as blue line
        pygame.draw.line(screen, (0, 0, 255), (0, (SEA_LEVEL - camera_y) * TILE_SIZE), (SCREEN_WIDTH, (SEA_LEVEL - camera_y) * TILE_SIZE), 1)

    # Draw player
        # Draw player sprite (use PLAYER_WIDTH/HEIGHT for size, but not for position)
    pygame.draw.rect(
        screen,
        (255, 0, 0) if not keys[pygame.K_F5] else (0, 0, 255),
        (
            int((player_x - camera_x) * TILE_SIZE),
            int((player_y - camera_y) * TILE_SIZE),
            int(TILE_SIZE * PLAYER_WIDTH),
            int(TILE_SIZE * PLAYER_HEIGHT)
        )
    )

    # DEEBUG
    if f3:
        fps = clock.get_fps()
        font = pygame.font.Font(None, 24)
        fps_text = font.render(f"FPS: {fps:.2f}", True, (255, 255, 255))
        screen.blit(fps_text, (10, 10))
        ROUNDE_player_x = round(player_x, 2)
        ROUNDE_player_y = round(player_y, 2)
        ROUNDE_player_vx = round(player_vx, 2)
        ROUNDE_player_vy = round(player_vy, 2)
        x_pos_text = font.render(f"XY: {ROUNDE_player_x:.2f}, {ROUNDE_player_y:.2f}", True, (255, 255, 255))
        screen.blit(x_pos_text, (10, 30))
        y_vel_text = font.render(f"VEL: {ROUNDE_player_vx:.2f}, {ROUNDE_player_vy:.2f}", True, (255, 255, 255))
        screen.blit(y_vel_text, (10, 50))

    if commandconsole:
        pygame.draw.rect(screen, (0, 0, 0, 128), (0, SCREEN_HEIGHT-50, 200, 48))
        font = pygame.font.Font(None, 24)
        input_surface = font.render(input_text, True, (255, 255, 255))
        screen.blit(input_surface, (10, SCREEN_HEIGHT-40))

    pygame.display.flip()
    clock.tick(60)