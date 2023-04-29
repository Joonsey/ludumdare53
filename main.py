#!/usr/bin/env python

from __future__ import annotations 
from pprint import pprint

import pygame
import enum

DISPLAY_DIMESION = (1080, 720)
RENDER_DIMENSION = (400, 240)

SIZE = 16
FPS = 60

pygame.init()

MAP_WIDTH = 25

class Level(enum.IntEnum):
    test  = 0
    one   = enum.auto()
    two   = enum.auto()

class Office:
    def __init__(self, size: int) -> None:
        self.size = size
        self._map_data: list[list[Tile]] = [[]]

    def generate_map(self, level: Level) -> None:
        data = self._load_map(level)
        for y in range(0, len(data)):
            row = []
            for x, char in enumerate(data[y]):
                if char == '#':
                    row.append(Tile(TileType.wall))

                elif char == '-':
                    row.append(Tile(TileType.conveyor))

                else:
                    row.append(Tile(TileType.floor))


            self._map_data.append(row)


    def render(self, surf: pygame.Surface) -> None:
        for y in range(len(self._map_data)):
            for x, tile in enumerate(self._map_data[y]):
                surf.blit(tile.surf, (x * self.size, y * self.size))

    def _load_map(self, level: Level) -> list[str]:
        data = []
        with open('levels/level-'+ str(level.value)) as file:
            for line in file.readlines():
                line = line.replace('\n','')
                row = line.split(',')
                assert len(row) == MAP_WIDTH
                data.append(row)

        return data



class Package:
    ...

class Tool:
    ...

class Tile:
    def __init__(self, type: TileType) -> None:
        self.type = type

    @property
    def surf(self) -> pygame.Surface:
        surf = pygame.Surface((SIZE, SIZE))
        if self.type == TileType.wall:
            surf.fill((255,0,0))

        if self.type == TileType.floor:
            surf.fill((0,255,0))

        if self.type == TileType.conveyor:
            surf.fill((0,0,255))

        return surf

class TileType(enum.Enum):
    wall      = enum.auto()
    floor     = enum.auto()
    conveyor  = enum.auto()


class Game:
    def __init__(self, DISPLAY_DIMESION) -> None:
        self.display = pygame.display.set_mode(DISPLAY_DIMESION)
        self.surf = pygame.surface.Surface(RENDER_DIMENSION)
        self.clock = pygame.time.Clock()
        self.deltatime = 0
        self.running = True

        self.office = Office(size=SIZE)
        self.office.generate_map(Level.test)

    def run(self):
        while self.running:

            self.office.render(self.surf)
            self._draw_surface_on_display()

        pygame.quit()


    def _draw_surface_on_display(self) -> None:
        resized_surf = pygame.transform.scale(self.surf, self.display.get_size())
        self.display.blit(resized_surf, (0,0))
        pygame.display.flip()
        self.display.fill(0)
        self.surf.fill(0)

if __name__ == "__main__":
    game = Game(DISPLAY_DIMESION)
    game.run()
