#!/usr/bin/env python

from __future__ import annotations
from typing import Protocol

import pygame
import sys
import enum
import math
import random

#DEFINES
DISPLAY_DIMESION = (1080, 720)
RENDER_DIMENSION = (400, 240)

SIZE = 16
FPS = 60
MAP_WIDTH = 25
MAP_HEIGHT = 11
INTERACT_INTERVAL = .6
PACKAGE_DROP_RADIUS = 17
SPAWN_INTERVAL = 4


class Interactable(Protocol):
    pos: Vec2
    behaviour: PackageBehaviour
    def interact(self, postman: Postman) -> None:
        ...
    def drop(self) -> None:
        ...

    def __str__(self) -> str:
        ...

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
    weight_modifier: float = 1

class HeavyPackageBehaviour(PackageBehaviour):
    weight_modifier: float = .3

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
    interval: int = SPAWN_INTERVAL
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

    def __sub__(self, other: Vec2) -> Vec2:
        return Vec2(self.x - other.x, self.y - other.y)

    def __repr__(self) -> str:
        return f"x: {self.x}, y: {self.y}"

    def as_tuple(self) -> tuple:
        return (self.x, self.y)

    def copy(self) -> Vec2:
        return Vec2(self.x, self.y)

    def magnitude(self) -> float:
        return max(self.as_tuple())

    def get_absolute_distance(self, other: Vec2) -> float:
        return abs((self - other).magnitude())

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
        self.range = 20
        self.nearest_interactable: None | Interactable = None
        self.currently_holding: None | Interactable = None
        self.interact_delta: float = INTERACT_INTERVAL

    @property
    def is_holding(self) -> bool:
        return self.currently_holding != None

    @property
    def can_interact(self) -> bool:
        if self.nearest_interactable == None:
            return False

        distance = self.nearest_interactable.pos - self.pos
        if distance.magnitude() < self.range:
            return True
        else:
            return False

    @property
    def interact_on_cooldown(self) -> bool:
        return self.interact_delta != INTERACT_INTERVAL

    @property
    def coliding(self) -> bool:
        return any([self.get_rect().colliderect(tile.get_rect()) for tile in self.colissions]) if self.colissions != None else False

    def interact(self) -> None:
        self.interact_delta -= .1

        if self.is_holding:
            self.drop()

        elif self.nearest_interactable != None and self.can_interact:
            self.nearest_interactable.interact(self)

    def drop(self) -> None:
        assert self.currently_holding != None, "can not drop when None"
        self.currently_holding.drop()
        self.currently_holding = None

    def get_rect(self) -> pygame.Rect:
        rect = self.sprite.get_rect()
        rect.x = int(self.pos.x)
        rect.y = int(self.pos.y)
        return rect

    def update(self, dt: float) -> None:
        delta = self._handle_inputs(dt)
        if self.interact_delta < 0:
            self.interact_delta = INTERACT_INTERVAL

        elif self.interact_delta != INTERACT_INTERVAL:
            self.interact_delta -= dt/1000

        if not self.colissions:
            self.pos = self.pos + delta
            return

        start_pos = self.pos.copy()

        speed_modifier = self._get_speed_modifier()
        self.pos.x = self.pos.x + delta.x * speed_modifier
        if self.coliding:
            self.pos.x = start_pos.x

        self.pos.y = self.pos.y + delta.y * speed_modifier
        if self.coliding:
            self.pos.y = start_pos.y

        if self.currently_holding != None:
            self.currently_holding.pos = self.pos.copy()

    def render(self, surf: pygame.Surface) -> None:
        surf.blit(self.sprite, (self.pos.x,self.pos.y))

    def _get_speed_modifier(self) -> float:
        if self.currently_holding:
            return self.currently_holding.behaviour.weight_modifier
        return 1

    def _handle_inputs(self, dt: float) -> Vec2:
        keys = pygame.key.get_pressed()
        normalized_dt = dt/1000


        if keys[pygame.K_e] and not self.interact_on_cooldown:
            self.interact()

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
        self.packages_delivered: int = 0
        self.size = size
        self._map_data: list[list[Tile]] = [[]]
        self._player: None | Postman = None
        self.packages: list[Package] = []
        self.drop_of_tile: Tile | None = None

    def generate_map(self, level: Level) -> None:
        data = self._load_map(level)
        for y in range(0, len(data)):
            row = []
            for x, char in enumerate(data[y]):
                pos = (x * SIZE, y * SIZE)
                if char == '#':
                    row.append(Tile(TileType.wall, pos))

                elif char == '¤':
                    row.append(Tile(TileType.wall_full, pos))

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

                elif char == 'x':
                    tile = Tile(TileType.drop_of, pos)
                    self.drop_of_tile = tile
                    row.append(tile)

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
        interactables = self.packages

        if self._player:
            self._player.colissions = list(filter(lambda x: not x.behaviour.can_walk_through, tiles))
            p = self._player

            if interactables:
                self._player.nearest_interactable = min(interactables, key=lambda item: math.sqrt((item.pos.x - p.pos.x) ** 2 + (item.pos.y - p.pos.y) ** 2))

        for tile in tiles:
            if tile.behaviour.does_update:
                tile.update(dt, self)

        packages_to_remove: list[Package] = []
        for package in self.packages:
            assert self.drop_of_tile != None, "drop of tile should exist in the map"
            if int(package.pos.get_absolute_distance(self.drop_of_tile.pos)) <= PACKAGE_DROP_RADIUS:
                if not package.being_held:
                    packages_to_remove.append(package)
                    self.packages_delivered += 1

            package.colissions = list(filter(lambda x: x != package, self.packages))
            if not package.at_end and any([package.get_rect().colliderect(tile.get_rect()) for tile in endtiles]):
                package.at_end = True
            package.update(dt)

        for package in packages_to_remove:
            self.packages.remove(package)
            del package

    def get_player(self) -> Postman:
        assert isinstance(self._player, Postman), "player not initialized during map generation!"
        return self._player

    def _load_map(self, level: Level) -> list[str]:
        data = []
        with open('levels/level-'+ str(level.value)) as file:
            for line in file.readlines():
                line = line.replace('\n','')
                row = line.split(',')
                assert len(row) == MAP_WIDTH, "map data width is not of correct size"
                data.append(row)

        assert len(data) == MAP_HEIGHT, "map data height is not of correct size"
        return data

class PackageVariation(enum.Enum):
    mail                  = enum.auto()
    mail_with_envelope    = enum.auto()
    package               = enum.auto()
    package_with_postmark = enum.auto()
    package_with_fragile  = enum.auto()
    package_with_heavy    = enum.auto()

def generate_random_package_variant() -> PackageVariation:
    return PackageVariation[random.choice(PackageVariation._member_names_)]

class Package:
    def __init__(self, pos: tuple[int, int], direction: Direction) -> None:
        self.pos = Vec2.from_tuple(pos)
        self.variation: PackageVariation = generate_random_package_variant()
        self.surf = pygame.image.load(f"assets/{self.variation.name}.png")
        self.direction = direction
        self.colissions: list[Package] | None = None
        self.speed = 3
        self.on_conveyor: bool = True
        self.at_end: bool = False
        self.being_held: bool = False

    @property
    def coliding(self) -> bool:
        return any([self.get_rect().colliderect(package.get_rect()) for package in self.colissions]) if self.colissions != None else False

    @property
    def behaviour(self) -> PackageBehaviour:
        if self.variation is PackageVariation.package_with_heavy:
            return HeavyPackageBehaviour()
        else:
            return PackageBehaviour()

    def update(self, dt) -> None:
        if self.at_end or not self.on_conveyor:
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

    def interact(self, postman: Postman) -> None:
        if not postman.is_holding:
            postman.currently_holding = self
            self.on_conveyor = False
            self.being_held = True

    def drop(self) -> None:
        self.being_held = False

    def update_direction(self, direction) -> None:
        self.direction = direction

    def get_rect(self) -> pygame.Rect:
        rect = self.surf.get_rect()
        rect.x = int(self.pos.x)
        rect.y = int(self.pos.y)
        return rect

    def __str__(self) -> str:
        return str(self.variation.name.replace("_", " "))

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

        elif self.type == TileType.wall_full:
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

        elif self.type == TileType.wall_full:
            sheet = Spritesheet("assets/wall_tile.png")
            sheet.active.fill((172, 40, 71))

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
    drop_of          = enum.auto()
    wall_full        = enum.auto()


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
            self.render_ui(self.surf)
            self._draw_surface_on_display()

        pygame.quit()

    def render_ui(self, surf: pygame.Surface) -> None:
        self._draw_current_item_info(surf)

    def _draw_current_item_info(self, surf: pygame.Surface) -> None:
        office_height = MAP_HEIGHT * SIZE
        margin_top = RENDER_DIMENSION[1] - office_height
        margin_left = RENDER_DIMENSION[0] / 2

        window = pygame.Surface((margin_left, margin_top))
        window.fill((199, 164, 103))


        if self.player.currently_holding != None:
            package = self.player.currently_holding
            sysfont = pygame.font.get_default_font()
            font = pygame.font.SysFont(sysfont, 23)
            window.blit(font.render(str(package), False, (255,255,255)), (0,0))

        surf.blit(window, (margin_left, office_height))


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
    pygame.font.init()
    game = Game(DISPLAY_DIMESION)
    game.run()
