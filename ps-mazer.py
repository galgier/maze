# vim: ts=4 sw=4 expandtab

from pyscript import document, display
from pyodide import create_proxy

import numpy as np

CELL_SIZE = 30           # width of a cell
WALL_THICK = 3           # thickness of wall
ARROW_THICK = 1
SPACING = CELL_SIZE + WALL_THICK
HALF_CELL = int(CELL_SIZE // 2)
ARROW_LEN = int(CELL_SIZE // 3)
COLOR_WALL = 'black'
COLOR_BLOCK = 'black'
COLOR_START = 'lime'
COLOR_END = 'red'
COLOR_ARROW = 'black'
COLOR_WALK = 'orange'
COLOR_LOOP = 'yellow'
COLOR_CLEAR = 'gray40'
COLOR_DEAD = 'gray50'
COLOR_SOLUTION = 'cyan'

def draw_maze(ctx, width, height):
    ctx.clearRect(0, 0,
        (width + 1) * SPACING - 1,
        (height + 1) * SPACING - 1)
    draw_grid(ctx, width, height, COLOR_WALL)

def draw_grid(ctx, width, height, style):
    maxx = (width + 1) * SPACING - 1
    maxy = (height + 1) * SPACING - 1
    for x in range(0, maxx, SPACING):
        draw_vert(ctx, x, 0, maxy, style)
    for y in range(0, maxy, SPACING):
        draw_horz(ctx, y, 0, maxx, style)

def draw_vert(ctx, x, miny, maxy, style):
    ctx.beginPath()
    ctx.moveTo(x, miny)
    ctx.lineTo(x, maxy)
    ctx.strokeStyle = style
    ctx.stroke()

def draw_horz(ctx, y, minx, maxx, style):
    ctx.beginPath()
    ctx.moveTo(minx, y)
    ctx.lineTo(maxx, y)
    ctx.strokeStyle = style
    ctx.stroke()

def on_generate():
    canvas = document.getElementById("maze")
    ctx = canvas.getContext("2d")
    draw_maze(ctx, 10, 10)

generate_proxy = create_proxy(on_generate)
element = document.getElementById("generate_button")
element.addEventListener("click", generate_proxy)
