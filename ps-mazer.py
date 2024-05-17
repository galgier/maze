# vim: ts=4 sw=4 expandtab

from pyscript import document, display
from pyodide.ffi import create_proxy
from datetime import datetime
import secrets
from enum import Enum, auto
import numpy as np

from maze import Maze

class State(Enum):
    INITIAL = auto()
    CLEARED = auto()
    GENERATING = auto()
    GENERATED = auto()
    SOLVING = auto()
    SOLVED = auto()

DEF_WIDTH = 10           # number of cells
DEF_HEIGHT = 10
DEF_LEVELS = 1
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

class App():
    def __init__(self):
        # Initialize
        super().__init__()
        self.state = State.INITIAL
        self.shape = self.shape2d((DEF_WIDTH,DEF_HEIGHT,DEF_LEVELS))
        self.maze = Maze(self.shape)
        self.clear_button = None
        self.generate_button = None
        self.generate_button = None
        self.width_input = None
        self.height_input = None

    # For efficiency a 3D maze with only one level is best handled as
    # if it is a 2D maze.  This accepts a tuple or list and returns a
    # new tuple that is perhaps only two members.
    def shape2d(self, shape):
        s = list(shape)
        s.extend([1, 1, 1])         # silently handle short shapes
        if s[2] == 1:
            return tuple(s[0:2])
        else:
            return tuple(s[0:3])

    def fetch_elements():
        # I would have used document.getElementById("xxx").value but
        # I get an error that the element has no value.
        if self.width_input is None:
            self.width_input = document.querySelector("[name='width']")
        if self.height_input is None:
            self.height_input = document.querySelector("[name='height']")
        if self.clear_button is None:
            self.clear_button = document.getElementById("clear_button")
        if self.generate_button is None:
            self.generate_button = document.getElementById("generate_button")
        if self.solve_button is None:
            self.solve_button = document.getElementById("solve_button")

    def update_states(self):
        self.fetch_elements()
        print(f"before: {clear_button.getAttribute('disabled') = }")
        print(f"before: {generate_button.getAttribute('disabled') = }")
        print(f"before: {solve_button.getAttribute('disabled') = }")
        match self.state:
            case State.INITIAL | State.CLEARED:
                clear_button.setAttribute("disabled",False)
                generate_button.setAttribute("disabled",False)
                solve_button.setAttribute("disabled",True)
            case State.GENERATING:
                clear_button.setAttribute("disabled",True)
                generate_button.setAttribute("disabled",True)
                solve_button.setAttribute("disabled",True)
            case State.GENERATED:
                clear_button.setAttribute("disabled",False)
                generate_button.setAttribute("disabled",False)
                solve_button.setAttribute("disabled",False)
            case State.SOLVING:
                clear_button.setAttribute("disabled",True)
                generate_button.setAttribute("disabled",True)
                solve_button.setAttribute("disabled",True)
            case State.SOLVED:
                clear_button.setAttribute("disabled",False)
                generate_button.setAttribute("disabled",False)
                solve_button.setAttribute("disabled",False)
        print(f"after: {clear_button.getAttribute('disabled') = }")
        print(f"after: {generate_button.getAttribute('disabled') = }")
        print(f"after: {solve_button.getAttribute('disabled') = }")

# instantiate the application
app = App()

def draw_maze(ctx, width, height):
    clear_maze(ctx, width, height)
    draw_grid(ctx, width, height, COLOR_WALL)

def draw_cell(ctx, x, y, style):
    ctx.fillStyle = style
    ctx.fillRect(x * SPACING + WALL_THICK - 1,
        y * SPACING + WALL_THICK - 1,
        CELL_SIZE - 1,
        CELL_SIZE - 1)
    
def clear_maze(ctx, width, height):
    # clear the current area
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height)
    # now set the new size
    ctx.canvas.width = width
    ctx.canvas.height = height
    
def draw_grid(ctx, width, height, style):
    maxx = width * SPACING + WALL_THICK - 1
    maxy = height * SPACING + WALL_THICK - 1
    ctx.canvas.width = maxx
    ctx.canvas.height = maxy
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
    self.fetch_elements()
    width = int(width_input.value)
    height = int(height_input.value)
    canvas = document.getElementById("maze")
    ctx = canvas.getContext("2d")
    clear_maze(ctx, width, height)
    app.state = State.CLEARED
    app.update_states()

def on_generate(*args):
    self.fetch_elements()
    width = int(width_input.value)
    height = int(height_input.value)
    choice = document.querySelector("[name='generator']:checked").value
    canvas = document.getElementById("maze")
    ctx = canvas.getContext("2d")
    draw_maze(ctx, width, height)
    app.state = State.GENERATING
    app.update_states()
    # XXX: setup callbacks and generate
    app.state = State.GENERATED
    app.update_states()

def on_solve(*args):
    self.fetch_elements()
    width = int(width_input.value)
    height = int(height_input.value)
    choice = document.querySelector("[name='solver']:checked").value
    canvas = document.getElementById("maze")
    ctx = canvas.getContext("2d")
    app.state = State.SOLVING
    app.update_states()
    # XXX: setup callbacks and solve
    for y in range(width):
        for x in range(y % 2, height, 2):
            draw_cell(ctx, x, y, COLOR_SOLUTION)
    app.state = State.SOLVED
    app.update_states()

self.state = State.INITIAL

clear_proxy = create_proxy(on_clear)
element = document.getElementById("clear_button")
element.addEventListener("click", clear_proxy)

generate_proxy = create_proxy(on_generate)
element = document.getElementById("generate_button")
element.addEventListener("click", generate_proxy)

solve_proxy = create_proxy(on_solve)
element = document.getElementById("solve_button")
element.addEventListener("click", solve_proxy)
