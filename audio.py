import pygame
import os

pygame.mixer.init()

SOUNDS = {}

def load_sounds():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sound_files = {
        'collect': 'collect.wav',
        'game_over': 'game_over.wav',
        'monster_death': 'monster_death.wav',
        'slime_attack': 'slime_attack.wav',
        'use_spark': 'use_spark.wav',
        'winning': 'winning.wav',
        'player_attack': 'player_attack.wav',
        'player_hurt': 'player_hurt.wav',
        'player_walk': 'player_walk.wav',
        'mob_damaged': 'mob_damaged.wav'
    }
    
    for name, filename in sound_files.items():
        path = os.path.join(base_dir, 'audio', filename)
        if os.path.exists(path):
            SOUNDS[name] = pygame.mixer.Sound(path)

load_sounds()

def play(name):
    sound = SOUNDS.get(name)
    if sound:
        sound.play()

_current_music = None

def play_music(name):
    global _current_music
    if _current_music == name:
        return
    base_dir = os.path.dirname(os.path.abspath(__file__))
    filename = 'Game_Music(Battle).wav' if name == 'battle' else 'Game_Music(Menu).wav'
    path = os.path.join(base_dir, 'audio', filename)
    if os.path.exists(path):
        pygame.mixer.music.load(path)
        pygame.mixer.music.play(-1)
        _current_music = name

def stop_music():
    global _current_music
    pygame.mixer.music.stop()
    _current_music = None

