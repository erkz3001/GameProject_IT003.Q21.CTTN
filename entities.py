import pygame
import random
from settings import C_WHITE, F_SMALL, F_TINY, MAP_COLS, MAP_ROWS, SCREEN_WIDTH, TILE_SIZE
import audio
from utils import load_assets_by_row, load_strip
from world import move_with_wall_collision, clamp_map
from pathfinding import astar, px_to_tile, tile_center

PATH_REPATH = 30

class Player(pygame.sprite.Sprite):
    MAX_STAMINA       = 700
    SPRINT_COOLDOWN   = 180   # 4 seconds at 60 fps
    ATTACK_DMG   = 3.6
    ATTACK_RANGE = 100
    INV_FRAMES   = 90

    def __init__(self, x, y, max_hp=20):
        super().__init__()
        self.max_hp = max_hp
        self.animations = {
            'attack_down':  load_assets_by_row('assets/player/attack.png',  8, 0, 4, 4),
            'attack_left':  load_assets_by_row('assets/player/attack.png',  8, 1, 4, 4),
            'attack_right': load_assets_by_row('assets/player/attack.png',  8, 2, 4, 4),
            'attack_up':    load_assets_by_row('assets/player/attack.png',  8, 3, 4, 4),
            'death_down':   load_assets_by_row('assets/player/death.png',   8, 0, 4, 4),
            'death_left':   load_assets_by_row('assets/player/death.png',   8, 1, 4, 4),
            'death_right':  load_assets_by_row('assets/player/death.png',   8, 2, 4, 4),
            'death_up':     load_assets_by_row('assets/player/death.png',   8, 3, 4, 4),
            'hurt_down':    load_assets_by_row('assets/player/hurt.png',    5, 0, 4, 4),
            'hurt_left':    load_assets_by_row('assets/player/hurt.png',    5, 1, 4, 4),
            'hurt_right':   load_assets_by_row('assets/player/hurt.png',    5, 2, 4, 4),
            'hurt_up':      load_assets_by_row('assets/player/hurt.png',    5, 3, 4, 4),
            'walk_down':    load_assets_by_row('assets/player/walk.png',    6, 0, 4, 4),
            'walk_left':    load_assets_by_row('assets/player/walk.png',    6, 1, 4, 4),
            'walk_right':   load_assets_by_row('assets/player/walk.png',    6, 2, 4, 4),
            'walk_up':      load_assets_by_row('assets/player/walk.png',    6, 3, 4, 4),
            'run_down':     load_assets_by_row('assets/player/run.png',     8, 0, 4, 4),
            'run_left':     load_assets_by_row('assets/player/run.png',     8, 1, 4, 4),
            'run_right':    load_assets_by_row('assets/player/run.png',     8, 2, 4, 4),
            'run_up':       load_assets_by_row('assets/player/run.png',     8, 3, 4, 4),
            'idle_down':    load_assets_by_row('assets/player/idle.png',   12, 0, 4, 4),
            'idle_left':    load_assets_by_row('assets/player/idle.png',   12, 1, 4, 4),
            'idle_right':   load_assets_by_row('assets/player/idle.png',   12, 2, 4, 4),
            'idle_up':      load_assets_by_row('assets/player/idle.png',   12, 3, 4, 4),
        }
        self.hp             = max_hp
        self.stamina        = self.MAX_STAMINA
        self.stamina_max    = self.MAX_STAMINA
        self.sprint_cooldown  = 0      # frames remaining before sprint is available
        self._was_sprinting   = False  # track sprint→idle transition
        self.state          = 'idle_down'
        self.last_direction = 'down'
        self.current_frame  = 0.0
        self.anim_speed     = 0.12
        self.speed          = 5
        self.velocity       = pygame.math.Vector2(0, 0)
        self.is_dead        = False
        self.invincible_timer = 0
        self.attack_hit_set = set()
        self.image  = self.animations[self.state][0]
        self.rect   = self.image.get_rect()
        # Hitbox is tile-aligned: slightly smaller than one tile so the player
        # can walk flush against walls without a large visual gap.
        _hb_size = TILE_SIZE - 16   # 112 px — 8px margin on each side
        self.hitbox = pygame.Rect(0, 0, _hb_size, _hb_size)
        self.hitbox.center = (x + TILE_SIZE // 2, y + TILE_SIZE // 2)
        self.rect.center = self.hitbox.center
        # Float-precision world position for smooth lighting
        self.fx = float(self.hitbox.centerx)
        self.fy = float(self.hitbox.centery)
        self.has_key = False
        self.walk_sound_timer = 0

    def change_state(self, new_state):
        if self.state != new_state and new_state in self.animations:
            self.state         = new_state
            self.current_frame = 0.0

    def receive_damage(self, amount):
        if self.is_dead or self.invincible_timer > 0:
            return
        self.hp               = max(0, self.hp - amount)
        self.invincible_timer = self.INV_FRAMES
        audio.play('player_hurt')
        if self.hp == 0:
            self.is_dead = True
            self.change_state('death_' + self.last_direction)
        else:
            self.change_state('hurt_' + self.last_direction)

    def get_attack_rect(self):
        R, W, H = self.ATTACK_RANGE, 110, 90
        cx, cy  = self.hitbox.centerx, self.hitbox.centery
        d       = self.last_direction
        if d == 'right': return pygame.Rect(cx,          cy - H // 2, R, H)
        if d == 'left':  return pygame.Rect(cx - R,      cy - H // 2, R, H)
        if d == 'down':  return pygame.Rect(cx - W // 2, cy,          W, R)
        return               pygame.Rect(cx - W // 2, cy - R,      W, R)

    def _handle_input(self):
        if self.is_dead or 'attack' in self.state or 'hurt' in self.state:
            self.velocity.update(0, 0)
            return
        keys = pygame.key.get_pressed()
        if keys[pygame.K_j]:
            self.anim_speed = 0.25
            self.change_state('attack_' + self.last_direction)
            self.attack_hit_set = set()
            self.velocity.update(0, 0)
            audio.play('player_attack')
            return
        self.anim_speed = 0.12
        # Tick sprint cooldown
        if self.sprint_cooldown > 0:
            self.sprint_cooldown -= 1
        can_sprint = (self.sprint_cooldown == 0 and self.stamina > 50)
        if keys[pygame.K_LSHIFT] and can_sprint:
            self.stamina = max(0, self.stamina - 7)
            spd, prefix  = self.speed * 1.25, 'run_'
            self._was_sprinting = True
        else:
            # Sprint just ended → start 4-second cooldown
            if self._was_sprinting:
                self.sprint_cooldown = self.SPRINT_COOLDOWN
                self._was_sprinting  = False
            self.stamina = min(self.stamina_max, self.stamina + 3)
            spd, prefix  = self.speed, 'walk_'
        dx = dy = 0.0
        if keys[pygame.K_a]: dx = -1.0
        if keys[pygame.K_d]: dx =  1.0
        if keys[pygame.K_w]: dy = -1.0
        if keys[pygame.K_s]: dy =  1.0
        if dx and dy:
            dx *= 0.707; dy *= 0.707
        self.velocity.update(dx * spd, dy * spd)
        if dx or dy:
            if   dx < 0: self.last_direction = 'left'
            elif dx > 0: self.last_direction = 'right'
            elif dy < 0: self.last_direction = 'up'
            else:        self.last_direction = 'down'
            self.change_state(prefix + self.last_direction)
        else:
            self.change_state('idle_' + self.last_direction)

    def _apply_animation(self):
        anim = self.animations[self.state]
        self.current_frame += self.anim_speed
        if self.current_frame >= len(anim):
            if   'death'  in self.state: self.current_frame = len(anim) - 1
            elif 'attack' in self.state:
                self.attack_hit_set = set()
                self.change_state('idle_' + self.last_direction)
            elif 'hurt'   in self.state: self.change_state('idle_' + self.last_direction)
            else:                        self.current_frame = 0.0
        self.image = anim[int(min(self.current_frame, len(anim) - 1))]

    def update(self, walls_group, slime_group, mob_group=None):
        self._handle_input()
        if self.invincible_timer > 0:
            self.invincible_timer -= 1

        # Physics: use the proven sequential X-then-Y resolver (corner-slide safe)
        move_with_wall_collision(self.hitbox, self.velocity.x, self.velocity.y, walls_group)
        clamp_map(self.hitbox)
        # Sync float world coords from resolved integer hitbox (used by fog only)
        self.fx = float(self.hitbox.centerx)
        self.fy = float(self.hitbox.centery)

        # Play walk sound at regular intervals when moving
        if ('walk' in self.state or 'run' in self.state) and self.velocity.length_squared() > 0:
            if self.walk_sound_timer <= 0:
                audio.play('player_walk')
                self.walk_sound_timer = 18 if 'run' in self.state else 26
            else:
                self.walk_sound_timer -= 1
        else:
            self.walk_sound_timer = 0

        if 'attack' in self.state and 3 <= int(self.current_frame) <= 6:
            atk = self.get_attack_rect()
            all_enemies = list(slime_group) + (list(mob_group) if mob_group else [])
            for enemy in all_enemies:
                if enemy not in self.attack_hit_set and atk.colliderect(enemy.hitbox):
                    enemy.receive_damage(self.ATTACK_DMG)
                    self.attack_hit_set.add(enemy)
        self._apply_animation()
        self.rect.center = self.hitbox.center

    def draw_hud(self, surface):
        bx, by, bw, bh = 30, 28, 300, 26
        pygame.draw.rect(surface, (80, 0, 0),     (bx, by, bw, bh))
        pygame.draw.rect(surface, (220, 40, 40),  (bx, by, int(bw * self.hp / self.max_hp), bh))
        pygame.draw.rect(surface, (240,240,240),  (bx, by, bw, bh), 2)
        surface.blit(F_SMALL.render(f'HP  {self.hp}/{self.max_hp}', True, C_WHITE),
                     (bx + bw + 10, by + 3))
        sx, sy, sw, sh = 30, 62, 200, 16
        on_cooldown = self.sprint_cooldown > 0
        bar_bg  = (40, 40, 80)  if on_cooldown else (0, 60, 0)
        bar_fg  = (80, 120, 200) if on_cooldown else (40, 200, 40)
        pygame.draw.rect(surface, bar_bg, (sx, sy, sw, sh))
        fill_w = int(sw * self.stamina / self.stamina_max)
        pygame.draw.rect(surface, bar_fg, (sx, sy, fill_w, sh))
        pygame.draw.rect(surface, (180,180,180), (sx, sy, sw, sh), 1)
        if on_cooldown:
            secs_left = max(0, self.sprint_cooldown / 60)
            cd_surf = F_TINY.render(f'Sprint CD  {secs_left:.1f}s', True, (160, 180, 255))
            surface.blit(cd_surf, (sx + sw + 8, sy))
        hint = F_TINY.render('WASD = Move    J = Attack    Shift = Sprint', True, (180,180,180))
        surface.blit(hint, (SCREEN_WIDTH - hint.get_width() - 20, 10))
        mhint = F_TINY.render(f'Map: {MAP_COLS}×{MAP_ROWS} tiles', True, (100, 100, 100))
        surface.blit(mhint, (SCREEN_WIDTH - mhint.get_width() - 20, 38))
        key_color = (255, 215, 0) if self.has_key else (100, 100, 100)
        key_text = 'Key: Acquired' if self.has_key else 'Key: Missing'
        k_surf = F_SMALL.render(key_text, True, key_color)
        surface.blit(k_surf, (30, 90))

class Slime(pygame.sprite.Sprite):
    ATTACK_RANGE    = 100
    ATTACK_COOLDOWN = 120

    def __init__(self, x, y, cfg):
        super().__init__()
        self.MAX_HP     = cfg['slime_hp']
        self.ATTACK_DMG = cfg['slime_dmg']
        self.WALK_SPEED = cfg['slime_walk']
        self.RUN_SPEED  = cfg['slime_run']
        self.DETECTION  = cfg['detection']
        self.LOSE_RANGE = cfg['lose_range']
        self.animations = {
            'attack_down':  load_assets_by_row('assets/slime/attack.png', 11, 0, 4, 4),
            'attack_up':    load_assets_by_row('assets/slime/attack.png', 11, 1, 4, 4),
            'attack_left':  load_assets_by_row('assets/slime/attack.png', 11, 2, 4, 4),
            'attack_right': load_assets_by_row('assets/slime/attack.png', 11, 3, 4, 4),
            'death_down':   load_assets_by_row('assets/slime/death.png',  10, 0, 4, 4),
            'death_up':     load_assets_by_row('assets/slime/death.png',  10, 1, 4, 4),
            'death_left':   load_assets_by_row('assets/slime/death.png',  10, 2, 4, 4),
            'death_right':  load_assets_by_row('assets/slime/death.png',  10, 3, 4, 4),
            'hurt_down':    load_assets_by_row('assets/slime/hurt.png',    5, 0, 4, 4),
            'hurt_up':      load_assets_by_row('assets/slime/hurt.png',    5, 1, 4, 4),
            'hurt_left':    load_assets_by_row('assets/slime/hurt.png',    5, 2, 4, 4),
            'hurt_right':   load_assets_by_row('assets/slime/hurt.png',    5, 3, 4, 4),
            'walk_down':    load_assets_by_row('assets/slime/walk.png',    8, 0, 4, 4),
            'walk_up':      load_assets_by_row('assets/slime/walk.png',    8, 1, 4, 4),
            'walk_left':    load_assets_by_row('assets/slime/walk.png',    8, 2, 4, 4),
            'walk_right':   load_assets_by_row('assets/slime/walk.png',    8, 3, 4, 4),
            'run_down':     load_assets_by_row('assets/slime/run.png',     8, 0, 4, 4),
            'run_up':       load_assets_by_row('assets/slime/run.png',     8, 1, 4, 4),
            'run_left':     load_assets_by_row('assets/slime/run.png',     8, 2, 4, 4),
            'run_right':    load_assets_by_row('assets/slime/run.png',     8, 3, 4, 4),
            'idle_down':    load_assets_by_row('assets/slime/idle.png',    6, 0, 4, 4),
            'idle_up':      load_assets_by_row('assets/slime/idle.png',    6, 1, 4, 4),
            'idle_left':    load_assets_by_row('assets/slime/idle.png',    6, 2, 4, 4),
            'idle_right':   load_assets_by_row('assets/slime/idle.png',    6, 3, 4, 4),
        }
        self.hp             = self.MAX_HP
        self.ai_state       = 'wander'
        self.anim_key       = 'idle_down'
        self.last_direction = 'down'
        self.current_frame  = 0.0
        self.anim_speed     = 0.15
        self.image  = self.animations[self.anim_key][0]
        self.rect   = self.image.get_rect()
        # Hitbox: tile-sized with a small margin, matching player collision feel.
        _hb_size = TILE_SIZE - 16
        self.hitbox = pygame.Rect(0, 0, _hb_size, _hb_size)
        self.hitbox.center = (x + TILE_SIZE // 2, y + TILE_SIZE // 2)
        self.rect.center = self.hitbox.center
        self.wander_timer        = 0
        self.move_dir            = pygame.math.Vector2(0, 0)
        self.is_dead             = False
        self.attack_cooldown     = 0
        self.attack_damage_dealt = False
        self.hurt_timer          = 0
        self.path                = []
        self.path_timer          = 0
        self.kill_callback       = None
        self.drop_callback       = None   # fn(cx, cy) → spawn HealSpark

    def kill(self):
        if self.kill_callback:
            self.kill_callback()
        if self.drop_callback and random.random() < 0.45:
            self.drop_callback(self.hitbox.centerx, self.hitbox.centery)
        super().kill()

    def _change_anim(self, key):
        if self.anim_key != key and key in self.animations:
            self.anim_key      = key
            self.current_frame = 0.0

    def receive_damage(self, amount):
        if self.is_dead or self.hurt_timer > 0:
            return
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0; self.is_dead = True; self.ai_state = 'dead'
            self._change_anim('death_' + self.last_direction)
            audio.play('monster_death')
        else:
            self.ai_state = 'hurt'; self.hurt_timer = 25
            self._change_anim('hurt_' + self.last_direction)
            audio.play('mob_damaged')

    def _dir_from_vec(self, v):
        if abs(v.x) > abs(v.y):
            self.last_direction = 'right' if v.x > 0 else 'left'
        elif v.y != 0:
            self.last_direction = 'down'  if v.y > 0 else 'up'

    def _run_anim(self):
        anim = self.animations.get(self.anim_key)
        if not anim: return
        self.current_frame += self.anim_speed
        if self.current_frame >= len(anim):
            if 'attack' in self.anim_key:
                self.ai_state = 'chase'
                self.attack_cooldown = self.ATTACK_COOLDOWN
                self.attack_damage_dealt = False
                self._change_anim('idle_' + self.last_direction)
            elif 'hurt' not in self.anim_key and 'death' not in self.anim_key:
                self.current_frame = 0.0
        self.image = anim[int(min(self.current_frame, len(anim) - 1))]

    def _wander(self, walls_group):
        self.wander_timer -= 1
        if self.wander_timer <= 0:
            choices = [(0,1,'down'),(0,-1,'up'),(1,0,'right'),(-1,0,'left'),(0,0,'idle')]
            dx, dy, act = random.choice(choices)
            self.move_dir.update(dx, dy)
            if act != 'idle':
                self.last_direction = act
                self._change_anim('walk_' + self.last_direction)
            else:
                self._change_anim('idle_' + self.last_direction)
            self.wander_timer = random.randint(60, 180)
        move_with_wall_collision(self.hitbox,
                                 self.move_dir.x * self.WALK_SPEED,
                                 self.move_dir.y * self.WALK_SPEED,
                                 walls_group)
        clamp_map(self.hitbox)

    def _chase(self, player, walls_group, nav_grid):
        self.path_timer -= 1
        if self.path_timer <= 0 or not self.path:
            start = px_to_tile(self.hitbox.centerx,   self.hitbox.centery, TILE_SIZE)
            goal  = px_to_tile(player.hitbox.centerx, player.hitbox.centery, TILE_SIZE)
            self.path       = astar(start, goal, nav_grid)
            self.path_timer = PATH_REPATH
        if self.path:
            tx, ty = tile_center(self.path[0][0], self.path[0][1], TILE_SIZE)
            delta  = pygame.math.Vector2(tx - self.hitbox.centerx, ty - self.hitbox.centery)
            if delta.length() < 24:
                self.path.pop(0)
            direction = delta.normalize() if delta.length() > 0 else pygame.math.Vector2(0, 1)
        else:
            d = pygame.math.Vector2(player.hitbox.centerx - self.hitbox.centerx,
                                    player.hitbox.centery - self.hitbox.centery)
            direction = d.normalize() if d.length() > 0 else pygame.math.Vector2(0, 1)
        self._dir_from_vec(direction)
        self._change_anim('run_' + self.last_direction)
        move_with_wall_collision(self.hitbox,
                                 direction.x * self.RUN_SPEED,
                                 direction.y * self.RUN_SPEED,
                                 walls_group)
        clamp_map(self.hitbox)

    def _attack(self, delta, player):
        if 'attack' not in self.anim_key:
            self._dir_from_vec(delta)
            self._change_anim('attack_' + self.last_direction)
            self.attack_damage_dealt = False
            audio.play('slime_attack')
        if not self.attack_damage_dealt and int(self.current_frame) >= 5:
            if player and self.hitbox.colliderect(player.hitbox.inflate(60, 60)):
                player.receive_damage(self.ATTACK_DMG)
            self.attack_damage_dealt = True

    def update(self, player_group, walls_group, nav_grid):
        player = player_group.sprite
        if self.ai_state == 'dead':
            self._run_anim()
            anim = self.animations.get(self.anim_key, [])
            if self.current_frame >= len(anim) - 1:
                self.kill()
            self.rect.center = self.hitbox.center
            return
        if self.ai_state == 'hurt':
            self.hurt_timer -= 1
            if self.hurt_timer <= 0:
                self.ai_state = 'chase'
                self._change_anim('idle_' + self.last_direction)
            self._run_anim()
            self.rect.center = self.hitbox.center
            return
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        if player and not player.is_dead:
            delta    = pygame.math.Vector2(
                player.hitbox.centerx - self.hitbox.centerx,
                player.hitbox.centery - self.hitbox.centery)
            distance = delta.length()
        else:
            delta    = pygame.math.Vector2(0, 0)
            distance = float('inf')
        if self.ai_state == 'wander' and distance < self.DETECTION:
            self.ai_state = 'chase'
        elif self.ai_state == 'chase':
            if distance > self.LOSE_RANGE:
                self.ai_state = 'wander'; self.path = []; self.path_timer = 0
            elif distance < self.ATTACK_RANGE and self.attack_cooldown <= 0:
                self.ai_state = 'attack'
        if   self.ai_state == 'wander': self._wander(walls_group)
        elif self.ai_state == 'chase':  self._chase(player, walls_group, nav_grid)
        elif self.ai_state == 'attack': self._attack(delta, player)
        self._run_anim()
        self.rect.center = self.hitbox.center

    def draw_hp_bar(self, surface, camera):
        if 0 < self.hp < self.MAX_HP and not self.is_dead:
            bw, bh = 70, 7
            sx, sy = camera.world_to_screen(self.rect.centerx - bw // 2, self.rect.top - 14)
            pygame.draw.rect(surface, (150,30,30),  (sx, sy, bw, bh))
            pygame.draw.rect(surface, (55,210,55),  (sx, sy, int(bw * self.hp / self.MAX_HP), bh))
            pygame.draw.rect(surface, (0,0,0),      (sx, sy, bw, bh), 1)


# ---------------------------------------------------------------------------
# New mob base class (used by Skeleton, HeavySkeleton, Vampire)
# ---------------------------------------------------------------------------

SPRITE_SRC_W  = 32   # source sprite width  (pixels per frame)
SPRITE_SRC_H  = 32   # source sprite height
SPRITE_OUT_W  = TILE_SIZE
SPRITE_OUT_H  = TILE_SIZE


class BaseMob(pygame.sprite.Sprite):
    """
    Shared base for new strip-based enemy sprites.
    Animations are single-direction strips; we flip horizontally for left-facing.
    """
    MAX_HP          = 20
    ATTACK_DMG      = 4.0
    WALK_SPEED      = 3
    RUN_SPEED       = 5
    DETECTION       = 380
    LOSE_RANGE      = 560
    ATTACK_RANGE    = 110
    ATTACK_COOLDOWN = 120
    ASSET_DIR       = ''   # override in subclass

    def __init__(self, x, y, cfg):
        super().__init__()
        # Allow difficulty config to override base stats
        self.MAX_HP        = cfg.get('mob_hp',    self.MAX_HP)
        self.ATTACK_DMG    = cfg.get('mob_dmg',   self.ATTACK_DMG)
        self.WALK_SPEED    = cfg.get('slime_walk', self.WALK_SPEED)
        self.RUN_SPEED     = cfg.get('slime_run',  self.RUN_SPEED)
        self.DETECTION     = cfg.get('detection',  self.DETECTION)
        self.LOSE_RANGE    = cfg.get('lose_range', self.LOSE_RANGE)
        self.hp            = self.MAX_HP
        self.kill_callback = None
        self.drop_callback = None   # fn(cx, cy) → spawn HealSpark
        self.is_dead       = False
        self.ai_state      = 'wander'
        self.last_direction = 'right'
        self.attack_cooldown     = 0
        self.attack_damage_dealt = False
        self.hurt_timer          = 0
        self.wander_timer        = 0
        self.move_dir            = pygame.math.Vector2(0, 0)
        self.path                = []
        self.path_timer          = 0
        self._anim_key   = 'idle'
        self._frame      = 0.0
        self._flipped    = False
        self._load_animations()
        self.image  = self.anims.get('idle_r', list(self.anims.values())[0])[0]
        self.rect   = self.image.get_rect()
        self.hitbox = self.rect.inflate(-SPRITE_OUT_W // 2, -SPRITE_OUT_H // 3)
        self.hitbox.center = (x + TILE_SIZE // 2, y + TILE_SIZE // 2)
        self.rect.center = self.hitbox.center

    def _load_animations(self):
        """Subclasses define ASSET_DIR and frame file patterns."""
        raise NotImplementedError

    def _load_strip_pair(self, path, src_w=SPRITE_SRC_W, src_h=SPRITE_SRC_H):
        """Return (right_frames, left_frames) for a strip."""
        right = load_strip(path, src_w, src_h, SPRITE_OUT_W, SPRITE_OUT_H, flipped=False)
        left  = load_strip(path, src_w, src_h, SPRITE_OUT_W, SPRITE_OUT_H, flipped=True)
        return right, left

    def kill(self):
        if self.kill_callback:
            self.kill_callback()
        if self.drop_callback and random.random() < 0.45:
            self.drop_callback(self.hitbox.centerx, self.hitbox.centery)
        super().kill()

    def receive_damage(self, amount):
        if self.is_dead or self.hurt_timer > 0:
            return
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.is_dead    = True
            self.ai_state   = 'dead'
            self._set_anim('death')
            audio.play('monster_death')
        else:
            self.ai_state  = 'hurt'
            self.hurt_timer = 25
            self._set_anim('hurt')
            audio.play('mob_damaged')

    def _set_anim(self, key):
        if self._anim_key != key:
            self._anim_key = key
            self._frame    = 0.0

    def _get_frames(self):
        """Return current frame list respecting left/right flip."""
        key = self._anim_key
        if self._flipped:
            return self.anims.get(key + '_l', self.anims.get(key, [self.image]))
        return self.anims.get(key + '_r',     self.anims.get(key, [self.image]))

    def _run_anim(self, speed=0.15):
        frames = self._get_frames()
        self._frame += speed
        if self._frame >= len(frames):
            if self._anim_key in ('death',):
                self._frame = len(frames) - 1
            elif self._anim_key == 'attack':
                self.ai_state = 'chase'
                self.attack_cooldown     = self.ATTACK_COOLDOWN
                self.attack_damage_dealt = False
                self._set_anim('idle')
            elif self._anim_key == 'hurt':
                pass  # hurt_timer controls transition
            else:
                self._frame = 0.0
        self.image = frames[int(min(self._frame, len(frames) - 1))]

    def _wander(self, walls_group):
        self.wander_timer -= 1
        if self.wander_timer <= 0:
            choices = [(0,1),(0,-1),(1,0),(-1,0),(0,0)]
            dx, dy = random.choice(choices)
            self.move_dir.update(dx, dy)
            if dx != 0 or dy != 0:
                self._flipped = (dx < 0)
                self._set_anim('walk')
            else:
                self._set_anim('idle')
            self.wander_timer = random.randint(60, 180)
        move_with_wall_collision(self.hitbox,
                                 self.move_dir.x * self.WALK_SPEED,
                                 self.move_dir.y * self.WALK_SPEED,
                                 walls_group)
        clamp_map(self.hitbox)

    def _chase(self, player, walls_group, nav_grid):
        self.path_timer -= 1
        if self.path_timer <= 0 or not self.path:
            start = px_to_tile(self.hitbox.centerx,   self.hitbox.centery, TILE_SIZE)
            goal  = px_to_tile(player.hitbox.centerx, player.hitbox.centery, TILE_SIZE)
            self.path       = astar(start, goal, nav_grid)
            self.path_timer = PATH_REPATH
        if self.path:
            tx, ty = tile_center(self.path[0][0], self.path[0][1], TILE_SIZE)
            delta  = pygame.math.Vector2(tx - self.hitbox.centerx, ty - self.hitbox.centery)
            if delta.length() < 24:
                self.path.pop(0)
            direction = delta.normalize() if delta.length() > 0 else pygame.math.Vector2(1, 0)
        else:
            d = pygame.math.Vector2(player.hitbox.centerx - self.hitbox.centerx,
                                    player.hitbox.centery - self.hitbox.centery)
            direction = d.normalize() if d.length() > 0 else pygame.math.Vector2(1, 0)
        self._flipped = (direction.x < 0)
        self._set_anim('run')
        move_with_wall_collision(self.hitbox,
                                 direction.x * self.RUN_SPEED,
                                 direction.y * self.RUN_SPEED,
                                 walls_group)
        clamp_map(self.hitbox)

    def _attack(self, delta, player):
        self._flipped = (delta.x < 0)
        if self._anim_key != 'attack':
            self._set_anim('attack')
            self.attack_damage_dealt = False
        if not self.attack_damage_dealt and int(self._frame) >= 4:
            if player and self.hitbox.colliderect(player.hitbox.inflate(60, 60)):
                player.receive_damage(self.ATTACK_DMG)
            self.attack_damage_dealt = True

    def update(self, player_group, walls_group, nav_grid):
        player = player_group.sprite
        if self.ai_state == 'dead':
            self._run_anim(speed=0.12)
            frames = self._get_frames()
            if self._frame >= len(frames) - 1:
                self.kill()
            self.rect.center = self.hitbox.center
            return
        if self.ai_state == 'hurt':
            self.hurt_timer -= 1
            if self.hurt_timer <= 0:
                self.ai_state = 'chase'
                self._set_anim('idle')
            self._run_anim(speed=0.2)
            self.rect.center = self.hitbox.center
            return
        if self.attack_cooldown > 0:
            self.attack_cooldown -= 1
        if player and not player.is_dead:
            delta    = pygame.math.Vector2(
                player.hitbox.centerx - self.hitbox.centerx,
                player.hitbox.centery - self.hitbox.centery)
            distance = delta.length()
        else:
            delta    = pygame.math.Vector2(0, 0)
            distance = float('inf')
        if self.ai_state == 'wander' and distance < self.DETECTION:
            self.ai_state = 'chase'
        elif self.ai_state == 'chase':
            if distance > self.LOSE_RANGE:
                self.ai_state = 'wander'; self.path = []; self.path_timer = 0
            elif distance < self.ATTACK_RANGE and self.attack_cooldown <= 0:
                self.ai_state = 'attack'
        if   self.ai_state == 'wander': self._wander(walls_group)
        elif self.ai_state == 'chase':  self._chase(player, walls_group, nav_grid)
        elif self.ai_state == 'attack': self._attack(delta, player)
        self._run_anim()
        self.rect.center = self.hitbox.center

    def draw_hp_bar(self, surface, camera):
        if 0 < self.hp < self.MAX_HP and not self.is_dead:
            bw, bh = 70, 7
            sx, sy = camera.world_to_screen(self.rect.centerx - bw // 2, self.rect.top - 14)
            pygame.draw.rect(surface, (150, 30, 30), (sx, sy, bw, bh))
            pygame.draw.rect(surface, (55, 210, 55), (sx, sy, int(bw * self.hp / self.MAX_HP), bh))
            pygame.draw.rect(surface, (0, 0, 0),     (sx, sy, bw, bh), 1)


# ---------------------------------------------------------------------------
# Concrete mob classes
# ---------------------------------------------------------------------------

class Skeleton(BaseMob):
    """Skeleton Warrior (mob_version1 skeleton1). Fast, light."""
    MAX_HP       = 18
    ATTACK_DMG   = 3.5
    WALK_SPEED   = 3
    RUN_SPEED    = 5
    ATTACK_RANGE = 110

    def _load_animations(self):
        d = 'assets/Enemy_Animations_Set/enemies-skeleton1_'
        ir, il = self._load_strip_pair(d + 'idle.png')
        wr, wl = self._load_strip_pair(d + 'movement.png')
        ar, al = self._load_strip_pair(d + 'attack.png')
        hr, hl = self._load_strip_pair(d + 'take_damage.png')
        dr, dl = self._load_strip_pair(d + 'death.png')
        self.anims = {
            'idle_r': ir, 'idle_l': il,
            'walk_r': wr, 'walk_l': wl,
            'run_r':  wr, 'run_l':  wl,   # reuse walk for run
            'attack_r': ar, 'attack_l': al,
            'hurt_r': hr, 'hurt_l': hl,
            'death_r': dr, 'death_l': dl,
        }


class HeavySkeleton(BaseMob):
    """Heavy Skeleton (mob_version1 skeleton2). Slower, tankier."""
    MAX_HP       = 30
    ATTACK_DMG   = 6.0
    WALK_SPEED   = 2
    RUN_SPEED    = 4
    ATTACK_RANGE = 120
    ATTACK_COOLDOWN = 150

    def _load_animations(self):
        d = 'assets/Enemy_Animations_Set/enemies-skeleton2_'
        ir, il = self._load_strip_pair(d + 'idle.png')
        wr, wl = self._load_strip_pair(d + 'movemen.png')
        ar, al = self._load_strip_pair(d + 'attack.png')
        hr, hl = self._load_strip_pair(d + 'take_damage.png')
        dr, dl = self._load_strip_pair(d + 'death.png')
        self.anims = {
            'idle_r': ir, 'idle_l': il,
            'walk_r': wr, 'walk_l': wl,
            'run_r':  wr, 'run_l':  wl,
            'attack_r': ar, 'attack_l': al,
            'hurt_r': hr, 'hurt_l': hl,
            'death_r': dr, 'death_l': dl,
        }


class Vampire(BaseMob):
    """Vampire (mob_version1 vampire). Fast, high-combo attacker."""
    MAX_HP       = 22
    ATTACK_DMG   = 5.0
    WALK_SPEED   = 4
    RUN_SPEED    = 7
    ATTACK_RANGE = 100
    DETECTION    = 450

    def _load_animations(self):
        d = 'assets/Enemy_Animations_Set/enemies-vampire_'
        ir, il = self._load_strip_pair(d + 'idle.png')
        wr, wl = self._load_strip_pair(d + 'movement.png')
        ar, al = self._load_strip_pair(d + 'attack.png')
        hr, hl = self._load_strip_pair(d + 'take_damage.png')
        dr, dl = self._load_strip_pair(d + 'death.png')
        self.anims = {
            'idle_r': ir, 'idle_l': il,
            'walk_r': wr, 'walk_l': wl,
            'run_r':  wr, 'run_l':  wl,
            'attack_r': ar, 'attack_l': al,
            'hurt_r': hr, 'hurt_l': hl,
            'death_r': dr, 'death_l': dl,
        }
