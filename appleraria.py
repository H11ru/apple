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
    def __init__(self, id, name, color):
        self.id = id
        self.name = name
        self.color = color

    def __int__(self):
        return self.id

class Tiles:
    def __init__(self, tile_dict):
        # Convert all tiles to Tile instances
        self.tileinstances = {name: Tile(id, name, color) for name, (id, color) in tile_dict.items()}
    def __getattribute__(self, name):
        if name == 'tileinstances':
            return object.__getattribute__(self, 'tileinstances')
        if name in self.tileinstances:
            return self.tileinstances[name]
        else:
            return object.__getattribute__(self, name)

TILES = Tiles({
    "DEBUGBLOCK": [-1, (255, 0, 255)],
    "AIR": [0, (171, 205, 239)],
    "STONE": [1, (128, 128, 128)],
    "DIRT": [2, (139, 69, 19)],
    "GRASS": [3, (34, 139, 34)],
    "WATER": [4, (15, 15, 238)],
})





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
SEA_LEVEL = int(SCREEN_HEIGHT * 0.2 - HILL_HEIGHT) + (HILL_HEIGHT // 3) * 2 + 6

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
    if grid[center_x, y] == int(TILES.STONE):
        stone_y = y
        break

# Set camera so stone is in the vertical center of the viewport
camera_x = center_x - VIEWPORT_WIDTH // 2
camera_y = stone_y - VIEWPORT_HEIGHT // 2
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
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('Appleraria')
pygame.display.set_icon(pygame.image.load("icon.png")) # Apple icon!!!
clock = pygame.time.Clock()
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        camera_x -= 1
    if keys[pygame.K_RIGHT]:
        camera_x += 1
    if keys[pygame.K_UP]:
        camera_y -= 1
    if keys[pygame.K_DOWN]:
        camera_y += 1

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

    # Draw grid EFFUCUENTLY (rememebr: cam pos is a floatinger)
    for x in range(VIEWPORT_WIDTH):
        for y in range(VIEWPORT_HEIGHT):
            grid_x = int(camera_x + x)
            grid_y = int(camera_y + y)
            if 0 <= grid_x < GRID_WIDTH and 0 <= grid_y < GRID_HEIGHT:
                tile_type = grid[grid_x, grid_y]
                # Draw rectangle
                color = Tile_from_id(tile_type).color
                pygame.draw.rect(screen, color, (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))

    # Debug renderers
    if keys[pygame.K_F1]:
        # render sea level as blue line
        pygame.draw.line(screen, (0, 0, 255), (0, (SEA_LEVEL - camera_y) * TILE_SIZE), (SCREEN_WIDTH, (SEA_LEVEL - camera_y) * TILE_SIZE), 1)

    pygame.display.flip()
    clock.tick(60)