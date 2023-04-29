#!/usr/bin/env python

from __future__ import annotations
from pprint import pprint
from typing import Protocol

import pygame
import random
import sys
import enum

#DEFINES
DISPLAY_DIMESION = (1080, 720)
RENDER_DIMENSION = (400, 240)

SIZE = 16
FPS = 60
MAP_WIDTH = 25


class Spritesheet:
    """vertical spritesheet"""
    def __init__(self, path: str, dimensions: tuple[int, int] = (SIZE, SIZE)) -> None:
        self.sheet = pygame.image.load(path).convert_alpha()
        self.sprite_dimensions = dimensions
        self.images = self._make_surfaces_from_sheet()
        self._index = 0

    @property
    def active(self) -> pygame.Surface:
        return self.images[self._index]

    @property
    def max_index(self) -> int:
        return self.sheet.get_width() // self.sprite_dimensions[1]

    def next(self) -> pygame.Surface:
        if self._index == self.max_index - 1:
            self._index = 0
        else:
            self._index += 1

        return self.active

    def image_at(self, index: int):
        rect = pygame.Rect(
            (self.sprite_dimensions[0] * index, 0,
             self.sprite_dimensions[0], self.sprite_dimensions[1]))
        image = pygame.Surface(rect.size)
        image.blit(self.sheet, (0, 0), rect)
        return image

    def _make_surfaces_from_sheet(self) -> list[pygame.Surface]:
        images = []
        for i in range(self.max_index):
            images.append(self.image_at(i))

        return images

class Direction(enum.Enum):
    up = enum.auto()
    down = enum.auto()
    left = enum.auto()
    right = enum.auto()

class Behaviour(Protocol):
    can_walk_through = False
    can_pickup = False
    uses_spritesheet = False
    does_update = False
    animated = False
    animation_interval = 0
    animation_delta: float = 0

class WallBehaviour(Behaviour):
    pass

class PackageBehaviour(Behaviour):
    can_pickup = True
    does_update = True

class FloorBehaviour(Behaviour):
    can_walk_through = True

class ConveyorBehaviour(Behaviour):
    animated = True
    direction: Direction
    does_update = True
    uses_spritesheet = True
    animation_interval: float = .3
    animation_delta: float = animation_interval

class ConveyorSpawnerBehaviour(ConveyorBehaviour):
    interval: int = 4
    delta: float = interval

    def spawn_package(self, pos: tuple[int, int], office: Office) -> None:
        package = Package(pos, self.direction)
        office.packages.append(package)


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

    def copy(self) -> Vec2:
        return Vec2(self.x, self.y)

class Postman:
    def __init__(self, pos: tuple[int | float, int | float]) -> None:
        self.pos: Vec2 = Vec2.from_tuple(pos)
        self.velocity: Vec2 = Vec2(0,0)
        self.acceleration = 0
        self.max_velocity = 3
        self.base_acceleration = 1
        self.speed = 1.4
        self.sprite = pygame.image.load("assets/player.png").convert_alpha()
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
        start_pos = self.pos.copy()

        self.pos.x = self.pos.x + delta.x
        if self.coliding:
            self.pos.x = start_pos.x

        self.pos.y = self.pos.y + delta.y
        if self.coliding:
            self.pos.y = start_pos.y

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
        self.packages: list[Package] = []

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

                elif char == '-e':
                    row.append(Tile(TileType.conveyorend, pos))

                elif char == '+':
                    tile = Tile(TileType.package_spawner, pos)
                    assert isinstance(tile.behaviour, ConveyorSpawnerBehaviour)
                    tile.behaviour.direction = Direction.left
                    row.append(tile)

                elif char == 'X':
                    self._player = Postman(pos)
                    row.append(Tile(TileType.floor, pos))

                else:
                    row.append(Tile(TileType.floor, pos))


            self._map_data.append(row)


    def render(self, surf: pygame.Surface) -> None:
        for column in self._map_data:
            for tile in column:
                surf.blit(tile.sheet.active, tile.pos.as_tuple())

        for package in self.packages:
            surf.blit(package.surf, package.pos.as_tuple())

    def update(self, dt: float) -> None:
        tiles = [tile for subtiles in self._map_data for tile in subtiles]
        endtiles = list(filter(lambda x: x.type == TileType.conveyorend, tiles))
        if self._player:
            self._player.colissions = list(filter(lambda x: not x.behaviour.can_walk_through, tiles))

        for tile in tiles:
            if tile.behaviour.does_update:
                tile.update(dt, self)

        for package in self.packages:
            package.colissions = list(filter(lambda x: x != package, self.packages))
            if not package.at_end and any([package.get_rect().colliderect(tile.get_rect()) for tile in endtiles]):
                package.at_end = True
            package.update(dt)

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
    def __init__(self, pos: tuple[int, int], direction: Direction) -> None:
        self.pos = Vec2.from_tuple(pos)
        self.surf = pygame.image.load("assets/mail-0.png")
        self.behaviour = PackageBehaviour
        self.direction = direction
        self.colissions: list[Package] | None = None
        self.speed = 3
        self.at_end: bool = False

    def update(self, dt) -> None:
        if self.at_end:
            return
        normalized_dt = dt / 100
        start_pos = self.pos.copy()
        if self.direction == Direction.up:
            self.pos.y += normalized_dt * self.speed
        if self.direction == Direction.down:
            self.pos.y -= normalized_dt * self.speed

        if self.coliding:
            self.pos.y = start_pos.y

        if self.direction == Direction.right:
            self.pos.x += normalized_dt * self.speed
        if self.direction == Direction.left:
            self.pos.x -= normalized_dt * self.speed

        if self.coliding:
            self.pos.x = start_pos.x

    def update_direction(self, direction) -> None:
        self.direction = direction

    def get_rect(self) -> pygame.Rect:
        rect = self.surf.get_rect()
        rect.x = int(self.pos.x)
        rect.y = int(self.pos.y)
        return rect

    @property
    def coliding(self) -> bool:
        return any([self.get_rect().colliderect(package.get_rect()) for package in self.colissions]) if self.colissions != None else False

class Tool:
    ...

class Tile:
    def __init__(self, type: TileType, pos: tuple[int, int]) -> None:
        self.type = type
        self.sheet = self._infer_sheet_from_type(type)
        self.pos = Vec2.from_tuple(pos)
        self._behaviour: None | Behaviour =  None
        self.animation_index = 0

    def update(self, dt: float, office: Office) -> None:
        assert self.behaviour.does_update, "tried to update on a tile without update behaviour"

        if isinstance(self.behaviour, ConveyorSpawnerBehaviour):
            self.behaviour.delta -= dt/1000
            if self.behaviour.delta < 0:
                self.behaviour.spawn_package(self.pos.as_tuple(), office)
                self.behaviour.delta = self.behaviour.interval

        if self.behaviour.animated:
            self.behaviour.animation_delta -= dt/1000
            if self.behaviour.animation_delta < 0:
                self.sheet.next()
                self.behaviour.animation_delta = self.behaviour.animation_interval


    def get_rect(self) -> pygame.Rect:
        rect = self.sheet.active.get_rect()
        rect.x = int(self.pos.x)
        rect.y = int(self.pos.y)
        return rect

    @property
    def behaviour(self) -> Behaviour:
        if self._behaviour:
            return self._behaviour

        behaviour = Behaviour
        if self.type == TileType.wall:
            behaviour = WallBehaviour()

        elif self.type == TileType.package_spawner:
            behaviour = ConveyorSpawnerBehaviour()

        elif self.type == TileType.floor:
            behaviour = FloorBehaviour()

        elif self.type == TileType.conveyor:
            behaviour = ConveyorBehaviour()

        self._behaviour = behaviour
        return behaviour


    def _infer_sheet_from_type(self, TileType) -> Spritesheet:
        sheet = None
        if self.type == TileType.wall:
            sheet = Spritesheet("assets/wall_tile.png")

        elif self.type == TileType.floor:
            sheet = Spritesheet("assets/floor_tile.png")

        elif self.type == TileType.conveyor:
            sheet = Spritesheet("assets/conveyor-tile.png")

        elif self.type == TileType.conveyorend:
            sheet = Spritesheet("assets/dark_table.png")

        elif self.type == TileType.package_spawner:
            sheet = Spritesheet("assets/conveyor-tile.png")

        else:
            sheet = Spritesheet("assets/floor_tile.png")

        assert sheet != None
        return sheet

class TileType(enum.Enum):
    wall             = enum.auto()
    floor            = enum.auto()
    conveyor         = enum.auto()
    conveyorend      = enum.auto()
    package_spawner  = enum.auto()


class Game:
    def __init__(self, DISPLAY_DIMESION) -> None:
        self.display = pygame.display.set_mode(DISPLAY_DIMESION)
        self.surf = pygame.surface.Surface(RENDER_DIMENSION)
        self.clock = pygame.time.Clock()
        self.deltatime = 0
        self.running = True

        self.office = Office(size=SIZE)
        self.office.generate_map(Level.test)

        # The same pointer is shared between Game and Office
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
    pygame.init()
    game = Game(DISPLAY_DIMESION)
    game.run()
