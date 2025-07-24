from dataclasses import dataclass
import pygame # sped
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
    
    def __hash__(self):
        return hash(self.id)

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
    "LOGSTUMP_LEFT": [7, (150, 75, 0), 0],
    "LOGSTUMP_RIGHT": [8, (150, 75, 0), 0],
})
static_tiles = ["AIR", "DEBUGBLOCK", "STONE", "DIRT"] # Dont need any updates




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
speed = {} # IUse a DICT
# Put stuff in dict to maek tile by id faster
for tile_name, tile in TILES.tileinstances.items():
    speed[tile.id] = tile
PLAYER_COLLISION_HEIGHT = 2.8
def Tile_from_id(tile_id):
    # This is being called likea  million times in 20 seconds so we have to optimize it a lot
    # Linear searcH? who is this guy?
    # we need to use speed
    return speed.get(tile_id)
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
                # place stump
                # 1. left
                # tree base is at (x, y)
                y -= 1
                if random.random() < 0.6 and x - 1 >= 0 and grid[x - 1, y] == TILES.AIR and Tile_from_id(grid[x - 1, y + 1]).solid:
                    grid[x - 1, y] = TILES.LOGSTUMP_LEFT
                # 2. right
                if random.random() < 0.6 and  x + 1 < GRID_WIDTH and grid[x + 1, y] == TILES.AIR and Tile_from_id(grid[x + 1, y + 1]).solid:
                    grid[x + 1, y] = TILES.LOGSTUMP_RIGHT
                y += 1
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
update = {(1,1)} # (x, y)
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

# At start,u pdate everything tjat isnt static
# use niumpy to speed up
# So, loop over all tiles and f they are not static, add them to the update set


class Item:
    def __init__(self, name, id, *bleh, **blah):
        self.name = name
        self.id = id
        if "count" in blah or "count" in bleh:
            raise DeprecationWarning("Item count is gone")

    def __repr__(self):
        return f"Item(name={self.name}, id={self.id})"

    def __eq__(self, other):
        return isinstance(other, Item) and self.name == other.name and self.id == other.id
    
    def __hash__(self):
        # must be a hashable type for dicts
        return hash((self.name, self.id))

GROWABLE_TILES = {TILES.GRASS, TILES.DIRT} # Soil

class Inventory:
    def __init__(self):
        self.items = {}

    def add_item(self, item, count=1):
        if isinstance(item, Tile):
            item = Item(name=item.name,
                        id=int(item) + 10000)
        if item in self.items:
            self.items[item] += count
        else:
            self.items[item] = count

    def remove_item(self, item, count=1):
        if item in self.items:
            self.items[item] -= count
            if self.items[item] <= 0:
                del self.items[item]
        else:
            raise ValueError(f"Item {item} not found in inventory")
        
    def can_lose_item(self, item, count=1):
        if item in self.items:
            return self.items[item] >= count
        return False
    
    def try_remove_item(self, item, count=1):
        if self.can_lose_item(item, count):
            self.remove_item(item, count)
            return True
        return False
    
    def get_all_items(self):
        return self.items
    
inventory = Inventory()

ITEMS = {
    "STONE": ("STONE", 1, 1),
    "DIRT": ("DIRT", 2, 1),
    "LOG": ("LOG", 5, 1),
    "APPLE": ("APPLE", 6, 1),
}

def AAAA(item_dict, name, id, count, confirm):
    # Crash
    raise ValueError(f"Item {name} with id {id} and count {count} has its other name wrong. corruption or typo or wrong or soerthing ?????")

class Items:
    # Tiles style but for ITEMS instead
    def __init__(self, item_dict):
        # Convert all items to Item instances
        self.iteminstances = {name: Item(name, id) if confirm == name else AAAA(item_dict, name, id, trash, confirm) for name, (confirm, id, trash) in item_dict.items()}
    def __getattribute__(self, name):
        if name == 'iteminstances':
            return object.__getattribute__(self, 'iteminstances')
        if name in self.iteminstances:
            return self.iteminstances[name]
        else:
            return object.__getattribute__(self, name)

ITEMS = Items(ITEMS) # Convert dict to useful objecvt

drops = {
    TILES.STONE: {ITEMS.STONE: [{"chance": 1.0, "count": 1}]}, # List of tables
    TILES.DIRT: {ITEMS.DIRT: [{"chance": 1.0, "count": 1}]},
    TILES.GRASS: {ITEMS.DIRT: [{"chance": 1.0, "count": 1}]}, # Grass drops dirt because you kill the grass
    TILES.LOG: {ITEMS.LOG: [{"chance": 1.0, "count": 1}]},
    TILES.LEAVES: {ITEMS.APPLE: [{"chance": 0.1, "count": 1}]}, # 10% chance to drop an apple
}

rotateflip_grid = np.random.randint(0, 16, size=(GRID_WIDTH, GRID_HEIGHT), dtype=np.uint8)
# 4 bits: [rotate(2 bits)][flipx][flipy]
rotateflip_data = {
    # Allow flipping (0 = no, 1 = X only, 2 = Y only, 3 = yes), Allow rotation (0 = no, 1 = only 180, 2 = all)
    TILES.DEBUGBLOCK: [0, 0],
    TILES.AIR: [0, 0],
    TILES.STONE: [3, 1],
    TILES.DIRT: [3, 2],
    TILES.GRASS: [1, 0], # It has a grassy top, so we cant rotate it or flip it on Y asi t would move the grassy top
    TILES.LOG: [3, 1], # Logs have top to bototm lines. we can onyl flip or rotate 180, 90 would misalign the lines.
    TILES.LEAVES: [3, 2],
    TILES.WATER: [3, 1], # Wave pattern
}


import os

def load_texture(name, fallback_color, size, override=None, stfu=False, override_override=False):
    if name == "tile_debugblock":
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        surf.fill((0, 0, 0))
        # Top-left
        pygame.draw.rect(surf, (255, 0, 255), (0, 0, size // 2, size // 2))
        # Bottom-right
        pygame.draw.rect(surf, (255, 0, 255), (size // 2, size // 2, size // 2, size // 2))
        return surf


    filename = f"{name}.png"
    if os.path.exists(filename):
        try:
            img = pygame.image.load(filename).convert_alpha()
            img = pygame.transform.scale(img, (size, size if override is None else override))
            return img
        except Exception as e:
            print(f"[WARN] Failed to load {filename}: {e}") if not stfu else None
    print(f"[WARN] Texture '{filename}' not found, using solid color.") if not stfu else None
    surf = pygame.Surface((size, size if override is None else override), pygame.SRCALPHA)
    # Old: fill with fallback color
    # New: classic error texture
    surf.fill((0, 0, 0))
    w = size
    h = size if override is None else override
    # Top-left
    pygame.draw.rect(surf, (255, 0, 255), (0, 0, w // 2, h // 2))
    # Bottom-right
    pygame.draw.rect(surf, (255, 0, 255), (w // 2, h // 2, w // 2, h // 2))
    if override_override:
        surf.fill(fallback_color)
    return surf

tile_textures = {}
for tile in TILES.tileinstances.values():
    texname = f"tile_{tile.name.lower()}"
    tile_textures[tile.id] = load_texture(texname, tile.color, TILE_SIZE, stfu=True if texname == "tile_air" else False, override_override=texname== "tile_air")

item_textures = {}
for item in ITEMS.iteminstances.values():
    texname = f"item_{item.name.lower()}"
    if os.path.exists(texname + ".png"):
        item_textures[item.id] = load_texture(texname, (200, 200, 200), TILE_SIZE)
    else:
        item_textures[item.id] = load_texture("tile_" + item.name.lower(), (200, 200, 200), TILE_SIZE)

# Player texture (example, you can customize)
player_texture = load_texture("player", (255, 0, 0), TILE_SIZE * PLAYER_WIDTH, override=TILE_SIZE * PLAYER_HEIGHT)


# ...existing code...

# Precompute all needed flip/rotate variants for each tile type
precomputed_tile_variants = {}

for tile in TILES.tileinstances.values():
    if tile in rotateflip_data:
        allow_flip, allow_rotate = rotateflip_data[tile]
        variants = {}
        # Possible rotations
        rot_options = [0]
        if allow_rotate == 1:
            rot_options = [0, 180]
        elif allow_rotate == 2:
            rot_options = [0, 90, 180, 270]
        # Possible flips
        flip_options = [(False, False)]
        if allow_flip == 1:
            flip_options = [(False, False), (True, False)]
        elif allow_flip == 2:
            flip_options = [(False, False), (False, True)]
        elif allow_flip == 3:
            flip_options = [(False, False), (True, False), (False, True), (True, True)]
        # Generate all needed combinations
        for rot in rot_options:
            for flipx, flipy in flip_options:
                key = (rot, flipx, flipy)
                tex = tile_textures[tile.id]
                tex2 = pygame.transform.flip(tex, flipx, flipy)
                if rot:
                    tex2 = pygame.transform.rotate(tex2, rot)
                variants[key] = tex2
        precomputed_tile_variants[tile.id] = variants

# ...existing code...

oscreen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

f3 = False
commandconsole = False
input_text = ""
deltarune = 1
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
                    if input_text.strip():
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
                        commandconsole = False
                        input_text = ""
                else:
                    input_text += event.unicode


    keys = pygame.key.get_pressed()
    on_ground = False

    mouse_x, mouse_y = pygame.mouse.get_pos()  


    if pygame.mouse.get_pressed()[0]:  # Left mouse button
        tile_x = int(camera_x + mouse_x / TILE_SIZE)
        tile_y = int(camera_y + mouse_y / TILE_SIZE)
        if 0 <= tile_x < GRID_WIDTH and 0 <= tile_y < GRID_HEIGHT:
            tile_id = grid[tile_x, tile_y]
            if tile_id != TILES.AIR and tile_id != TILES.DEBUGBLOCK:
                #print(f"You whacked a {Tile_from_id(tile).name} at ({tile_x}, {tile_y})")
                #print("driosO: " + str(drops.get(Tile_from_id(tile), {})))
                # Get drops for this tile
                if tile_id == TILES.LOG:
                    # Remove left stump if present and facing into this log
                    if tile_x - 1 >= 0 and grid[tile_x - 1, tile_y] == TILES.LOGSTUMP_LEFT:
                        grid[tile_x - 1, tile_y] = TILES.AIR
                    # Remove right stump if present and facing into this log
                    if tile_x + 1 < GRID_WIDTH and grid[tile_x + 1, tile_y] == TILES.LOGSTUMP_RIGHT:
                        grid[tile_x + 1, tile_y] = TILES.AIR

                if Tile_from_id(tile_id) in drops:
                    for item, tables in drops[Tile_from_id(tile_id)].items():
                        for drop in tables:
                            #print("drop: " + str(drop))
                            if random.random() < drop["chance"]:
                                inventory.add_item(item, drop["count"])
                                #print(f"Inserter: Added item: {item.name} x{drop['count']}")
                # Remove tile from grid
                grid[tile_x, tile_y] = TILES.AIR
                # Add surrounding tiles to update list
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        nx, ny = tile_x + dx, tile_y + dy
                        if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                            if (nx, ny) not in update:
                                update.add((nx, ny))



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
    new_update = set()
    for x, y in update:
        tileid = grid[x, y]
        tileobj = Tile_from_id(tileid)
        if tileid == TILES.LOG:
            below = grid[x, y + 1] if y + 1 < GRID_HEIGHT else TILES.GRASS
            if Tile_from_id(below) not in GROWABLE_TILES | {TILES.LOG}:
                # The log breaks
                grid[x, y] = TILES.AIR
                # Drops
                if TILES.LOG in drops:
                    for item, tables in drops[TILES.LOG].items():
                        for drop in tables:
                            if random.random() < drop["chance"]:
                                inventory.add_item(item, drop["count"])
                                #print(f"Inserter: Added item: {item.name} x{drop['count']}")

                # Add surrounding tiles to update list
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                            if (nx, ny) not in new_update:
                                new_update.add((nx, ny))
                  # --- LEAF SUPPORT CHECK ---
        # Stumps
        elif tileid == TILES.LOGSTUMP_LEFT:
            # check for log on right, if no, remove stump
            if grid[x + 1, y] != TILES.LOG:
                grid[x, y] = TILES.AIR
        elif tileid == TILES.LOGSTUMP_RIGHT:
            # check for log on left, if no, remove stump
            if grid[x - 1, y] != TILES.LOG:
                grid[x, y] = TILES.AIR


        elif tileid == TILES.LEAVES:
            found_log = False
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                        if grid[nx, ny] == TILES.LOG:
                            # Use flood fill to check for a direct path from the log to this leaf, if not, dont count
                            def ff(smallergrid, sx, sy, ex, ey):
                                q = [(sx, sy)]
                                visited = set()
                                while q:
                                    cx, cy = q.pop(0)
                                    if (cx, cy) == (ex, ey):
                                        return True
                                    visited.add((cx, cy))
                                    for dx2 in range(-1, 2):
                                        for dy2 in range(-1, 2):
                                            if abs(dx2) + abs(dy2) == 1:
                                                nx2, ny2 = cx + dx2, cy + dy2
                                                #if 0 <= nx2 < GRID_WIDTH and 0 <= ny2 < GRID_HEIGHT: # old
                                                if 0 <= nx2 < smallergrid.shape[0] and 0 <= ny2 < smallergrid.shape[1]: # new
                                                    if smallergrid[nx2, ny2] == TILES.LEAVES or smallergrid[nx2, ny2] == TILES.LOG:
                                                        if (nx2, ny2) not in visited:
                                                            q.append((nx2, ny2))
                                return False
                            
                            # floro dill using  4x4 grid artound leaf
                            leaf_grid = grid[x-2:x+3, y-2:y+3]
                            if ff(leaf_grid, 2, 2, 2 + dx, 2 + dy):
                                found_log = True
                                break
                            
                if found_log:
                    break



            if not found_log:
                # The leaf disintegrates and drops fruit
                grid[x, y] = TILES.AIR
                if TILES.LEAVES in drops:
                    for item, tables in drops[TILES.LEAVES].items():
                        for drop in tables:
                            if random.random() < drop["chance"]:
                                inventory.add_item(item, drop["count"])
                for dx in range(-1, 2):
                    for dy in range(-1, 2):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < GRID_WIDTH and 0 <= ny < GRID_HEIGHT:
                            if (nx, ny) not in new_update:
                                new_update.add((nx, ny))



    update = new_update
                    
            
    # --- Horizontal movement and wall collision ---
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        player_vx += -0.1
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        player_vx += 0.1

    
    next_x = player_x + player_vx * deltarune 
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
    #print(deltarune)


    # --- Gravity and jumping ---
    gravity = 0.05
    air_friction = 0.95
    player_vy += gravity * deltarune  # Gravity
    player_vy *= air_friction ** deltarune  # Friction scaled by deltatime


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
        if player_vy > 0:
            on_ground = True
        player_vy = 0

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

    # Draw grid EFFUCUENTLY (rememebr: cam pos is a floatinger so we need to NOT use int(), as if you walk half a block they should be ofset)
    
    # --- Replace grid drawing ---
    # We use a different surface because for whatever reason drawing anything onto the pygame.display.set_mode is super slow but Surfaces are fast. WHY??????????????????

    for x in range(VIEWPORT_WIDTH+1):
        for y in range(VIEWPORT_HEIGHT+1):
            gx = int(camera_x + x)
            gy = int(camera_y + y)
            if 0 <= gx < GRID_WIDTH and 0 <= gy < GRID_HEIGHT:
                tile_id = grid[gx, gy]
                tile_obj = Tile_from_id(tile_id)
                tex = tile_textures.get(tile_id)
                if tex:
                    if tile_id in precomputed_tile_variants and tile_obj in rotateflip_data:
                        allow_flip, allow_rotate = rotateflip_data[tile_obj]
                        rf = rotateflip_grid[gx, gy]
                        # Rotation
                        rot = 0
                        if allow_rotate == 1:
                            if (rf >> 2) & 0b01:
                                rot = 180
                        elif allow_rotate == 2:
                            rot = ((rf >> 2) & 0b11) * 90
                        # Flip
                        flipx = False
                        flipy = False
                        if allow_flip == 1:
                            flipx = bool(rf & 0b0010)
                        elif allow_flip == 2:
                            flipy = bool(rf & 0b0001)
                        elif allow_flip == 3:
                            flipx = bool(rf & 0b0010)
                            flipy = bool(rf & 0b0001)
                        tex2 = precomputed_tile_variants[tile_id].get((rot, flipx, flipy), tex)
                    else:
                        tex2 = tex
                    oscreen.blit(
                        tex2,
                        (
                            int(x * TILE_SIZE - (camera_x % 1) * TILE_SIZE),
                            int(y * TILE_SIZE - (camera_y % 1) * TILE_SIZE)
                        )
                    )
    screen.blit(oscreen, (0, 0))


                
    # Debug renderers
    if keys[pygame.K_F1]:
        # render sea level as blue line
        pygame.draw.line(screen, (0, 0, 255), (0, (SEA_LEVEL - camera_y) * TILE_SIZE), (SCREEN_WIDTH, (SEA_LEVEL - camera_y) * TILE_SIZE), 1)

    # Draw player
        # Draw player sprite (use PLAYER_WIDTH/HEIGHT for size, but not for position)

    # --- Replace player drawing ---
    screen.blit(
        player_texture,
        (
            int((player_x - camera_x) * TILE_SIZE),
            int((player_y - camera_y) * TILE_SIZE)
        )
    )

    # Draw inventory as a row of item icons with counts
    font = pygame.font.Font(None, 24)
    spacing = 8
    x_offset = 10
    y_offset = 10
    # Draw a transparant bg for the bar (calculate based on amount of items)
    inventory_width = len(inventory.get_all_items()) * (32 + spacing) - spacing
    if inventory_width < 0: inventory_width = 0
    transparancy_surface = pygame.Surface((inventory_width + 16, 32 + 16), pygame.SRCALPHA)
    transparancy_surface.fill((0, 0, 0, 128))  # semi-transparent black
    if len(inventory.get_all_items()) != 0:
        screen.blit(transparancy_surface, (SCREEN_WIDTH / 2 - inventory_width / 2 - 12, SCREEN_HEIGHT - 32 - 10 - 8))
    for idx, (item, count) in enumerate(inventory.get_all_items().items()):
        # Start at (SCREEN_WIDTH / 2 - (len(inventory.get_all_items()) * (TILE_SIZE + spacing) / 2), SCREEN_HEIGHT - TILE_SIZE - 10)
        """item_x = x_offset + idx * (TILE_SIZE + spacing)
        item_y = y_offset""" # THIS IS FUCKING NOT AT ALL LIKE WHAT ISAID IN THE OCMMENT. WRONG!!!!!!!!
        item_x = SCREEN_WIDTH / 2 - (len(inventory.get_all_items()) * (32 + spacing) / 2) + idx * (32 + spacing)
        item_y = SCREEN_HEIGHT - 32 - 10
        item_texture = item_textures.get(item.id)
        if item_texture:
            screen.blit(pygame.transform.scale(item_texture, (32, 32)), (item_x, item_y))
            count_text = font.render(f"x{count}", True, (255, 255, 255))
            screen.blit(count_text, (item_x + 32 - count_text.get_width(), item_y + 32 - count_text.get_height()))


    if commandconsole:
        pygame.draw.rect(screen, (0, 0, 0, 128), (0, SCREEN_HEIGHT-50, 200, 48))
        font = pygame.font.Font(None, 24)
        input_surface = font.render(input_text, True, (255, 255, 255))
        screen.blit(input_surface, (10, SCREEN_HEIGHT-40))


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
        # INVENJTORIUM
        # Draw inventory liek this: Inventory: A x1, B x2, C x3
        inventory_text = font.render(f"Inventory: " + ", ".join(f"{item.name} x{count}" for item, count in inventory.get_all_items().items()), True, (255, 255, 255))
        screen.blit(inventory_text, (10, 70))


    deltarune = 60 / clock.get_fps() if clock.get_fps() > 0 else 60 # deltatime
    deltarune /= 2

    pygame.display.flip()
    clock.tick(60)