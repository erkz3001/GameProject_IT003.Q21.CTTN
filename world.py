import pygame
import random
from settings import TILE_SIZE, SCREEN_WIDTH, SCREEN_HEIGHT, MAP_ROWS, MAP_COLS
from utils import load_assets_by_col, load_assets_by_row, load_tileset_tile, load_strip

# Dungeon_Tileset.png tile indices (10×10 grid, 16×16 px each)
_FLOOR_TILE_INDICES = [6, 7, 8, 9, 16, 17, 18, 19, 26, 27, 28, 29]  # user-confirmed floor
_FLOOR_WEIGHTS      = [2, 2, 2, 2,  2,  3,  3,  2,  2,  2,  2,  2]  # 12 entries
_WALL_H_INDICES     = [1, 2]              # horizontal wall tiles (top/bottom edges)
_WALL_TOP_IDX       = 15                  # vertical wall — top brick row
_WALL_BOT_IDX       = 25                  # vertical wall — bottom brick row
_DOOR_IDX_L         = 66                  # left door panel
_DOOR_IDX_R         = 67                  # right door panel
_HALF               = TILE_SIZE // 2      # half tile size

def move_with_wall_collision(hitbox, dx, dy, walls_group):
    hitbox.x += int(dx)
    for w in walls_group:
        if hitbox.colliderect(w.rect):
            if dx > 0:
                hitbox.right = w.rect.left
                if hitbox.bottom - w.rect.top <= 32:
                    hitbox.y -= 5
                    if any(hitbox.colliderect(wall.rect) for wall in walls_group): hitbox.y += 5
                elif w.rect.bottom - hitbox.top <= 32:
                    hitbox.y += 5
                    if any(hitbox.colliderect(wall.rect) for wall in walls_group): hitbox.y -= 5
            elif dx < 0:
                hitbox.left = w.rect.right
                if hitbox.bottom - w.rect.top <= 32:
                    hitbox.y -= 5
                    if any(hitbox.colliderect(wall.rect) for wall in walls_group): hitbox.y += 5
                elif w.rect.bottom - hitbox.top <= 32:
                    hitbox.y += 5
                    if any(hitbox.colliderect(wall.rect) for wall in walls_group): hitbox.y -= 5
                    
    hitbox.y += int(dy)
    for w in walls_group:
        if hitbox.colliderect(w.rect):
            if dy > 0:
                hitbox.bottom = w.rect.top
                if hitbox.right - w.rect.left <= 32:
                    hitbox.x -= 5
                    if any(hitbox.colliderect(wall.rect) for wall in walls_group): hitbox.x += 5
                elif w.rect.right - hitbox.left <= 32:
                    hitbox.x += 5
                    if any(hitbox.colliderect(wall.rect) for wall in walls_group): hitbox.x -= 5
            elif dy < 0:
                hitbox.top  = w.rect.bottom
                if hitbox.right - w.rect.left <= 32:
                    hitbox.x -= 5
                    if any(hitbox.colliderect(wall.rect) for wall in walls_group): hitbox.x += 5
                elif w.rect.right - hitbox.left <= 32:
                    hitbox.x += 5
                    if any(hitbox.colliderect(wall.rect) for wall in walls_group): hitbox.x -= 5

def clamp_map(hitbox):
    """Clamp a hitbox to the full map bounds (not the screen)."""
    map_w = MAP_COLS * TILE_SIZE
    map_h = MAP_ROWS * TILE_SIZE
    hitbox.x = max(0, min(map_w - hitbox.width,  hitbox.x))
    hitbox.y = max(0, min(map_h - hitbox.height, hitbox.y))

class Camera:
    def __init__(self):
        self.x = 0
        self.y = 0

    def update(self, target_rect):
        self.x = target_rect.centerx - SCREEN_WIDTH  // 2
        self.y = target_rect.centery - SCREEN_HEIGHT // 2
        map_w  = MAP_COLS * TILE_SIZE
        map_h  = MAP_ROWS * TILE_SIZE
        self.x = max(0, min(self.x, map_w - SCREEN_WIDTH))
        self.y = max(0, min(self.y, map_h - SCREEN_HEIGHT))

    def world_to_screen(self, wx, wy):
        return wx - self.x, wy - self.y

    def screen_rect(self, world_rect):
        return pygame.Rect(world_rect.x - self.x, world_rect.y - self.y,
                           world_rect.width, world_rect.height)

class FogOfWar:
    DARK_ALPHA    = 250          # near-opaque darkness
    PLAYER_RADIUS = 260          # px — tight lantern-like radius
    TORCH_RADIUS  = 360          # px — torches illuminate nearby area
    TORCH_COLOR   = (30, 18, 0)  # very dark warm amber

    def __init__(self):
        self._surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        self._pg   = self._build_gradient(self.PLAYER_RADIUS, (0, 0, 0))
        self._tg   = self._build_gradient(self.TORCH_RADIUS,  self.TORCH_COLOR)

    def _build_gradient(self, radius, color=(0, 0, 0)):
        """Radial gradient: large transparent centre fading to opaque at the rim.

        Using power > 1 keeps alpha near-zero for most of the radius so the
        lit area is large, then rises quickly toward the outer edge.
        """
        size = radius * 2 + 2
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        surf.fill((*color, self.DARK_ALPHA))
        cx = cy = radius + 1
        for r in range(radius, 0, -1):
            t     = r / radius        # 1.0 at edge, 0.0 at centre
            alpha = int(self.DARK_ALPHA * (t ** 5))  # power 5 → tighter bright core
            pygame.draw.circle(surf, (*color, alpha), (cx, cy), r)
        # Guarantee a fully-transparent core
        pygame.draw.circle(surf, (*color, 0), (cx, cy), max(1, radius // 6))
        return surf

    def _punch(self, grad, sx, sy):
        radius = grad.get_width() // 2
        self._surf.blit(grad, (sx - radius, sy - radius),
                        special_flags=pygame.BLEND_RGBA_MIN)

    def draw(self, screen, player, torch_group, camera):
        self._surf.fill((0, 0, 0, self.DARK_ALPHA))
        # Use float world coords for sub-pixel accurate light placement
        px = round(player.fx - camera.x)
        py = round(player.fy - camera.y)
        self._punch(self._pg, px, py)
        for t in torch_group:
            tx, ty = camera.world_to_screen(t.rect.centerx, t.rect.centery)
            self._punch(self._tg, tx, ty)
        screen.blit(self._surf, (0, 0))

class Wall(pygame.sprite.Sprite):
    _H_TOP   = [1, 2, 3, 4]
    _H_MID   = [41, 42, 43, 44]
    _V_LEFT  = [0, 10, 20, 30]
    _V_RIGHT = [5, 15, 25, 35]
    _C_BL    = 40
    _C_BR    = 45

    def __init__(self, x, y, wall_type: str = 'h_mid', horizontal: bool = False):
        super().__init__()
        if wall_type == 'h_mid' and horizontal:
            wall_type = 'h_top'
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        if wall_type == 'h_top':
            idx = random.choice(self._H_TOP)
        elif wall_type == 'v_left':
            idx = random.choice(self._V_LEFT)
        elif wall_type == 'v_right':
            idx = random.choice(self._V_RIGHT)
        elif wall_type == 'corner_bl':
            idx = self._C_BL
        elif wall_type == 'corner_br':
            idx = self._C_BR
        else:
            idx = random.choice(self._H_MID)
        self.image.blit(load_tileset_tile(idx, output_size=TILE_SIZE), (0, 0))
        self.rect = self.image.get_rect(topleft=(x, y))

class Torch(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.frames        = load_assets_by_col('assets/torch/torch.png', 6, 3, 4, 4)
        self.current_frame = 0.0
        self.anim_speed    = 0.06
        self.image         = self.frames[0]
        self.rect          = self.image.get_rect(topleft=(x, y))

    def update(self):
        self.current_frame = (self.current_frame + self.anim_speed) % len(self.frames)
        self.image         = self.frames[int(self.current_frame)]

class Item(pygame.sprite.Sprite):
    """Health flask — restores 5 HP on pickup."""
    HEAL_AMOUNT = 5

    def __init__(self, x, y):
        super().__init__()
        # Load animated red flask frames (flasks_3_1..4)
        self.frames = []
        base = 'assets/items and trap_animation/flasks/'
        for i in range(1, 5):
            try:
                img = pygame.image.load(f'{base}flasks_3_{i}.png').convert_alpha()
                self.frames.append(pygame.transform.scale(img, (80, 80)))
            except Exception:
                fb = pygame.Surface((80, 80), pygame.SRCALPHA)
                fb.fill((220, 60, 60, 200))
                self.frames.append(fb)
        self.current_frame = 0.0
        self.anim_speed    = 0.06
        self.image = self.frames[0]
        self.rect  = self.image.get_rect(center=(x + TILE_SIZE // 2, y + TILE_SIZE // 2))
        self.bob_timer = 0
        self.bob_dir   = 1

    def update(self):
        self.current_frame = (self.current_frame + self.anim_speed) % len(self.frames)
        self.image = self.frames[int(self.current_frame)]
        self.bob_timer += 1
        if self.bob_timer % 4 == 0:
            self.rect.y += self.bob_dir
            if self.bob_timer % 32 == 0:
                self.bob_dir *= -1

class KeyItem(pygame.sprite.Sprite):
    """Animated pickup key. Collected by walking over it; grants player.has_key."""
    def __init__(self, x, y):
        super().__init__()
        base = 'assets/items and trap_animation/keys/'
        self.frames = []
        for i in range(1, 5):
            try:
                img = pygame.image.load(f'{base}keys_1_{i}.png').convert_alpha()
                self.frames.append(pygame.transform.scale(img, (80, 80)))
            except Exception:
                fb = pygame.Surface((80, 80), pygame.SRCALPHA)
                fb.fill((255, 215, 0, 200))
                self.frames.append(fb)
        self.current_frame = 0.0
        self.anim_speed    = 0.08
        self.image = self.frames[0]
        self.rect  = self.image.get_rect(center=(x + TILE_SIZE // 2, y + TILE_SIZE // 2))
        self._bob_timer = 0
        self._bob_dir   = 1

    def update(self):
        self.current_frame = (self.current_frame + self.anim_speed) % len(self.frames)
        self.image = self.frames[int(self.current_frame)]
        self._bob_timer += 1
        if self._bob_timer % 4 == 0:
            self.rect.y += self._bob_dir
            if self._bob_timer % 32 == 0:
                self._bob_dir *= -1


class ExitTile(pygame.sprite.Sprite):
    """Two-tile wooden door from Dungeon_Tileset indices 66 & 67. Visually static."""
    def __init__(self, x, y):
        super().__init__()
        left  = load_tileset_tile(_DOOR_IDX_L, output_size=TILE_SIZE)
        right = load_tileset_tile(_DOOR_IDX_R, output_size=TILE_SIZE)
        self.image = pygame.Surface((TILE_SIZE * 2, TILE_SIZE))
        self.image.blit(left,  (0,         0))
        self.image.blit(right, (TILE_SIZE, 0))
        self.rect  = self.image.get_rect(topleft=(x, y))

    def update(self):
        pass  # Door is intentionally static — no visual change on key pickup


# ---------------------------------------------------------------------------
# Traps
# ---------------------------------------------------------------------------

class SpikeTrap(pygame.sprite.Sprite):
    """
    Animated floor spike trap.  Active (damaging) on frames 1-2 out of 4.
    Tile code 10 in the map grid.
    """
    DAMAGE        = 5.0
    CYCLE_PERIOD  = 90   # frames between activations
    ACTIVE_FRAMES = {1, 2}

    def __init__(self, x, y):
        super().__init__()
        base = 'assets/items and trap_animation/peaks/'
        self.frames = []
        for i in range(1, 5):
            try:
                img = pygame.image.load(f'{base}peaks_{i}.png').convert_alpha()
                self.frames.append(pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE)))
            except Exception:
                fb = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
                fb.fill((180, 30, 30, 200))
                self.frames.append(fb)
        self.current_frame = 0.0
        self.image = self.frames[0]
        self.rect  = self.image.get_rect(topleft=(x, y))
        self._timer    = 0
        self.is_active = False

    @property
    def hitbox(self):
        return self.rect.inflate(-TILE_SIZE // 3, -TILE_SIZE // 3)

    def update(self, player=None):
        self._timer = (self._timer + 1) % self.CYCLE_PERIOD
        # Advance animation based on timer phase
        phase = self._timer / self.CYCLE_PERIOD
        self.current_frame = min(int(phase * len(self.frames)), len(self.frames) - 1)
        self.is_active = (self.current_frame in self.ACTIVE_FRAMES)
        self.image = self.frames[self.current_frame]
        if self.is_active and player and not player.is_dead:
            if self.hitbox.colliderect(player.hitbox):
                player.receive_damage(self.DAMAGE)


class FlamethrowerTrap(pygame.sprite.Sprite):
    """
    Wall-mounted flamethrower.  Damages player while flame frames (1-3) are active.
    Tile code 11 in the map grid.
    """
    DAMAGE        = 3.0
    CYCLE_PERIOD  = 120
    ACTIVE_FRAMES = {1, 2, 3}

    def __init__(self, x, y):
        super().__init__()
        base = 'assets/items and trap_animation/flamethrower/'
        self.frames = []
        for i in range(1, 5):
            try:
                img = pygame.image.load(f'{base}flamethrower_1_{i}.png').convert_alpha()
                self.frames.append(pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE * 2)))
            except Exception:
                fb = pygame.Surface((TILE_SIZE, TILE_SIZE * 2), pygame.SRCALPHA)
                fb.fill((220, 100, 20, 200))
                self.frames.append(fb)
        self.current_frame = 0.0
        self.image = self.frames[0]
        self.rect  = self.image.get_rect(topleft=(x, y - TILE_SIZE))  # extends upward
        self._timer    = 0
        self.is_active = False

    @property
    def hitbox(self):
        return self.rect.inflate(-TILE_SIZE // 4, -TILE_SIZE // 4)

    def update(self, player=None):
        self._timer = (self._timer + 1) % self.CYCLE_PERIOD
        phase = self._timer / self.CYCLE_PERIOD
        self.current_frame = min(int(phase * len(self.frames)), len(self.frames) - 1)
        self.is_active = (self.current_frame in self.ACTIVE_FRAMES)
        self.image = self.frames[self.current_frame]
        if self.is_active and player and not player.is_dead:
            if self.hitbox.colliderect(player.hitbox):
                player.receive_damage(self.DAMAGE)

class HealSpark(pygame.sprite.Sprite):
    """Small glowing orb dropped by enemies on death. Heals HEAL_AMOUNT HP on pickup."""
    HEAL_AMOUNT  = 3
    LIFETIME     = 600   # frames before it fades (10 sec at 60fps)

    def __init__(self, cx, cy):
        super().__init__()
        base = 'assets/items and trap_animation/coin/'
        raw_frames = []
        for i in range(1, 5):
            try:
                img = pygame.image.load(f'{base}coin_{i}.png').convert_alpha()
                raw_frames.append(img)
            except Exception:
                pass
        if not raw_frames:
            fb = pygame.Surface((32, 32), pygame.SRCALPHA)
            pygame.draw.circle(fb, (80, 255, 120, 220), (16, 16), 12)
            raw_frames = [fb]

        # Tint frames green to visually distinguish from coins
        size = TILE_SIZE // 2  # 64px
        self.frames = []
        for raw in raw_frames:
            scaled = pygame.transform.scale(raw, (size, size)).copy()
            tint = pygame.Surface((size, size), pygame.SRCALPHA)
            tint.fill((0, 200, 80, 90))  # green tint overlay
            scaled.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            self.frames.append(scaled)

        self.current_frame = 0.0
        self.anim_speed    = 0.12
        self.image = self.frames[0]
        self.rect  = self.image.get_rect(center=(cx, cy))
        self._bob_timer = 0
        self._bob_dir   = 1
        self._age       = 0

    def update(self):
        self._age += 1
        # Fade out in last 120 frames
        if self._age >= self.LIFETIME:
            self.kill()
            return
        self.current_frame = (self.current_frame + self.anim_speed) % len(self.frames)
        self.image = self.frames[int(self.current_frame)].copy()
        if self._age > self.LIFETIME - 120:
            alpha = int(255 * (self.LIFETIME - self._age) / 120)
            self.image.set_alpha(alpha)
        # Bob up/down
        self._bob_timer += 1
        if self._bob_timer % 4 == 0:
            self.rect.y += self._bob_dir
            if self._bob_timer % 28 == 0:
                self._bob_dir *= -1


def _random_floor_positions(tile_map, count, avoid_px):
    # Filter all walkable floor candidates that respect the avoid_px constraint
    base_candidates = []
    for r, row in enumerate(tile_map):
        for c, tile in enumerate(row):
            if tile == 0:
                tx, ty = c * TILE_SIZE, r * TILE_SIZE
                far_enough = True
                for ax, ay in avoid_px:
                    if abs(tx - ax) <= TILE_SIZE * 3 and abs(ty - ay) <= TILE_SIZE * 3:
                        far_enough = False
                        break
                if far_enough:
                    base_candidates.append((r, c))

    dist_5_candidates = []
    dist_4_candidates = []
    dist_3_candidates = []
    dist_2_candidates = []
    dist_1_candidates = []
    dist_0_candidates = []
    
    rows, cols = len(tile_map), len(tile_map[0])
    for r, c in base_candidates:
        # Check Chebyshev distance to walls (3) and out-of-bounds up to 5 tiles
        max_free_dist = 5
        for dist in range(1, 6):
            has_wall = False
            for dr in range(-dist, dist + 1):
                for dc in range(-dist, dist + 1):
                    nr, nc = r + dr, c + dc
                    if not (0 <= nr < rows and 0 <= nc < cols) or tile_map[nr][nc] == 3:
                        has_wall = True
                        break
                if has_wall:
                    break
            if has_wall:
                max_free_dist = dist - 1
                break
        
        if max_free_dist == 5:
            dist_5_candidates.append((c * TILE_SIZE, r * TILE_SIZE))
        elif max_free_dist == 4:
            dist_4_candidates.append((c * TILE_SIZE, r * TILE_SIZE))
        elif max_free_dist == 3:
            dist_3_candidates.append((c * TILE_SIZE, r * TILE_SIZE))
        elif max_free_dist == 2:
            dist_2_candidates.append((c * TILE_SIZE, r * TILE_SIZE))
        elif max_free_dist == 1:
            dist_1_candidates.append((c * TILE_SIZE, r * TILE_SIZE))
        else:
            dist_0_candidates.append((c * TILE_SIZE, r * TILE_SIZE))

    random.shuffle(dist_5_candidates)
    random.shuffle(dist_4_candidates)
    random.shuffle(dist_3_candidates)
    random.shuffle(dist_2_candidates)

    final_candidates = (
        dist_5_candidates + 
        dist_4_candidates + 
        dist_3_candidates + 
        dist_2_candidates
    )
    return final_candidates[:count]

def build_floor(tile_map):
    map_w = MAP_COLS * TILE_SIZE
    map_h = MAP_ROWS * TILE_SIZE
    surf  = pygame.Surface((map_w, map_h))
    surf.fill((0, 0, 0))

    # Load floor tiles from Dungeon_Tileset.png
    floor_tiles   = [load_tileset_tile(idx, output_size=TILE_SIZE) for idx in _FLOOR_TILE_INDICES]
    floor_weights = _FLOOR_WEIGHTS



    for r, row in enumerate(tile_map):
        for c, tile in enumerate(row):
            if tile != 3:
                x, y = c * TILE_SIZE, r * TILE_SIZE

                # Pick a weighted random floor tile from the dungeon tileset
                base_tile = random.choices(floor_tiles, weights=floor_weights, k=1)[0]
                surf.blit(base_tile, (x, y))

                # tile 7 (water) and tile 8 (bridge) both render as regular floor

    # Add Ambient Occlusion (Shadows) around walls
    shadow_surf = pygame.Surface((map_w, map_h), pygame.SRCALPHA)
    for r, row in enumerate(tile_map):
        for c, tile in enumerate(row):
            if tile == 3:
                x, y = c * TILE_SIZE, r * TILE_SIZE
                # Bottom shadow (Drop shadow)
                if r + 1 < MAP_ROWS and tile_map[r+1][c] != 3:
                    pygame.draw.rect(shadow_surf, (0, 0, 0, 90), (x, y + TILE_SIZE, TILE_SIZE, 12))
                    pygame.draw.rect(shadow_surf, (0, 0, 0, 45), (x, y + TILE_SIZE + 12, TILE_SIZE, 12))
                # Right shadow
                if c + 1 < MAP_COLS and tile_map[r][c+1] != 3:
                    pygame.draw.rect(shadow_surf, (0, 0, 0, 70), (x + TILE_SIZE, y, 12, TILE_SIZE))
                    pygame.draw.rect(shadow_surf, (0, 0, 0, 30), (x + TILE_SIZE + 12, y, 12, TILE_SIZE))
                # Left shadow
                if c - 1 >= 0 and tile_map[r][c-1] != 3:
                    pygame.draw.rect(shadow_surf, (0, 0, 0, 70), (x - 12, y, 12, TILE_SIZE))
                    pygame.draw.rect(shadow_surf, (0, 0, 0, 30), (x - 24, y, 12, TILE_SIZE))
                # Top shadow
                if r - 1 >= 0 and tile_map[r-1][c] != 3:
                    pygame.draw.rect(shadow_surf, (0, 0, 0, 70), (x, y - 12, TILE_SIZE, 12))
                    pygame.draw.rect(shadow_surf, (0, 0, 0, 30), (x, y - 24, TILE_SIZE, 12))

    surf.blit(shadow_surf, (0, 0))

    # Darker border outside the play area
    pygame.draw.rect(surf, (20, 16, 14), (0, 0, map_w, map_h), 12)
    return surf

def draw_group_with_camera(surface, group, camera):
    for sprite in group:
        sx, sy = camera.world_to_screen(sprite.rect.x, sprite.rect.y)
        if -sprite.rect.width < sx < SCREEN_WIDTH and -sprite.rect.height < sy < SCREEN_HEIGHT:
            surface.blit(sprite.image, (sx, sy))
