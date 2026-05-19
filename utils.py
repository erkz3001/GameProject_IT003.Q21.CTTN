import pygame
from settings import C_GOLD, C_WHITE

# ---------------------------------------------------------------------------
# New helpers for the dungeon tileset and enemy strip sprites
# ---------------------------------------------------------------------------

_TILESET_CACHE: dict = {}

def load_tileset_tile(flat_index: int, tile_px: int = 16,
                      cols_per_row: int = 10,
                      path: str = 'assets/Dungeon_Tileset.png',
                      output_size: int | None = None) -> pygame.Surface:
    """Return a single tile from Dungeon_Tileset.png scaled to output_size."""
    global _TILESET_CACHE
    cache_key = (flat_index, output_size)
    if cache_key in _TILESET_CACHE:
        return _TILESET_CACHE[cache_key]
    try:
        sheet = pygame.image.load(path).convert_alpha()
        r = flat_index // cols_per_row
        c = flat_index % cols_per_row
        tile = sheet.subsurface((c * tile_px, r * tile_px, tile_px, tile_px)).copy()
        if output_size is not None:
            tile = pygame.transform.scale(tile, (output_size, output_size))
        _TILESET_CACHE[cache_key] = tile
        return tile
    except Exception:
        size = output_size or tile_px
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        s.fill((150, 80, 180, 200))
        _TILESET_CACHE[cache_key] = s
        return s


def load_strip(path: str, frame_w: int, frame_h: int,
               output_w: int, output_h: int,
               flipped: bool = False) -> list[pygame.Surface]:
    """
    Load a horizontal sprite strip where every frame is frame_w × frame_h pixels.
    Scales each frame to output_w × output_h. If flipped=True, mirrors horizontally.
    """
    try:
        sheet = pygame.image.load(path).convert_alpha()
        total_w = sheet.get_width()
        num_frames = total_w // frame_w
        frames = []
        for i in range(num_frames):
            s = pygame.Surface((frame_w, frame_h), pygame.SRCALPHA)
            s.blit(sheet, (0, 0), (i * frame_w, 0, frame_w, frame_h))
            s = pygame.transform.scale(s, (output_w, output_h))
            if flipped:
                s = pygame.transform.flip(s, True, False)
            frames.append(s)
        return frames
    except Exception:
        return [_fallback(output_w, output_h)] * max(1, 6)

def _fallback(w, h, colour=(150, 80, 180, 200)):
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill(colour)
    return s

def load_assets_by_row(path, num_frames, row_index, num_rows=4, scale_factor=1):
    try:
        sheet  = pygame.image.load(path).convert_alpha()
        fw, fh = sheet.get_width() // num_frames, sheet.get_height() // num_rows
        result = []
        for i in range(num_frames):
            s = pygame.Surface((fw, fh), pygame.SRCALPHA)
            s.blit(sheet, (0, 0), (i * fw, row_index * fh, fw, fh))
            if scale_factor != 1:
                s = pygame.transform.scale(
                    s, (max(1, int(fw * scale_factor)), max(1, int(fh * scale_factor))))
            result.append(s)
        return result
    except Exception:
        size = max(1, int(32 * scale_factor))
        return [_fallback(size, size)] * num_frames

def load_assets_by_col(path, num_frames, col_index, num_cols=4, scale_factor=1):
    try:
        sheet  = pygame.image.load(path).convert_alpha()
        fw     = sheet.get_width()  // num_cols
        fh     = sheet.get_height() // num_frames
        result = []
        for i in range(num_frames):
            s = pygame.Surface((fw, fh), pygame.SRCALPHA)
            s.blit(sheet, (0, 0), (col_index * fw, i * fh, fw, fh))
            if scale_factor != 1:
                s = pygame.transform.scale(
                    s, (max(1, int(fw * scale_factor)), max(1, int(fh * scale_factor))))
            result.append(s)
        return result
    except Exception:
        size = max(1, int(32 * scale_factor))
        return [_fallback(size, size)] * num_frames


def draw_panel(surface, rect, bg_col=(30, 25, 25), alpha=220, border_col=C_GOLD, border_w=3, radius=16):
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(panel, (*bg_col, alpha), panel.get_rect(), border_radius=radius)
    pygame.draw.rect(panel, border_col, panel.get_rect(), border_w, border_radius=radius)
    shadow = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 150), shadow.get_rect(), border_radius=radius)
    surface.blit(shadow, (rect.x + 10, rect.y + 10))
    surface.blit(panel, rect.topleft)

def draw_text_with_shadow(surface, text, font, col, center):
    shadow = font.render(text, True, (0, 0, 0))
    lbl = font.render(text, True, col)
    surface.blit(shadow, shadow.get_rect(center=(center[0] + 4, center[1] + 4)))
    surface.blit(lbl, lbl.get_rect(center=center))


