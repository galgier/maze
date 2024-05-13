# vim: ts=4 sw=4 expandtab

import tkinter as tk
from tkinter import ttk
import sys
import time
import threading
import queue
import numpy as np
import secrets
from enum import Enum, auto

from maze import Maze

_sentinel = object()    # used to mark end of data in queue

SOLVE_THREADED = False

class State(Enum):
    INITIAL = auto()
    CLEARED = auto()
    GENERATING = auto()
    GENERATED = auto()
    SOLVING = auto()
    SOLVED = auto()

MIN_SPEED = 0
MAX_SPEED = 100
DEF_WIDTH = 10           # number of cells
DEF_HEIGHT = 10
DEF_LEVELS = 1
MAX_DIMENSION = 1000
LEFT_MARGIN = RIGHT_MARGIN = TOP_MARGIN = BOT_MARGIN = 5
CELL_SIZE = 30           # width of a cell
WALL_THICK = 3           # thickness of wall
ARROW_THICK = 1
SPACING = CELL_SIZE + WALL_THICK
HALF_CELL = int(CELL_SIZE // 2)
ARROW_LEN = int(CELL_SIZE // 3)
STEP_DELAY=1500  # repeat delay
STEP_REPEAT=100  # repeat interval
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

# Useful during debugging
def dir_name(dir):
    match dir & Maze.DIR:
        case Maze.E:
            return "E"
        case Maze.NE:
            return "NE"
        case Maze.N:
            return "N"
        case Maze.NW:
            return "NW"
        case Maze.W:
            return "W"
        case Maze.SW:
            return "SW"
        case Maze.S:
            return "S"
        case Maze.SE:
            return "SE"
        case Maze.U:
            return "U"
        case Maze.D:
            return "D"
        case _:
            return "?"
def dir_names(dirs):
    def bits(n):
        result = []
        while n:
            i = (n - 1) & n
            result.append(i ^ n)
            n = i
        return result
    result = list()
    for dir in bits(dirs & Maze.DIR):
        result.append(dir_name(dir))
    return result

class App(tk.Tk):
    def __init__(self, title, size):
        # Initialize
        super().__init__()
        self.state = State.INITIAL
        self.start = self.end = self.tstart = self.tend = tuple()
        self.app_title = title
        self.log = None
        self.title(title)
        self.columnconfigure(0, weight=1)
        self.minsize(size[0],size[1])
        self.shape = self.shape2d((DEF_WIDTH,DEF_HEIGHT,DEF_LEVELS))
        self.maze = Maze(self.shape)
        self.maze.log = self.log
        self.gen_queue = self.solve_q = None
        self.generator = None
        self.stepper = lambda : None
        self.entry_vars = dict()
        self.clear_button = None
        self.generate_button = None
        self.replay_button = None
        self.step_button = None
        self.solve_button = None
        self.bg_color = self.cget('bg')
        self.settings = dict()
        event_callbacks = {
            "<<FileQuit>>": lambda _: self.quit(),
        }
        for sequence, callback in event_callbacks.items():
            self.bind(sequence, callback)

        # Determine what algorithms are available
        self.generators = dict()
        generators = self.maze.generators
        for (name,generator,description) in generators:
            self.generators[name] = {
                "description": description,
                "function": generator,
            }
        self.solvers = dict()
        solvers = self.maze.solvers
        for (name,solver,description) in solvers:
            self.solvers[name] = {
                "description": description,
                "function": solver,
            }

        # Pick a main menu style based upon OS
        if sys.platform.startswith("darwin"):
            cls = MacOsMainMenu
        elif sys.platform.startswith("win32"):
            cls = WindowsMainMenu
        elif sys.platform.startswith("linux"):
            cls = LinuxMainMenu
        else:
            cls = GenericMainMenu
        menu = cls(self, self.settings)
        self.config(menu=menu)

        # Widgets
        self.add_widgets()

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

    # This does a 2d conversion for a coordinate tuple.
    # However, it bases its decisions upon the given shape.
    # If the shape is omitted, it will use self.shape.
    def coord2d(self, coord, shape = None):
        if shape is None:
            shape = self.shape
        s = list(shape)
        s.extend([1, 1, 1])         # silently handle short shapes
        c = list(coord)
        c.extend([0, 0, 0])
        if s[2] == 1:
            return tuple(c[0:2])
        else:
            return tuple(c[0:3])

    # These do the inverse
    def shape3d(self, shape):
        s = list(shape)
        s.extend([1, 1, 1])         # silently handle short shapes
        return tuple(s[0:3])
    def coord3d(Self, coord):
        c = list(coord)
        c.extend([0, 0, 0])         # silently handle short shapes
        return tuple(c[0:3])

    # This transforms the maze coordinate directions to screen coordinate
    # directions. This is needed because the screen coordinate for (0,0)
    # at the top left, but a geometric coordinate system puts (0,0) at
    # the bottom left.
    def coord_trans(self, coord, shape = None):
        if shape is None:
            shape = self.shape
        result = list()
        n = len(shape)
        for i in range(len(coord)):
            if i == 1 and i < n:        # Y coordinate
                result.append(shape[i] - coord[i] - 1)
            else:
                result.append(coord[i])
        return tuple(result)

    def clear_start(self,coord):
        self.start = self.tstart = tuple()
        self.draw_cell(coord)

    def set_start(self,coord):
        redraw = [coord]
        if len(self.start) and self.start != coord:
            redraw.append(self.start)
        if len(self.tstart) and self.tstart != coord:
            redraw.append(self.tstart)
        self.start = self.tstart = coord
        for coord in redraw:
            self.draw_cell(coord)

    def clear_end(self,coord):
        self.end = self.tend = tuple()
        self.draw_cell(coord)

    def set_end(self,coord):
        redraw = [coord]
        if len(self.end) and self.end != coord:
            redraw.append(self.end)
        if len(self.tend) and self.tend != coord:
            redraw.append(self.tend)
        self.end = self.tend = coord
        for coord in redraw:
            self.draw_cell(coord)

    def clear_hidden(self,coord):
        self.maze.cells[coord] &= ~Maze.HIDDEN
        self.draw_cell(coord)

    def set_hidden(self,coord):
        self.maze.cells[coord] |= Maze.HIDDEN
        self.draw_cell(coord)

    # A couple canvas/cell untility functions
    def canvas_size(self):
        (width, height, levels) = list(self.shape3d(self.maze.cells.shape))
        return (
            LEFT_MARGIN + width * SPACING + WALL_THICK + RIGHT_MARGIN,
            TOP_MARGIN + height * SPACING + WALL_THICK + BOT_MARGIN
        )
    def canvasxy2cell(self,canvas,x,y):
        (width, height, levels) = list(self.shape3d(self.maze.cells.shape))
        cellx = min((x - LEFT_MARGIN) // SPACING, width - 1)
        celly = min((y - TOP_MARGIN) // SPACING, height - 1)
        return (cellx, celly)

    # Add a book (aka a maze level) to a notebook
    def add_book(self,book,level):
        def cell_popup(event):
            canvas = event.widget
            if self.state == State.INITIAL:
                canvas.popup.grab_release()
                return
            canvas.popup.delete(0, 'end')
            (w, h) = self.canvas_size()
            (cellx, celly) = self.canvasxy2cell(canvas, event.x, event.y)
            coord = self.coord2d((cellx, celly, canvas.level))
            cell = self.maze.cells[coord]
            ishidden = cell & Maze.HIDDEN
            isstart = coord in (self.start, self.tstart)
            isend = coord in (self.end, self.tend)
            hiddenstate = startstate = endstate = tk.NORMAL
            if isend or ishidden: startstate = tk.DISABLED
            if isstart:
                canvas.popup.add_command(label="Clear start cell",
                    command=lambda : self.clear_start(coord)
                )
            else:
                canvas.popup.add_command(label="Set start cell",
                    command=lambda : self.set_start(coord),
                    state=startstate
                )
            if isstart or ishidden: endstate = tk.DISABLED
            if isend:
                canvas.popup.add_command(label="Clear end cell",
                    command=lambda : self.clear_end(coord)
                )
            else:
                canvas.popup.add_command(label="Set end cell",
                    command=lambda : self.set_end(coord),
                    state=endstate
                )
            if isstart or isend: hiddenstate = tk.DISABLED
            if ishidden:
                canvas.popup.add_command(label="Unhide cell",
                    command=lambda : self.clear_hidden(coord)
                )
            else:
                canvas.popup.add_command(label="Hide cell",
                    command=lambda : self.set_hidden(coord),
                    state=hiddenstate
                )
            canvas.popup.add_separator()
            canvas.popup.add_command(label="Dismiss Menu")
            try:
                canvas.popup.tk_popup(event.x_root, event.y_root, 0)
            finally:
                canvas.popup.grab_release()
            canvas.update_idletasks()
        frame = tk.Frame(book)
        book.add(frame,text="Level " + str(level))
        label=ttk.Label(frame,
            text="Level " + str(level),
            font=("TkDefaultFont", 16)
        )
        label.pack()
        (w, h) = self.canvas_size()
        canvas = tk.Canvas(frame,
            width=w,
            height=h,
            scrollregion=(0,0,500,500),
            xscrollincrement=SPACING,
            yscrollincrement=SPACING,
        )
        canvas.level = level
        canvas.popup = tk.Menu(canvas, tearoff=False)
        #canvas.popup.add_command(label="Set or clear start")
        #canvas.popup.add_command(label="Set or clear end")
        #canvas.popup.add_command(label="Set or clear hidden")
        #canvas.popup.add_separator()
        #canvas.popup.add_command(label="Dismiss Menu")
        canvas.bind("<Button-3>", cell_popup)
        canvas.hbar = tk.Scrollbar(frame, orient=tk.HORIZONTAL)
        canvas.hbar.pack(side=tk.BOTTOM, fill=tk.X)
        canvas.hbar.config(command=canvas.xview)
        canvas.vbar=tk.Scrollbar(frame, orient=tk.VERTICAL)
        canvas.vbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.vbar.config(command=canvas.yview)
        canvas.config(xscrollcommand=canvas.hbar.set,
            yscrollcommand=canvas.vbar.set)
        canvas.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        return canvas

    def add_widgets(self):

        # Local storage and functions to validate and fix dimensions
        values = dict()     # where we remember the last valid value
        def dim_validate(reason, action, val, name, maximum):
            maximum = int(maximum)
            ok = True
            match reason:
                case "focusin":
                    # Save the value on focus in
                    values[name] = val
                case "focusout":
                    # Validate it and optionally fix it on focus out
                    try:
                        n = int(val)
                    except ValueError:
                        ok = False
                    else:
                        ok = 0 < n and n <= MAX_DIMENSION and n <= maximum
                    if not ok:
                        self.entry_vars[name].set(values[name])
                    self.update_states()
            return ok

        # Wrap up label, entry and validation as one function
        def dim_entry(parent,name,init,maximum,row):
            dim_register = parent.register(dim_validate)
            self.entry_vars[name] = tk.StringVar(value=str(init))
            ttk.Label(parent,
                text=name,
                font=("TkDefaultFont", 10)
                ).grid(row=row,column=0, padx=5)
            ttk.Entry(parent,
                textvariable=self.entry_vars[name],
                width=6,
                validate="all",
                validatecommand=(dim_register, "%V", "%d", "%P", name, maximum),
            ).grid(row=row,column=1, padx=5)

        # First section is just a title
        ttk.Label(self,
            text=self.app_title,
            font=("TkDefaultFont", 16)
        ).grid(row=0)

        # The second section accepts settings
        # We create a frame to hold all the input
        self.input_frame = tk.Frame(self)
        self.input_frame.grid(row=1)

        # Left side of second section is for dimensions
        self.size_frame = tk.Frame(self.input_frame)
        self.size_frame.grid(row=1, column=0, padx=5, sticky="n")
        ttk.Label(self.size_frame,
            text="Dimensions",
            font=("TkDefaultFont", 12)
        ).grid(row=0, columnspan=2, padx=5, sticky="n")

        dim_entry(self.size_frame,"Width",str(DEF_WIDTH),1000,1)
        dim_entry(self.size_frame,"Height",str(DEF_HEIGHT),1000,2)
        dim_entry(self.size_frame,"Levels",str(DEF_LEVELS),1,3)

        # Middle of second section is for choosing generator method
        self.generator_frame = tk.Frame(self.input_frame)
        self.generator_frame.grid(row=1, column=1, padx=5, sticky="n")
        self.generator_var = tk.StringVar()

        ttk.Label(self.generator_frame,
            text="Generators",
            font=("TkDefaultFont", 12)
        ).grid(row=0, column=0)

        i = 0
        keys = list(self.generators.keys())
        keys.sort()
        for generator in keys:
            if i == 0:
                # Choose the first one as a default
                self.generator_var.set(generator)
                self.generator = generator
            ttk.Radiobutton(self.generator_frame,
                text=generator,
                variable=self.generator_var,
                value=generator,
                command=lambda : self.update_states()
            ).grid(row=i + 1, column=0, sticky="ew")
            i += 1

        # Third part of second section is for choosing solver method
        self.solver_frame = tk.Frame(self.input_frame)
        self.solver_frame.grid(row=1, column=2, padx=5, sticky="n")
        self.solver_var = tk.StringVar()

        ttk.Label(self.solver_frame,
            text="Solvers",
            font=("TkDefaultFont", 12)
        ).grid(row=0, column=0)

        i = 0
        keys = list(self.solvers.keys())
        keys.sort()
        for solver in keys:
            if i == 0:
                # Choose the first one as a default
                self.solver_var.set(solver)
                self.solver = solver
            ttk.Radiobutton(self.solver_frame,
                text=solver,
                variable=self.solver_var,
                value=solver,
                command=lambda : self.update_states()
            ).grid(row=i + 1, column=0, sticky="ew")
            i += 1

        # The forth part supports single step.
        self.step_frame = tk.Frame(self.input_frame)
        self.step_frame.grid(row=1, column=3, padx=5, sticky="n")
        self.step_var = tk.IntVar()
        self.step_var.set(0)
        self.step_check = tk.Checkbutton(self.step_frame,
            text="Single step",
            variable=self.step_var,
            command=self.step_checked,
            state=tk.NORMAL,
        )
        self.step_check.grid()
        self.step_button = tk.Button(self.step_frame,
            text="Step",
            command=self.step_pressed,
            repeatdelay=STEP_DELAY,
            repeatinterval=STEP_REPEAT,
            state=tk.DISABLED
        )
        self.step_button.grid()

        # The third section holds the action buttons
        self.action_frame = tk.Frame(self.input_frame)
        self.action_frame.grid(row=2, columnspan=3)
        self.clear_button = tk.Button(self.action_frame,
            text="Clear",
            command=self.clear_pressed,
        )
        self.clear_button.grid(row=0,column=0)
        self.generate_button = tk.Button(self.action_frame,
            text="Generate",
            command=self.generate_pressed,
            state=tk.DISABLED
        )
        self.generate_button.grid(row=0,column=1)
        self.replay_button = tk.Button(self.action_frame,
            text="Replay",
            command=self.replay_pressed,
            state=tk.DISABLED
        )
        self.replay_button.grid(row=0,column=2)
        self.solve_button_text = tk.StringVar(value="Solve")
        self.solve_button = tk.Button(self.action_frame,
            textvariable=self.solve_button_text,
            command=self.solve_pressed,
            state=tk.DISABLED
        )
        self.solve_button.grid(row=0,column=3)

        # The fourth section holds the maze
        # We use a notebook to hold the maze.  The
        # pages of the notebook are the levels of the
        # maze.  On each page we create a frame.  In
        # that frame we put a label and then a canvas.
        # Prior to generation, we create one tab to save the space.
        self.note_book = ttk.Notebook(self, padding=5)
        self.note_book.grid(row=3, sticky=tk.N + tk.E + tk.S + tk.W)
        self.note_book.master.rowconfigure(3,weight=1)
        self.note_book.master.columnconfigure(0,weight=1)
        self.tabs = dict()
        self.tabs[0] = self.add_book(self.note_book, 0)

    def update_one(self,button,state):
        if button is not None:
            button.configure(state=state)
    def update_states(self):
        if self.params_changed():
            self.update_one(self.generate_button, tk.DISABLED)
            self.update_one(self.replay_button, tk.DISABLED)
            self.update_one(self.solve_button, tk.DISABLED)
            self.solve_button_text.set("Solve")
            self.update_one(self.step_button, tk.DISABLED)
            return
        match self.state:
          case State.INITIAL:
            self.update_one(self.generate_button, tk.DISABLED)
            self.update_one(self.replay_button, tk.DISABLED)
            self.update_one(self.solve_button, tk.DISABLED)
            self.solve_button_text.set("Solve")
            self.update_one(self.step_button, tk.DISABLED)
          case State.CLEARED:
            self.update_one(self.generate_button, tk.NORMAL)
            self.update_one(self.replay_button, tk.DISABLED)
            self.update_one(self.solve_button, tk.DISABLED)
            self.solve_button_text.set("Solve")
            self.update_one(self.step_button, tk.DISABLED)
          case State.GENERATING:
            self.update_one(self.generate_button, tk.DISABLED)
            self.update_one(self.replay_button, tk.DISABLED)
            self.update_one(self.solve_button, tk.DISABLED)
            self.solve_button_text.set("Solve")
            if self.step_var.get() == 0:
                self.update_one(self.step_button, tk.DISABLED)
            else:
                self.update_one(self.step_button, tk.NORMAL)
          case State.GENERATED | State.SOLVED:
            self.update_one(self.generate_button, tk.NORMAL)
            self.update_one(self.replay_button, tk.NORMAL)
            self.update_one(self.solve_button, tk.NORMAL)
            if self.step_var.get() == 0:
                self.update_one(self.step_button, tk.DISABLED)
            else:
                self.update_one(self.step_button, tk.NORMAL)

    def params_changed(self):
        shape = self.shape2d((
            int(self.entry_vars["Width"].get()),
            int(self.entry_vars["Height"].get()),
            int(self.entry_vars["Levels"].get()),
        ))
        generator = self.generator_var.get()
        return (
            (self.generator is not None and self.generator != generator)
            or (self.shape is not None and self.shape != shape)
        )

    def step_checked(self):
        if self.step_var.get() == 0:
            self.update_one(self.step_button, tk.DISABLED)
            self.after(10, self.stepper)
        else:
            self.update_one(self.step_button, tk.NORMAL)
    def step_pressed(self):
        if self.state in (State.GENERATING, State.SOLVING):
            self.after(10, self.stepper)

    def clear_pressed(self):
        self.generator = self.generator_var.get()
        self.shape = self.shape2d((
            int(self.entry_vars["Width"].get()),
            int(self.entry_vars["Height"].get()),
            int(self.entry_vars["Levels"].get()),
        ))
        self.maze = Maze(self.shape)
        self.maze.log = self.log
        self.state = State.CLEARED
        self.recanvas()
        self.grid_maze(cells=COLOR_CLEAR, walls=COLOR_WALL)
        self.update_states()

    def generate_pressed(self):
        if self.params_changed():
            self.clear_pressed()
        # Set a new random seed and the rest is the same as replay
        self.seed = secrets.randbits(128)
        self.replay_pressed()

    def replay_pressed(self):
        if self.state is State.INITIAL:
            self.clear_pressed()
        else:
            self.maze.clean()
            self.grid_maze(cells=COLOR_CLEAR, walls=COLOR_WALL)

        # Start/restart RNG with seed
        self.maze.rand = np.random.default_rng(self.seed)
        self.state = State.GENERATING
        self.update_states()
        self.generate()

    def generate(self):
        generator = self.generators[self.generator]["function"]
        handler=lambda **kw: self.gen_event(**kw)
        params = { "log": self.log, "callback": handler }
        if self.single_threaded:
            solver(self.maze, **params)
        else:
            self.pipeline(generator, [self.maze], params, handler)

    def solve_pressed(self):
        match self.state:
            case State.SOLVED:
                self.clear_solution()
                self.state = State.GENERATED
                self.stepper = lambda : None
                self.solve_button_text.set("Solve")
            case State.GENERATED:
                self.state = State.SOLVING
                self.solver = self.solver_var.get()
                self.solve()
                self.solve_button_text.set("Hide solution")

    def solve(self):
        solver = self.solvers[self.solver]["function"]
        handler=lambda **kw: self.solve_event(**kw)
        params = { "log": self.log, "callback": handler }
        if len(self.start):
            params["start"] = self.start
        if len(self.end):
            params["end"] = self.end
        self.tstart = self.tend = tuple()
        if self.single_threaded:
            solver(self.maze, **params)
        else:
            self.pipeline(solver, [self.maze], params, handler)

    def pipeline(self, producer, args, kwargs, consumer):
        def _consumer():
            if self.queue is None: return
            try:
                data = self.queue.get(False)
            except queue.Empty:
                # If nothing waiting, check back again later
                self.after(100, _consumer)
            else:
                if data is _sentinel:
                    self.queue = None
                else:
                    # We use a lambda function to change the opaque
                    # data into **kwargs.   I am not sure if this is
                    # needed, but it seems to be.
                    visible = (lambda kwargs: consumer(**kwargs))(data)
                    # If there was no visible update, or not single stepping
                    # check again in a litle bit
                    if self.step_var.get() == 0 or not visible:
                        self.after(10, _consumer)
        def _producer(*args, **kwargs):
#            callback=lambda **kw: self.queue.put(kw)
#            producer(self.maze,
#                log=self.log,
#                callback=callback
#            )
            producer(*args,**kwargs)
            self.queue.put(_sentinel)

        kw = kwargs.copy()
        kw["callback"] = lambda **kw: self.queue.put(kw)
        self.stepper = _consumer
        self.queue = queue.Queue(0)
        self.thread = threading.Thread(target=_producer, args=args, kwargs=kw)
        self.thread.start()
        self.after(100, _consumer)

    def clear_solution(self):
        self.tstart = self.tend = tuple()
        self.maze.unsolve()
        self.grid_maze()
        self.draw_maze()

    def draw_maze(self, /, *, color=None):
        # Generate all the coordinates and draw each cell
        for coord in zip(*np.nonzero(self.maze.cells | 1)):
            self.draw_cell(coord, color=color)

    def recanvas(self):
        (width, height, levels) = list(self.shape3d(self.maze.cells.shape))
        w = width * SPACING + WALL_THICK + 1
        h = height * SPACING + WALL_THICK + 1
        keys = list(self.tabs.keys())   # must be a copy
        # Get rid of excess levels
        for key in keys:
            canvas = self.tabs[key]
            if key >= levels:
                frame = canvas.master
                canvas.hbar.destroy()
                canvas.vbar.destroy()
                self.note_book.forget(frame)
                canvas.destroy()
                frame.destroy()
                del self.tabs[key]
            else:
                canvas.configure(width=w, height=w)
        # Clear existing levels and add any needed
        for level in range(levels):
            if level in keys:
                self.tabs[level].delete("all")
            else:
                self.tabs[level] = self.add_book(self.note_book,level)
        pass

    def gen_event(self, **kwargs):
        # Was there a visible update?
        visible = True
        match kwargs["event"]:
            case "generated":
                self.state = State.GENERATED
                self.stepper = lambda : None
                self.update_states()
            case "clear-cell":
                self.draw_cell(kwargs["current"], cell=0, color=COLOR_CLEAR)
            case "mark-cell":
                self.draw_cell(kwargs["current"])
            case "walk-start":
                self.draw_cell(kwargs["current"], cell=Maze.INMAZE)
            case "walk-end":
                cells = kwargs["cells"]
                self.draw_cell(kwargs["current"], cell=cells[0])
            case "walk-step":
                cells = kwargs["cells"]
                self.draw_cell(kwargs["current"],
                    cell=cells[0], color=COLOR_WALK)
            case "walk-loop":
                cells = kwargs["cells"]
                self.draw_cell(kwargs["neighbor"],
                    cell=cells[1], color=COLOR_LOOP)
            case _:
                visible = False
        return visible

    def solve_event(self, **kwargs):
        # Was there a visible update?
        visible = True
        match kwargs["event"]:
            case "solved":
                self.state = State.SOLVED
                self.stepper = lambda : None
                self.update_states()
            case "random-start":
                self.tstart=kwargs["start"]
                self.draw_cell(kwargs["start"])
            case "random-end":
                self.tend=kwargs["end"]
                self.draw_cell(kwargs["end"])
            case "dead-end":
                self.draw_cell(kwargs["current"], color=COLOR_DEAD)
            case "solution":
                coord = kwargs["current"]
                if coord in (self.start, self.tstart):
                    color = COLOR_START
                elif coord in (self.end, self.tend):
                    color = COLOR_END
                else:
                    color = COLOR_SOLUTION
                self.draw_cell(coord, color=color)
            case _:
                visible = False
        return visible

    def grid_maze(self, /, *, cells = None, walls = None):
        shape = self.shape3d(self.maze.cells.shape)
        for level in range(shape[2]):
            self.grid_level(level, cells = cells, walls = walls)

    def grid_level(self, level, /, *, cells = None, walls = None):
        try:
            canvas = self.tabs[level]
        except Exception:
            return

        if walls is None: walls=COLOR_WALL
        shape = self.shape2d(self.maze.cells.shape)
        (width, height) = shape[0:2]

        # A note about lines:
        # When you say you want a line from (X1,Y) to (X2,Y) it will
        # draw the line centered on Y.  If we are to acurarately fill
        # a cell inside that, we need to shift the walls a bit.
        # Hense the fudge factor.   It might be best to keep the line
        # widths an odd number.
        fudge = int(WALL_THICK // 2)
        xleft = LEFT_MARGIN                  # X coord of leftmost wall
        xright = xleft + width * SPACING    # X coord of rightmost wall
        ytop = TOP_MARGIN                    # Y coord of topmost wall
        ybottom = ytop + height * SPACING   # Y coord of botommost wall

        if cells is not None:
            canvas.create_rectangle(
                xleft, ytop, xright, ybottom,
                outline=cells,
                fill=cells,
                width=0
            )

        # Vertical lines
        x = xleft + fudge
        for i in range(width + 1):
            canvas.create_line(
                x, ytop, x, ybottom + WALL_THICK,
                fill=walls,
                width=WALL_THICK
            )
            #canvas.create_line(x,ybottom + 10,x,ybottom+20,fill='red',width=1)
            x += SPACING

        # Horizontal lines
        y = ytop + fudge
        for i in range(height + 1):
            canvas.create_line(
                xleft, y, xright + WALL_THICK, y,
                fill=walls,
                width=WALL_THICK
            )
            #canvas.create_line(xright + 10,y,xright+20,y,fill='red',width=1)
            y += SPACING

    def draw_cell(self, coord, /, *, color=None, cell=None):
        shape = self.maze.cells.shape
        for i in range(len(shape)):
            if (n := coord[i]) < 0 or shape[i] <= n:
                return
        if cell is None:
            cell = self.maze.cells[coord]
        (x, y, z) = self.coord3d(coord)

        # Get the canvas we will act upon
        try:
            canvas = self.tabs[z]
        except Exception:
            return

        # A note about lines:
        # When you say you want a line from (X1,Y) to (X2,Y) it will
        # draw the line centered on Y.  If we are to acurarately fill
        # a cell inside that, we need to shift the walls a bit.
        # Hense the fudge factor.   It might be best to keep the line
        # widths an odd number.
        fudge = int(WALL_THICK // 2)
        leftwall = LEFT_MARGIN + x * SPACING     # X of left wall
        leftcell = leftwall + WALL_THICK         # X of left side of cell
        rightwall = leftwall + SPACING          # X of right wall
        rightcell = rightwall - 1               # X of right side of cell
        topwall = TOP_MARGIN + y * SPACING       # Y of top wall
        topcell = topwall + WALL_THICK           # Y of top side of Cell
        bottomwall = topwall + SPACING          # Y of bottom wall
        bottomcell = bottomwall - 1             # Y of bottom side of cell
        xcenter = leftcell + HALF_CELL
        ycenter = topcell + HALF_CELL

        doors = self.maze.bits(cell & Maze.DIR)
        arrows = list()

        fill = self.bg_color
        if (cell & Maze.INUSE) == 0:
            if cell & Maze.DIR:
                # must be doing random walk
                fill = COLOR_WALK
                arrows = doors
                doors = list()
            else:
                fill = COLOR_CLEAR
        elif cell & Maze.HIDDEN:
            fill = COLOR_BLOCK
            doors = list()
        elif cell & Maze.INUSE:
            fill = self.bg_color

        if coord in (self.start, self.tstart):
            fill = COLOR_START
        elif coord in (self.end, self.tend):
            fill = COLOR_END

        if color is not None:
            fill = color

        # Draw cell within the walls
        canvas.create_rectangle(
            leftcell - 1, topcell - 1, rightwall, bottomwall,
            fill=fill,
            width=0
        )

        #doors = list()

        # Erase the walls that are really doors
        for dir in doors:
            match dir:
                case Maze.N:
                    y = topwall + fudge
                    xy = (leftcell - 1, y, rightcell + 1, y)
                case Maze.E:
                    x = rightwall + fudge
                    xy = (x, topcell - 1, x, bottomcell + 1)
                case Maze.S:
                    y = bottomwall + fudge
                    xy = (leftcell - 1, y, rightcell + 1, y)
                case Maze.W:
                    x = leftwall + fudge
                    xy = (x, topcell - 1, x, bottomcell + 1)
                case _:
                    continue
            (x0, y0, x1, y1) = xy
            canvas.create_line(x0, y0, x1, y1,
                fill=fill,
                width=WALL_THICK + 1,
            )

        # Draw arrows when walking
        for dir in arrows:
            match dir:
                case Maze.N:
                    xy = (xcenter, ycenter, xcenter, ycenter - ARROW_LEN)
                case Maze.E:
                    xy = (xcenter, ycenter, xcenter + ARROW_LEN, ycenter)
                case Maze.S:
                    xy = (xcenter, ycenter, xcenter, ycenter + ARROW_LEN)
                case Maze.W:
                    xy = (xcenter, ycenter, xcenter - ARROW_LEN, ycenter)
                case _:
                    continue
            (x0, y0, x1, y1) = xy
            canvas.create_line(x0, y0, x1, y1,
                fill=COLOR_ARROW,
                width=ARROW_THICK,
                arrow=tk.LAST,
            )

class GenericMainMenu(tk.Menu):
    """The main menu"""

    styles = dict()
    accelerators = {
        "quit": "Ctrl+Q"
    }
    keybinds = {
        "<Control-q>": "<<FileQuit>>"
    }

    def __init__(self, parent, settings, **kwargs):
        super().__init__(parent, **kwargs)
        self.settings = settings
        self._menus = dict()
        self._build_menu()
        self._bind_accelerators()

    def _build_menu(self):
        # File menu
        self._menus["File"] = tk.Menu(self, tearoff = False, **self.styles)
        self._add_quit(self._menus["File"])
        self.add_cascade(label="File", menu=self._menus["File"])

        # Help menu
        self._menus["Help"] = tk.Menu(self, tearoff = False, **self.styles)
        self._add_about(self._menus["Help"])
        self.add_cascade(label="Help", menu=self._menus["Help"])

    def _event(self, sequence):
        def callback(*_):
            root = self.master.winfo_toplevel()
            root.event_generate(sequence)
        return callback

    def _add_quit(self,menu):
        menu.add_command(
            label="Quit",
            command=self._event("<<FileQuit>>"),
            accelerator=self.accelerators.get("quit"),
            compound=tk.LEFT
        )

    def _add_about(self,menu):
        menu.add_command(
            label="About...",
            command=self.show_about,
            compound=tk.LEFT
        )

    def _bind_accelerators(self):
        for key, sequence in self.keybinds.items():
            self.bind_all(key, self._event(sequence))

    def show_about(self):
        """Show an about dialog"""
        message = "Maze Generator"
        detail = (
            "Copyright 2024, Gary Algier\n\n"
        )
        messagebox.showinfo(title="About", message=message, detail=detail)

class LinuxMainMenu(GenericMainMenu):
    styles = {
        "background": "#333",
        "foreground": "white",
        "activebackground": "#772",
        "activeforeground": "white",
        "relief": tk.GROOVE
    }

    def _build_menu(self):
        # File menu
        self._menus["File"] = tk.Menu(self, tearoff = False, **self.styles)
        self._add_quit(self._menus["File"])
        self.add_cascade(label="File", menu=self._menus["File"])

        # Help menu
        self._menus["Help"] = tk.Menu(self, tearoff = False, **self.styles)
        self._add_about(self._menus["Help"])
        self.add_cascade(label="Help", menu=self._menus["Help"])

class WindowsMainMenu(GenericMainMenu):
    def __init__(self, *args, **kwargs):
        del self.keybinds["<Control-q>"]
        super().__init__(*args, **kwargs)

    def _add_quit(self,menu):
        menu.add_command(
            label="Exit",
            command=self._event("<<FileQuit>>"),
            compound=tk.LEFT
        )

    def _build_menu(self):
        # File menu
        self._menus["File"] = tk.Menu(self, tearoff = False)
        self._add_quit(self._menus["File"])
        self.add_cascade(label="File", menu=self._menus["File"])

        # Help menu
        self._menus["Help"] = tk.Menu(self, tearoff = False, **self.styles)
        self._add_about(self._menus["Help"])
        self.add_cascade(label="Help", menu=self._menus["Help"])

class MacOsMainMenu(GenericMainMenu):
    keybinds = {
    }
    accelerators = {
    }
    styles = {
        "background": "#333",
        "foreground": "white",
        "activebackground": "#772",
        "activeforeground": "white",
        "relief": tk.GROOVE
    }

    def _build_menu(self):
        # App Menu
        self._menus["App"] = tk.Menu(self, tearoff=False, name="apple")
        self._add_about(self._menus["App"])
        self._menus["App"].add_separator()

        # File menu
        self._menus["File"] = tk.Menu(self, tearoff = False, **self.styles)
        self.add_cascade(label="File", menu=self._menus["File"])

        # Help menu
        self._menus["Help"] = tk.Menu(self, tearoff = False, **self.styles)
        self.add_cascade(label="Help", menu=self._menus["Help"])

def main():
    import argparse

    app = App("Maze Generator",(500,650))

    parser = argparse.ArgumentParser(description='Maze generator.')
    parser.add_argument('-V', '--version',
                        action='version',
                        version="%(prog)s 1.0")
    parser.add_argument('-l', '--logfile',
                        dest='logfile')
    parser.add_argument('--single-threaded', '--single-thread', '--single',
                        dest='single',
                        action=argparse.BooleanOptionalAction)
    args = parser.parse_args()

    if args.logfile is not None:
        try:
            app.log = open(args.logfile,"w")
        except Exception:
            # Silently ignore errors
            app.log = None
    else:
        app.log = None
    app.single_threaded = args.single
    app.mainloop()

main()
exit(0)
