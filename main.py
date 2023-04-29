#!/usr/bin/env python

import pygame

DISPLAY_DIMESION = (1080, 720)
RENDER_DIMENSION = (540, 360)

SIZE = 16
FPS = 60

pygame.init()

class Game:
    def __init__(self, DISPLAY_DIMESION) -> None:
        self.display = pygame.display.set_mode(DISPLAY_DIMESION)
        self.surf = pygame.surface.Surface((540, 360))
        self.clock = pygame.time.Clock()
        self.deltatime = 0
        self.running = True

    def run(self):
        while self.running:

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
