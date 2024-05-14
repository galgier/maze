# vim: ts=4 sw=4 expandtab

from pyscript import document, display
from pyodide.ffi import create_proxy
from datetime import datetime

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
    clear_maze(ctx, width, height)
    draw_grid(ctx, width, height, COLOR_WALL)

def draw_cell(ctx, x, y, thick, style):
    ctx.beginPath()
    ctx.lineWidth = 0
    ctx.strokeStyle = style
    ctx.rect(x * SPACING, y * SPACING, CELLSIZE, CELLSIZE)
    ctx.stroke()
    
def clear_maze(ctx, width, height):
    ctx.clearRect(0, 0,
        (width + 1) * SPACING - 1,
        (height + 1) * SPACING - 1)

def draw_grid(ctx, width, height, style):
    maxx = (width + 1) * SPACING - 1
    maxy = (height + 1) * SPACING - 1
    for x in range(0, maxx, SPACING):
        draw_vert(ctx, x, 0, maxy, WALL_THICK, style)
    for y in range(0, maxy, SPACING):
        draw_horz(ctx, y, 0, maxx, WALL_THICK, style)

def draw_vert(ctx, x, miny, maxy, thick, style):
    ctx.beginPath()
    ctx.lineWidth = thick
    ctx.moveTo(x, miny)
    ctx.lineTo(x, maxy)
    ctx.strokeStyle = style
    ctx.stroke()

def draw_horz(ctx, y, minx, maxx, thick, style):
    ctx.beginPath()
    ctx.lineWidth = thick
    ctx.moveTo(minx, y)
    ctx.lineTo(maxx, y)
    ctx.strokeStyle = style
    ctx.stroke()

def on_clear(*args):
    print(f"{args = }")
    canvas = document.getElementById("maze")
    ctx = canvas.getContext("2d")
    clear_maze(ctx, 10, 10)

def on_generate(*args):
    print(f"{args = }")
    canvas = document.getElementById("maze")
    ctx = canvas.getContext("2d")
    draw_maze(ctx, 10, 10)

def on_solve(*args):
    print(f"{args = }")
    canvas = document.getElementById("maze")
    ctx = canvas.getContext("2d")
    for y in range(10):
        for x in range(y % 2, 10, 2):
            print(f"draw_cell(ctx,{x},{y},0,{COLOR_SOLUTION})")
            draw_cell(ctx, x, y, 0, COLOR_SOLUTION)

clear_proxy = create_proxy(on_clear)
element = document.getElementById("clear_button")
element.addEventListener("click", clear_proxy)

generate_proxy = create_proxy(on_generate)
element = document.getElementById("generate_button")
element.addEventListener("click", generate_proxy)

solve_proxy = create_proxy(on_solve)
element = document.getElementById("solve_button")
element.addEventListener("click", solve_proxy)
