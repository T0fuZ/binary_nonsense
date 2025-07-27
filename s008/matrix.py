
import pygame
import sys
import random
from PIL import Image

pygame.init()
screen_w, screen_h = 640, 480
screen = pygame.display.set_mode((screen_w, screen_h))
fullscreen = False
pygame.display.set_caption("Matrix Rain")
clock = pygame.time.Clock()

font_img = Image.open("rexpaint_cp437_10x10.png").convert("RGBA")
font_img.save("rex_temp.png")
font_surf = pygame.image.load("rex_temp.png").convert_alpha()

cell_w, cell_h = 10, 10
cols_in_sheet = 16
scale = 2
char_w = cell_w * scale
char_h = cell_h * scale

grid_cols = screen_w // char_w
grid_rows = screen_h // char_h

char_set = list("01abcdefhkmnprstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+-*/=$#%&@")

def draw_char(surface, char, x, y, color):
    code = ord(char)
    if not (0 <= code <= 255):
        return
    sx = (code % cols_in_sheet) * cell_w
    sy = (code // cols_in_sheet) * cell_h
    rect = pygame.Rect(sx, sy, cell_w, cell_h)
    glyph = font_surf.subsurface(rect).copy()
    color_surf = pygame.Surface((cell_w, cell_h)).convert_alpha()
    color_surf.fill(color)
    glyph.blit(color_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    glyph_scaled = pygame.transform.scale(glyph, (char_w, char_h))
    surface.blit(glyph_scaled, (x, y))

def create_streams():
    streams = []
    for col in range(grid_cols):
        stream = {
            'x': col,
            'y': random.randint(-grid_rows, 0),
            'speed': 0.15 + random.random() * 0.3,
            'trail': random.randint(10, 30),
            'chars': [random.choice(char_set) for _ in range(40)],
            'counter': 0.0
        }
        streams.append(stream)
    return streams

streams = create_streams()

running = True
while running:
    screen.fill((0, 0, 0))

    for stream in streams:
        x = stream['x']
        y = stream['y']
        trail = stream['trail']
        counter = stream['counter']
        counter += 0.1
        if counter >= stream['speed']:
            stream['y'] += 1
            stream['counter'] = 0
        else:
            stream['counter'] = counter
        for i in range(trail):
            row_y = y - i
            if 0 <= row_y < grid_rows:
                ch = stream['chars'][i % len(stream['chars'])]
                brightness = max(40, 255 - i * 10)
                color = (0, brightness, 0) if i != 0 else (160, 255, 160)
                draw_char(screen, ch, x * char_w, row_y * char_h, color)
        if stream['y'] - stream['trail'] > grid_rows:
            stream['y'] = random.randint(-grid_rows, 0)
            stream['trail'] = random.randint(10, 30)
            stream['chars'] = [random.choice(char_set) for _ in range(40)]
        for i in range(len(stream['chars'])):
            if random.random() < 0.05:
                stream['chars'][i] = random.choice(char_set)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_F11:
                fullscreen = not fullscreen
                if fullscreen:
                    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                else:
                    screen = pygame.display.set_mode((640, 480))
                screen_w, screen_h = screen.get_size()
                grid_cols = screen_w // char_w
                grid_rows = screen_h // char_h
                streams = create_streams()

    pygame.display.flip()
    clock.tick(30)

pygame.quit()
sys.exit()
