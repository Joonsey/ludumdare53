#!/usr/bin/env python

from __future__ import annotations
from pprint import pprint
from typing import Protocol

import pygame
import sys
import enum

DISPLAY_DIMESION = (1080, 720)
RENDER_DIMENSION = (400, 240)

SIZE = 16
FPS = 60

pygame.init()

MAP_WIDTH = 25

class Behaviour(Protocol):
    can_walk_through = False
    can_pickup = False

class WallBehaviour(Behaviour):
    pass

class FloorBehaviour(Behaviour):
    can_walk_through = True

class ConveyorBehaviour(Behaviour):
    pass

class Vec2:
    def __init__(self, x: int | float, y: int | float) -> None:
        self.x = x
        self.y = y

    @classmethod
    def from_tuple(cls, pos: tuple[int | float, int | float]) -> Vec2:
        return cls(pos[0], pos[1])

    def __add__(self, other: Vec2) -> Vec2:
        return Vec2(other.x + self.x, other.y + self.y)

    def __repr__(self) -> str:
        return f"x: {self.x}, y: {self.y}"

    def as_tuple(self) -> tuple:
        return (self.x, self.y)

class Postman:
    def __init__(self, pos: tuple[int | float, int | float]) -> None:
        self.pos: Vec2 = Vec2.from_tuple(pos)
        self.velocity: Vec2 = Vec2(0,0)
        self.acceleration = 0
        self.max_velocity = 3
        self.base_acceleration = 1
        self.speed = 1.4
        self.sprite = pygame.image.load("assets/rocks.png").convert_alpha()
        self.colissions: list[Tile] | None = None

    @property
    def coliding(self) -> bool:
        return any([self.get_rect().colliderect(tile.get_rect()) for tile in self.colissions]) if self.colissions != None else False

    def get_rect(self) -> pygame.Rect:
        rect = self.sprite.get_rect()
        rect.x = int(self.pos.x)
        rect.y = int(self.pos.y)
        return rect

    def update(self, dt: float) -> None:
        delta = self._handle_inputs(dt)

        if not self.colissions:
            self.pos = self.pos + delta
            return

        #TODO add change in behaviour if coliding
        #need to wait until i have better test sprite
        self.pos.x = self.pos.x + delta.x
        self.pos.y = self.pos.y + delta.y


    def render(self, surf: pygame.Surface) -> None:
        surf.blit(self.sprite, (self.pos.x,self.pos.y))

    def _handle_inputs(self, dt: float) -> Vec2:
        keys = pygame.key.get_pressed()
        normalized_dt = dt/1000

        if keys[pygame.K_w]:
            self.velocity.y =- self.acceleration * normalized_dt

        elif keys[pygame.K_s]:
            self.velocity.y =+ self.acceleration * normalized_dt
        else:
            self.velocity.y = 0

        if keys[pygame.K_a]:
            self.velocity.x =- self.acceleration * normalized_dt

        elif keys[pygame.K_d]:
            self.velocity.x =+ self.acceleration * normalized_dt
        else:
            self.velocity.x = 0

        if self.velocity.x or self.velocity.y:
            self.acceleration *= dt / 10
            if self.acceleration >= self.max_velocity:
                self.acceleration = self.max_velocity
        else:
            self.acceleration = self.base_acceleration / 4

        return Vec2(self.velocity.x * self.speed * dt, self.velocity.y * self.speed * dt)

class Level(enum.IntEnum):
    test  = 0
    one   = enum.auto()
    two   = enum.auto()

class Office:
    def __init__(self, size: int) -> None:
        self.size = size
        self._map_data: list[list[Tile]] = [[]]
        self._player: None | Postman = None

    def generate_map(self, level: Level) -> None:
        data = self._load_map(level)
        for y in range(0, len(data)):
            row = []
            for x, char in enumerate(data[y]):
                pos = (x * SIZE, y * SIZE)
                if char == '#':
                    row.append(Tile(TileType.wall, pos))

                elif char == '-':
                    row.append(Tile(TileType.conveyor, pos))

                elif char == 'X':
                    self._player = Postman(pos)
                    row.append(Tile(TileType.floor, pos))

                else:
                    row.append(Tile(TileType.floor, pos))


            self._map_data.append(row)


    def render(self, surf: pygame.Surface) -> None:
        for y in range(len(self._map_data)):
            for x, tile in enumerate(self._map_data[y]):
                surf.blit(tile.surf, tile.pos.as_tuple())

    def update(self, dt: float) -> None:
        if self._player:
            tiles = [tile for subtiles in self._map_data for tile in subtiles]
            self._player.colissions = list(filter(lambda x: not x.behaviour.can_walk_through, tiles))


    def get_player(self) -> Postman:
        assert isinstance(self._player, Postman), "player not initialized during map generation!"
        return self._player

    def _load_map(self, level: Level) -> list[str]:
        data = []
        with open('levels/level-'+ str(level.value)) as file:
            for line in file.readlines():
                line = line.replace('\n','')
                row = line.split(',')
                assert len(row) == MAP_WIDTH, "map data is not of correct size"
                data.append(row)

        return data

class Package:
    ...

class Tool:
    ...

class Tile:
    def __init__(self, type: TileType, pos : tuple[int, int]) -> None:
        self.type = type
        self.pos = Vec2.from_tuple(pos)

    @property
    def behaviour(self) -> Behaviour:
        behaviour = Behaviour
        if self.type == TileType.wall:
            behaviour = WallBehaviour

        elif self.type == TileType.floor:
            behaviour = FloorBehaviour

        elif self.type == TileType.conveyor:
            behaviour = ConveyorBehaviour

        return behaviour

    def get_rect(self) -> pygame.Rect:
        rect = self.surf.get_rect()
        rect.x = int(self.pos.x)
        rect.y = int(self.pos.y)
        return rect

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

        # The same pointer is shared between Game and Officer
        self.player = self.office.get_player()

    def run(self):
        while self.running:
            self.deltatime = self.clock.tick(FPS)
            self._check_should_close()

            # updates
            self.office.update(self.deltatime)
            self.player.update(self.deltatime)

            # renders
            self.office.render(self.surf)
            self.player.render(self.surf)
            self._draw_surface_on_display()

        pygame.quit()


    def _draw_surface_on_display(self) -> None:
        resized_surf = pygame.transform.scale(self.surf, self.display.get_size())
        self.display.blit(resized_surf, (0,0))
        pygame.display.flip()
        self.display.fill(0)
        self.surf.fill(0)

    def _check_should_close(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

if __name__ == "__main__":
    game = Game(DISPLAY_DIMESION)
    game.run()
