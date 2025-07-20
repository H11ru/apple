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
    "AIR": [0, (171, 205, 239)],
    "STONE": [1, (128, 128, 128)],
})





camera_x, camera_y = 0, 0
grid = np.zeros((GRID_WIDTH, GRID_HEIGHT), dtype=int)
noise_vals = np.array([helpers.perlin(i / 15, scale=10) for i in range(GRID_WIDTH)])

HILL_HEIGHT = 20

for x in range(GRID_WIDTH):
    height = int(noise_vals[x] * HILL_HEIGHT) + int(SCREEN_HEIGHT * 0.2 - HILL_HEIGHT)
    grid[x, height:] = TILES.STONE.id

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

    pygame.display.flip()
    clock.tick(60)