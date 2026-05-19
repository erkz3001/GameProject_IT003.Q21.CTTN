import pygame
import pygame_menu
import random
import audio
import settings

from sys import exit
from settings import (SCREEN_WIDTH, SCREEN_HEIGHT, FPS, C_BG, C_WHITE, C_GREY, C_GOLD, C_RED, C_GREEN,
                      F_HUGE, F_MED, F_SMALL, F_TINY, DIFF, TILE_SIZE, MAP_ROWS, MAP_COLS)
from utils import draw_panel, draw_text_with_shadow
from maps import get_random_map, create_nav_grid, add_traps, place_door_and_key
from world import (FogOfWar, Wall, Torch, Item, ExitTile, KeyItem, Camera,
                   build_floor, _random_floor_positions, SpikeTrap, FlamethrowerTrap,
                   HealSpark)
from entities import Player, Slime, Skeleton, HeavySkeleton, Vampire

# Initialize screen
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('Dungeon Escape')
clock  = pygame.time.Clock()

# Global stats
stats = {'killed': 0, 'start_ms': 0, 'end_ms': 0}

def slime_killed_callback():
    stats['killed'] += 1

def _classify_wall(tile_map, r, c):
    """
        Phân loại tường
        Input : tọa độ (r, c) của tường
        Output : loại tường
    Priority:
      corner_bl  — left edge AND bottom edge
      corner_br  — right edge AND bottom edge
      v_left     — left edge  (void/OOB to left, room interior to right)
      v_right    — right edge (void/OOB to right, room interior to left)
      h_top      — topmost horizontal
      h_mid      — lower horizontal / inner
    """
    rows, cols = len(tile_map), len(tile_map[0])
    def W(rr, cc):  return 0 <= rr < rows and 0 <= cc < cols and tile_map[rr][cc] == 3
    def IB(rr, cc): return 0 <= rr < rows and 0 <= cc < cols

    L, R, A, B = W(r, c-1), W(r, c+1), W(r-1, c), W(r+1, c)
    left_edge  = not L
    right_edge = not R
    top_edge   = not A
    bot_edge   = not B

    # Disambiguate when both horizontal edges are open:
    # in-bounds non-wall = room floor (interior); OOB = void (exterior).
    # The FLOOR side tells us which boundary this wall belongs to.
    if left_edge and right_edge:
        l_floor = IB(r, c-1) and not W(r, c-1)  # floor to the left
        r_floor = IB(r, c+1) and not W(r, c+1)  # floor to the right
        if l_floor and not r_floor:
            left_edge = False   # floor on left → right boundary wall
        elif r_floor and not l_floor:
            right_edge = False  # floor on right → left boundary wall

    if left_edge  and bot_edge:  return 'corner_bl'
    if right_edge and bot_edge:  return 'corner_br'
    if left_edge:                return 'v_left'
    if right_edge:               return 'v_right'
    return 'h_top' if top_edge else 'h_mid'


def parse_map(tile_map, diff_key):
    """
        Phân tích map
        Input : map, độ khó
        Output : wall_group, torch_group, item_group, exit_group, key_group, trap_group, player_spawn
    """
    cfg = DIFF[diff_key]
    wall_group  = pygame.sprite.Group()
    torch_group = pygame.sprite.Group()
    item_group  = pygame.sprite.Group()
    exit_group  = pygame.sprite.Group()
    key_group   = pygame.sprite.Group()  # single key pickup
    trap_group  = pygame.sprite.Group()
    player_spawn  = (TILE_SIZE, TILE_SIZE)
    
    # Count original slimes in the map template and turn them into floor tiles (0)
    base_slime_count = 0
    for r, row in enumerate(tile_map):
        for c, tile in enumerate(row):
            if tile == 2:
                base_slime_count += 1
                tile_map[r][c] = 0

    key_spawned   = False  # enforce single key per level
    for r, row in enumerate(tile_map):
        for c, tile in enumerate(row):
            x, y = c * TILE_SIZE, r * TILE_SIZE
            if   tile == 1:  player_spawn = (x, y)
            elif tile == 3:  wall_group.add(Wall(x, y, wall_type=_classify_wall(tile_map, r, c)))
            elif tile == 4:
                # Ensure even hardcoded/template torches are not spawned too close to each other
                too_close = False
                for t in torch_group:
                    if ((x - t.rect.x)**2 + (y - t.rect.y)**2)**0.5 < 6 * TILE_SIZE:
                        too_close = True
                        break
                if not too_close:
                    torch_group.add(Torch(x, y))
            elif tile == 5:  item_group.add(Item(x, y))
            elif tile == 6:
                # Only spawn ExitTile at the LEFT tile of each 6,6 pair.
                # If the tile to the left is also 6, this is the right half — skip it.
                left_is_door = (c > 0 and tile_map[r][c - 1] == 6)
                if not left_is_door:
                    exit_group.add(ExitTile(x, y))
                # tile 6 never adds a Wall → creates a passable opening in the wall
            elif tile == 9:
                if not key_spawned:        # only one key per level
                    key_group.add(KeyItem(x, y))
                    key_spawned = True
            elif tile == 10: trap_group.add(SpikeTrap(x, y))
            elif tile == 11: trap_group.add(FlamethrowerTrap(x, y))

    # Procedurally place extra torches on wall-adjacent floor tiles for better illumination
    torch_positions = [(sprite.rect.x, sprite.rect.y) for sprite in torch_group]
    wall_adjacent_candidates = []
    for r in range(1, len(tile_map) - 1):
        for c in range(1, len(tile_map[0]) - 1):
            if tile_map[r][c] == 0:
                # Check 4 cardinal neighbors for a wall (3)
                if (tile_map[r-1][c] == 3 or
                    tile_map[r+1][c] == 3 or
                    tile_map[r][c-1] == 3 or
                    tile_map[r][c+1] == 3):
                    wall_adjacent_candidates.append((r, c))

    random.shuffle(wall_adjacent_candidates)
    # Dynamically scale number of extra torches to keep it beautifully lit but not too cluttered
    max_extra_torches = 5
    extra_torches_added = 0
    for r, c in wall_adjacent_candidates:
        if extra_torches_added >= max_extra_torches:
            break
        tx, ty = c * TILE_SIZE, r * TILE_SIZE
        # Ensure torches are placed at least 6 tiles apart (6 * 128 = 768 px) to space them sparsely
        too_close = False
        for ex, ey in torch_positions:
            if ((tx - ex)**2 + (ty - ey)**2)**0.5 < 6 * TILE_SIZE:
                too_close = True
                break
        if not too_close:
            torch_group.add(Torch(tx, ty))
            torch_positions.append((tx, ty))
            extra_torches_added += 1

    # Base Slimes (map_slime_limit applies)
    slime_limit = cfg['map_slime_limit']
    num_slimes_to_spawn = min(base_slime_count, slime_limit)
    slime_group = pygame.sprite.Group()
    
    avoid = [player_spawn]
    
    # Randomly spawn the base slimes one-by-one on walkable floor tiles (ensuring spacing)
    for _ in range(num_slimes_to_spawn):
        pos = _random_floor_positions(tile_map, 1, avoid)
        if pos:
            sx, sy = pos[0]
            s = Slime(sx, sy, cfg)
            s.kill_callback = slime_killed_callback
            slime_group.add(s)
            avoid.append((sx, sy))

    # Extra slimes on hard (spawned one-by-one)
    for _ in range(cfg['extra_slimes']):
        pos = _random_floor_positions(tile_map, 1, avoid)
        if pos:
            sx, sy = pos[0]
            s = Slime(sx, sy, cfg)
            s.kill_callback = slime_killed_callback
            slime_group.add(s)
            avoid.append((sx, sy))

    # New mobs scaled by difficulty (spawned one-by-one)
    mob_cls_by_diff = {
        'easy':   [Skeleton],
        'medium': [Skeleton, Skeleton, HeavySkeleton],
        'hard':   [Skeleton, HeavySkeleton, Vampire, Vampire],
    }
    mob_classes = mob_cls_by_diff.get(diff_key, [Skeleton])
    mob_group = pygame.sprite.Group()
    
    for cls in mob_classes:
        pos = _random_floor_positions(tile_map, 1, avoid)
        if pos:
            mx, my = pos[0]
            m = cls(mx, my, cfg)
            m.kill_callback = slime_killed_callback
            mob_group.add(m)
            avoid.append((mx, my))

    return (player_spawn, slime_group, mob_group, wall_group,
            torch_group, item_group, exit_group, key_group, trap_group)

def draw_group_with_camera(surface, group, camera):
    """Blit every sprite in group offset by camera."""
    for sprite in group:
        sx, sy = camera.world_to_screen(sprite.rect.x, sprite.rect.y)
        surface.blit(sprite.image, (sx, sy))

def main():
    global stats
    fog           = FogOfWar()
    game_state    = 'start'
    chosen_diff   = 'easy'
    
    floor_surface = None
    nav_grid      = None
    player_group = slime_group = mob_group = wall_group = None
    torch_group = item_group = exit_group = key_group = trap_group = camera = None
    heal_spark_group = None
    monster_breath_cooldown = 0

    def new_game():
        nonlocal floor_surface, nav_grid, player_group, slime_group, mob_group, wall_group
        nonlocal torch_group, item_group, exit_group, key_group, trap_group, camera, heal_spark_group
        stats['killed'] = 0
        stats['start_ms'] = pygame.time.get_ticks()
        stats['end_ms'] = 0

        chosen_map = get_random_map()
        chosen_map = place_door_and_key(chosen_map)
        chosen_map = add_traps(chosen_map, spike_count=5)
        nav_grid = create_nav_grid(chosen_map)
        floor_surface = build_floor(chosen_map)

        result = parse_map(chosen_map, chosen_diff)
        p_spawn, s_grp, mob_grp, walls, torches, items, exits, keys, traps = result
        player_group = pygame.sprite.GroupSingle()
        player_group.add(Player(*p_spawn, max_hp=DIFF[chosen_diff]['player_hp']))

        slime_group = s_grp
        mob_group   = mob_grp
        wall_group  = walls
        torch_group = torches
        item_group  = items
        exit_group  = exits
        key_group   = keys
        trap_group  = traps
        camera = Camera()
        heal_spark_group = pygame.sprite.Group()

        def _spawn_heal_spark(cx, cy):
            heal_spark_group.add(HealSpark(cx, cy))

        for s in slime_group:
            s.drop_callback = _spawn_heal_spark
        for m in mob_group:
            m.drop_callback = _spawn_heal_spark

    def start_the_game():
        nonlocal game_state
        new_game()
        game_state = 'playing'
        audio.play_music('battle')
        
    def update_selector_padding(selector_widget):
        val_str = selector_widget.get_value()[0][0]
        font = pygame.font.Font(pygame_menu.font.FONT_MUNRO, 65)
        full_text = f"Difficulty: < {val_str} >"
        text_w = font.size(full_text)[0]
        right_pad = max(10, 850 - text_w - 60)
        selector_widget.set_padding((25, right_pad, 25, 60))

    def set_difficulty(value, difficulty_key):
        nonlocal chosen_diff
        chosen_diff = difficulty_key
        try:
            update_selector_padding(sel)
        except NameError:
            pass

    def return_to_main():
        nonlocal game_state
        game_state = 'start'
        audio.play_music('menu')

    # Create Pygame Menus
    theme = pygame_menu.themes.THEME_DARK.copy()
    theme.title_font_size = 80
    theme.widget_font_size = 60
    theme.widget_margin = (0, 20)

    start_theme = theme.copy()
    start_theme.background_color = pygame_menu.BaseImage('assets/menu_background.png')
    start_theme.title_bar_style = pygame_menu.widgets.MENUBAR_STYLE_NONE

    # Align and Position widgets
    start_theme.widget_alignment = pygame_menu.locals.ALIGN_LEFT
    start_theme.widget_margin = (250, 25)
    start_theme.widget_padding = (25, 80)  # Balanced vertical and horizontal padding

    # Fonts
    start_theme.widget_font = pygame_menu.font.FONT_MUNRO
    start_theme.widget_font_size = 65
    start_theme.widget_font_color = (255, 255, 255)

    # Shadows
    start_theme.widget_font_shadow = True
    start_theme.widget_font_shadow_color = (15, 10, 15)
    start_theme.widget_font_shadow_offset = 3

    # Translucent Background for widgets
    start_theme.widget_background_color = (20, 15, 25, 190)

    # Selection/Hover outline effect (Into the Breach style)
    start_theme.selection_color = (255, 255, 255)
    start_theme.widget_selection_effect = pygame_menu.widgets.HighlightSelection(
        border_width=3, margin_x=0, margin_y=0
    )

    start_menu = pygame_menu.Menu('', SCREEN_WIDTH, SCREEN_HEIGHT, theme=start_theme)
    # Huge game title at the top left
    start_menu.add.label('DUNGEON ESCAPE',
                         font_name=pygame_menu.font.FONT_8BIT,
                         font_size=160,
                         font_color=(255, 255, 255),
                         font_shadow=True,
                         font_shadow_color=(20, 10, 20),
                         font_shadow_offset=6,
                         margin=(250, 120),
                         padding=0,
                         background_color=None)
    start_menu.add.vertical_margin(120)
    
    sel = start_menu.add.selector('Difficulty: ', [('Easy', 'easy'), ('Medium', 'medium'), ('Hard', 'hard')], onchange=set_difficulty)
    update_selector_padding(sel)
    
    font_munro = pygame.font.Font(pygame_menu.font.FONT_MUNRO, 65)
    
    play_btn = start_menu.add.button('Play', start_the_game)
    play_w = font_munro.size("Play")[0]
    play_btn.set_padding((25, 850 - play_w - 60, 25, 60))
    
    quit_btn = start_menu.add.button('Quit', pygame_menu.events.EXIT)
    quit_w = font_munro.size("Quit")[0]
    quit_btn.set_padding((25, 850 - quit_w - 60, 25, 60))

    # End Menu Theme
    end_theme = theme.copy()
    end_theme.background_color = (0, 0, 0)  # Solid black
    end_theme.title_bar_style = pygame_menu.widgets.MENUBAR_STYLE_NONE  # No title bar

    # Defaults
    end_theme.widget_alignment = pygame_menu.locals.ALIGN_CENTER
    end_theme.widget_font = pygame_menu.font.FONT_MUNRO
    end_theme.widget_font_size = 60
    end_theme.widget_font_color = (240, 150, 100)  # Peach/orange

    # Borderless selection
    end_theme.widget_selection_effect = pygame_menu.widgets.NoneSelection()

    end_menu = pygame_menu.Menu('', SCREEN_WIDTH, SCREEN_HEIGHT, theme=end_theme)

    # Title
    label_status = end_menu.add.label('GAME OVER',
                                      font_name=pygame_menu.font.FONT_8BIT,
                                      font_size=130,
                                      font_color=(240, 190, 40),
                                      font_shadow=True,
                                      font_shadow_color=(30, 20, 10),
                                      font_shadow_offset=6,
                                      margin=(0, 80))

    # Subtitle
    end_menu.add.label('CONTINUE?',
                       font_name=pygame_menu.font.FONT_MUNRO,
                       font_size=60,
                       font_color=(110, 125, 180),
                       margin=(0, 40))

    # Horizontal frame for YES / NO
    h_frame = end_menu.add.frame_h(600, 120, align=pygame_menu.locals.ALIGN_CENTER, margin=(0, 40))

    def on_select_yes(selected, widget, menu):
        if selected:
            widget.set_title("*YES*")
        else:
            widget.set_title("YES")

    def on_select_no(selected, widget, menu):
        if selected:
            widget.set_title("*NO*")
        else:
            widget.set_title("NO")

    btn_yes = end_menu.add.button('YES', start_the_game, onselect=on_select_yes, margin=(0, 0))
    btn_no = end_menu.add.button('NO', return_to_main, onselect=on_select_no, margin=(0, 0))

    h_frame.pack(btn_yes, align='align-center', margin=(50, 0))
    h_frame.pack(btn_no, align='align-center', margin=(50, 0))

    # Stats label at the bottom (smaller, gray text)
    label_stats = end_menu.add.label('',
                                     font_size=32,
                                     font_color=(140, 140, 140),
                                     margin=(0, 100))

    audio.play_music('menu')
    while True:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                if game_state != 'start':
                    start_the_game()

        if game_state == 'start':
            if start_menu.is_enabled():
                start_menu.update(events)
                start_menu.draw(screen)

        elif game_state in ('dead', 'win'):
            # Update end menu text
            title = 'YOU ESCAPED' if game_state == 'win' else 'GAME OVER'
            label_status._font_color = (60, 220, 80) if game_state == 'win' else (240, 190, 40)
            label_status.set_title(title)
            
            elapsed = (stats['end_ms'] - stats['start_ms']) // 1000
            mins, secs = divmod(elapsed, 60)
            stats_str = f"Difficulty: {DIFF[chosen_diff]['label']} | Killed: {stats['killed']} | Time: {mins:02d}:{secs:02d}"
            label_stats.set_title(stats_str)

            if end_menu.is_enabled():
                end_menu.update(events)
                end_menu.draw(screen)

        elif game_state == 'playing':
            player = player_group.sprite if player_group else None
            player_group.update(wall_group, slime_group, mob_group)
            slime_group.update(player_group, wall_group, nav_grid)
            mob_group.update(player_group, wall_group, nav_grid)
            torch_group.update()
            item_group.update()
            exit_group.update()
            key_group.update()
            trap_group.update(player)
            heal_spark_group.update()

            if player and camera:
                camera.update(player.rect)

            for item in list(item_group):
                if player.hitbox.colliderect(item.rect.inflate(20, 20)):
                    player.hp = min(player.max_hp, player.hp + Item.HEAL_AMOUNT)
                    audio.play('use_spark')
                    item.kill()

            # Heal spark pickup
            for spark in list(heal_spark_group):
                if player.hitbox.colliderect(spark.rect.inflate(20, 20)):
                    player.hp = min(player.max_hp, player.hp + HealSpark.HEAL_AMOUNT)
                    audio.play('use_spark')
                    spark.kill()

            # Key pickup — walk over the key to collect it
            for key in list(key_group):
                if player.hitbox.colliderect(key.rect):
                    player.has_key = True
                    audio.play('collect')
                    key.kill()

            if player.is_dead:
                game_state = 'dead'
                stats['end_ms'] = pygame.time.get_ticks()
                audio.stop_music()
                audio.play('game_over')
            for ex in exit_group:
                if player.hitbox.colliderect(ex.rect) and player.has_key:
                    game_state = 'win'
                    stats['end_ms'] = pygame.time.get_ticks()
                    audio.stop_music()
                    audio.play('winning')

            # Monster breath proximity check
            if monster_breath_cooldown > 0:
                monster_breath_cooldown -= 1
            elif player and not player.is_dead:
                near_monster = False
                all_monsters = list(slime_group) + list(mob_group)
                for enemy in all_monsters:
                    if not enemy.is_dead:
                        dx = enemy.hitbox.centerx - player.hitbox.centerx
                        dy = enemy.hitbox.centery - player.hitbox.centery
                        dist = (dx*dx + dy*dy)**0.5
                        if dist < 400:  # ~3 tiles near player
                            near_monster = True
                            break
                if near_monster:
                    audio.play('monster_breath')
                    monster_breath_cooldown = random.randint(180, 300)  # 3-5 seconds cooldown at 60 FPS

            screen.blit(floor_surface,
                        (0, 0),
                        (camera.x, camera.y, SCREEN_WIDTH, SCREEN_HEIGHT))

            draw_group_with_camera(screen, wall_group,       camera)
            draw_group_with_camera(screen, trap_group,       camera)
            draw_group_with_camera(screen, exit_group,       camera)
            draw_group_with_camera(screen, key_group,        camera)
            draw_group_with_camera(screen, item_group,       camera)
            draw_group_with_camera(screen, heal_spark_group, camera)
            draw_group_with_camera(screen, torch_group,      camera)
            draw_group_with_camera(screen, slime_group,      camera)
            draw_group_with_camera(screen, mob_group,        camera)

            for slime in slime_group:
                slime.draw_hp_bar(screen, camera)
            for mob in mob_group:
                mob.draw_hp_bar(screen, camera)

            if player and not (player.invincible_timer > 0 and player.invincible_timer % 8 < 4):
                sx, sy = camera.world_to_screen(player.rect.x, player.rect.y)
                screen.blit(player.image, (sx, sy))

            if player and not player.is_dead:
                fog.draw(screen, player, torch_group, camera)

            if player:
                player.draw_hud(screen)

        pygame.display.update()
        clock.tick(FPS)

if __name__ == '__main__':
    main()
