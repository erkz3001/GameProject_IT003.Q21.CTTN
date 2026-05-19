import pygame

pygame.init()

SCREEN_WIDTH  = 2560
SCREEN_HEIGHT = 1600
TILE_SIZE     = 128
FPS           = 60
MAP_ROWS      = 20
MAP_COLS      = 36

F_HUGE  = pygame.font.SysFont(None, 140)
F_BIG   = pygame.font.SysFont(None, 96)
F_MED   = pygame.font.SysFont(None, 64)
F_SMALL = pygame.font.SysFont(None, 42)
F_TINY  = pygame.font.SysFont(None, 32)

C_BG    = ( 15,  12,  10)
C_WHITE = (255, 255, 255)
C_GREY  = (160, 160, 160)
C_GOLD  = (240, 190,  40)
C_RED   = (220,  50,  50)
C_GREEN = ( 60, 220,  80)

DIFF = {
    'easy': dict(
        label='EASY',   btn_col=(45, 140, 60),  btn_active=(70, 200, 90),
        player_hp=30,
        slime_hp=10,  slime_dmg=2.0, slime_walk=2, slime_run=4,
        detection=280, lose_range=450, extra_slimes=0,
        map_slime_limit=2,
    ),
    'medium': dict(
        label='MEDIUM', btn_col=(150, 120, 25), btn_active=(220, 175, 40),
        player_hp=20,
        slime_hp=15,  slime_dmg=4.0, slime_walk=3, slime_run=5,
        detection=380, lose_range=560, extra_slimes=0,
        map_slime_limit=99,
    ),
    'hard': dict(
        label='HARD',   btn_col=(150, 35,  35), btn_active=(220, 60,  60),
        player_hp=15,
        slime_hp=22,  slime_dmg=6.0, slime_walk=4, slime_run=7,
        detection=500, lose_range=700, extra_slimes=6,
        map_slime_limit=99,
    ),
}
