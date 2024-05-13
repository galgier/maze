""" Class Maze
    An object type to represent a Maze as well as some utility functions.
    There are multiple generators (and solvers?) defined here that use
    different algorithms.
    See attributes Maze.generators and Maze.solutions.
"""

# vim: ts=4 sw=4 expandtab

"""

Notes:

Though in most cases people think of mazes as orthogonal arrangements
in one plane, we want to support potential multilevel mazes as well
as hexagonal or even circular mazes.   Defaults will be based on 2D
orthogonal mazes.

Unfortunately, there are different ways to represent coordinate systems
and compass directions:
    -- Typical geometry places the X access on the horizontal, the
    Y access on the vertical.  0 degrees is along the X, 90 degrees along
    the Y.
    -- Typical maps have north 0 degrees going up, along the Y access,
    east 90 degrees along the X access.
    -- Then most graphics systems, printers, etc. have Y increase
    down the page or screen.

Here is what the author chose:
    -- X increases left to right.
    -- Y increases top to bottom.
    -- Z increases deaper into the screen or to later pages
    -- N is 90 degrees and towards decreasing Y
    -- E is 0 degrees and towards increasing X
    -- Up is towards decreasing Z

A hex grid looks like this (or as close as ASCII art can represent
while not using back-slashes):
     *---*    *---*
    /     `  /     `
   *       **       *
    `     /  `     /
     *---*    *---*
This means that hexagons have no neighbors east or west, but have them
north, south, north-east, NW, SE, and SW.  IE, every 60 degrees starting
at 30 degrees.   This was done to make the tops and bottoms parallel to
the top and bottom of the screen which is more pleasing to the author.

When mapping the hexagons to an x,y labeling, the top corner is
still 0,0.  But then the cell to the south-east is 1,0, south is 0,1, etc.

I use the arrays defined by numpy.   These allow some useful methods
that can be applied to the whole array.   They also can be indexed
by a coordinate that is a tuple.   This means that the maze can be
2D, 3D or even 10D and a lot of the code woould work the same.
There are a few places I do check if the third dimension is just a
single layer.  This makes random direction descisions faster.  One
does not need to generate all 6 directional choices when two of
them woould be discarded as "off grid" anyway.

"""

import sys
import random
import numpy as np

__all__ = [ 'Maze' ]

class Direction:
    def __init__(self,val,opposite,name,deltas):
        self.val = val
        self.name = name
        self.opposite = opposite
        self.deltas = deltas

class Maze:
    # Maze cell state and directions:
    # The directions represent openings in the walls.
    # We use _ to keep track of bit as we walk it to the left.
    # We also create the masks as we go.
    _ = 1
    STATE = 0
    STATE = STATE | (INMAZE := _)                  # a cell in the maze
    STATE = STATE | (HIDDEN := (_ := _ * 2))       # a cell to be hidden
    STATE = STATE | (SOLUTION := (_ := _ * 2))     # part of the solution
    STATE = STATE | (NOTSOLUTION := (_ := _ * 2))  # not part of solution
    INUSE = INMAZE | HIDDEN     # only these affect emptiness
    DIR = 0
    DIR = DIR | (E  := (_ := _ * 2))   # 0 degrees
    DIR = DIR | (NE := (_ := _ * 2))   # 30 degrees
    DIR = DIR | (N  := (_ := _ * 2))   # 90 degrees
    DIR = DIR | (NW := (_ := _ * 2))   # 150 degrees
    DIR = DIR | (W  := (_ := _ * 2))   # 180 degrees
    DIR = DIR | (SW := (_ := _ * 2))   # 210 degrees
    DIR = DIR | (S  := (_ := _ * 2))   # 270 degrees
    DIR = DIR | (SE := (_ := _ * 2))   # 330 degrees
    DIR = DIR | (U := (_ := _ * 2))
    DIR = DIR | (D := (_ := _ * 2))
    del _

    def wilsons_generate(self, log=None, callback = None):

        def walk(start):
            # used to clean up loops
            def clearpath(start,end):
                while start != end:
                    direction = self.cells[start] & Maze.DIR
                    self.cells[start] &= ~Maze.DIR
                    # been there so no need to check for out of bounds
                    neigh = tuple(map(
                        lambda i, j: i + j,
                        start,
                        self.compass[direction].deltas
                    ))
                    self.event(event="clear-cell",
                        cell=self.cells[start],
                        current=start
                    )
                    start = neigh
            def markpath(start,end):
                # all but the end cell are empty
                # this is used to "remember" how to go back the other way
                opposite = 0
                while start != end:
                    direction = self.cells[start] & Maze.DIR
                    # record the opposite direction and mark as in the maze
                    self.cells[start] |= (opposite | Maze.INMAZE)
                    # save opposite for next cell
                    opposite = self.compass[direction].opposite
                    # been there so no need to check for out of bounds
                    neigh = tuple(map(
                        lambda i, j: i + j,
                        start,
                        self.compass[direction].deltas
                    ))
                    self.event(event="mark-cell",
                        cell=self.cells[start],
                        current=start,
                    )
                    start = neigh
                self.cells[end] |= opposite

            directions = list(self.compass.keys())

            self.event(event="walk-start",
                cell=self.cells[start],
                current=start
            )
            current = start
            walking = True
            while walking:
                # pick a neighbor
                direction = directions[self.rand.integers(len(directions))]
                # coordinates of neighbor
                neigh = tuple(map(
                    lambda i, j: i + j,
                    current,
                    self.compass[direction].deltas
                ))
                if not self.inbound(neigh) or (self.cells[neigh] & Maze.HIDDEN):
                    # go back and try another direction
                    continue

                # did we find a maze cell?
                if self.cells[neigh] & Maze.INMAZE:
                    # record what direction we went
                    self.cells[current] &= ~Maze.DIR
                    self.cells[current] |= direction
                    self.event(event="walk-end",
                        cells=(
                            self.cells[current],
                            self.cells[neigh]
                        ),
                        current=current,
                        neighbor=neigh,
                    )
                    markpath(start,neigh)
                    # we are done
                    walking = False
                # or did we loop?
                elif self.cells[neigh] & Maze.DIR:
                    self.event(event="walk-loop",
                        cells=(
                            self.cells[current],
                            self.cells[neigh]
                        ),
                        current=current,
                        neighbor=neigh,
                    )
                    # record what direction we went
                    self.cells[current] &= ~Maze.DIR
                    self.cells[current] |= direction
                    # clean up the loop and continue from here
                    clearpath(neigh,current)
                    # forget the direction from last try
                    self.cells[current] &= ~Maze.DIR
                    current = neigh
                # else we need to keep looking
                else:
                    # record what direction we went and continue
                    self.cells[current] &= ~Maze.DIR
                    self.cells[current] |= direction
                    self.event(event="walk-step",
                        cells=(
                            self.cells[current],
                            self.cells[neigh]
                        ),
                        current=current,
                        neighbor=neigh,
                    )
                    current = neigh

            # we are done
            self.event(event="walked")

        self.log = log
        self.callback = callback

        self.clean()
        
        self.event(event="generating")

        empties = ((self.cells & Maze.INUSE) == 0).nonzero()
        # if maze is empty
        if empties[0].size:
            # we need at least one cell in the maze
            # pick an empty
            emlist = list(zip(*empties))
            coord = emlist[self.rand.integers(len(emlist))]
            self.cells[coord] = Maze.INMAZE
            self.event(event="mark-cell",
                cell=self.cells[coord],
                current=coord
            )
            # update the lists
            empties = ((self.cells & Maze.INUSE) == 0).nonzero()

        # while there are empty cells
        while empties[0].size:
            # pick a cell to start a walk
            emlist = list(zip(*empties))
            coord = emlist[self.rand.integers(len(emlist))]
            walk(coord)
            # update the list
            empties = ((self.cells & Maze.INUSE) == 0).nonzero()
        self.event(event="generated")

    def recursive_generate(self, log=None, callback = None):
        self.log = log
        self.callback = callback

        self.clean()

        self.event(event="generating")

        empties = ((self.cells & Maze.INUSE) == 0).nonzero()
        # While there are empty cells
        while empties[0].size:
            emlist = list(zip(*empties))
            # pick a random empty
            current = emlist[self.rand.integers(len(emlist))]
            self.recurse_gen(current)
            # update the list
            empties = ((self.cells & Maze.INUSE) == 0).nonzero()
        self.event(event="generated")

    def recurse_gen(self, current):
        self.cells[current] |= Maze.INMAZE
        self.event(event="mark-cell",
            cell=self.cells[current],
            current=current,
        )
        directions = list(self.compass.keys())
        self.rand.shuffle(directions)
        for direction in directions:
            neigh = tuple(map(
                lambda i, j: i + j,
                current,
                self.compass[direction].deltas
            ))
            if not self.inbound(neigh) or (self.cells[neigh] & Maze.INUSE):
                # go back and try another direction
                continue
            # Empty.  Claim it, remember the direction we went and recurse.
            self.cells[current] |= direction
            self.event(event="mark-cell",
                cell=self.cells[current],
                current=current,
            )
            opposite = self.compass[direction].opposite
            self.cells[neigh] |= (Maze.INMAZE | opposite)
            self.recurse_gen(neigh)

    def random_start(self, start=None):
        # if start is not given, choose random from left of highest level
        if start is not None:
            return start
        shape = self.cells.shape
        coord = map(lambda x: 0, shape)
        if (n := len(shape)) < 2 or n > 3:
            self.event(event="random-start",
                start=coord
            )
            return coord
        coord = list(coord)
        possible = []
        for coord[0] in range(shape[0]):
            if not (self.cells[tuple(coord)] & Maze.HIDDEN):
                possible.append(coord.copy())
        if len(possible) == 0:
            # Why would someone make all the cells hidden?
            # In that case, I don't care if it is
            coord[0] = 0
        else:
            self.rand.shuffle(possible)
            coord = possible[0]
        coord = tuple(coord)
        self.event(event="random-start",
            start=coord
        )
        return coord

    def random_end(self, end=None):
        # if end is not given, choose random from right of lowest level
        if end is not None:
            return end
        shape = self.cells.shape
        coord = map(lambda x: max(0,x-1), shape)
        if (n := len(shape)) < 2 or n > 3:
            self.event(event="random-start",
                start=coord
            )
            return coord
        coord = list(coord)
        possible = []
        maxx = coord[0]
        for coord[0] in range(shape[0]):
            if not (self.cells[tuple(coord)] & Maze.HIDDEN):
                possible.append(coord.copy())
        if len(possible) == 0:
            # Why would someone make all the cells hidden?
            # In that case, I don't care if it is
            coord[0] = maxx
        else:
            self.rand.shuffle(possible)
            coord = possible[0]
        coord = tuple(coord)
        self.event(event="random-end",
            end=coord
        )
        return coord

    def mouse_solve(self, log=None, callback = None, start=None, end=None):
        self.log = log
        self.callback = callback
        start = self.random_start(start = start)
        end = self.random_end(end = end)
        pass
    def deadend_solve(self, log=None, callback = None, start=None, end=None):
        def countdoors(cell):
            return len(self.bits(cell & Maze.DIR))
        def backfill(thecopy,dead):
            while countdoors(thecopy[dead]) == 1:
                thecopy[dead] |= Maze.NOTSOLUTION
                self.event(event="dead-end",
                    current=dead,
                    cell=self.cells[dead]
                )
                direction = thecopy[dead] & Maze.DIR
                opposite = self.compass[direction].opposite
                # coordinates of neighbor
                neigh = tuple(map(
                    lambda i, j: i + j,
                    dead,
                    self.compass[direction].deltas
                ))
                # close the doors
                thecopy[dead] &= ~direction
                thecopy[neigh] &= ~(opposite)
                dead = neigh
                if dead in (start, end):
                    break

        self.log = log
        self.callback = callback
        start = self.random_start(start = start)
        end = self.random_end(end = end)

        # copy the cells because we are going to temporarily close doos
        thecopy = np.copy(self.cells)

        # look for cells with only one door
        while True:
            counts = np.zeros_like(thecopy)
            for coord in zip(*np.nonzero(thecopy & Maze.DIR)):
                counts[coord] = countdoors(thecopy[coord])
            deadends = (counts == 1).nonzero()
            deadlist = list(filter(
                lambda x: x != start and x != end,
                zip(*deadends)
            ))
            if len(deadlist) == 0:
                break
            # we shuffle to make it interesting for anyone watching
            self.rand.shuffle(deadlist)
            for dead in deadlist:
                backfill(thecopy,dead)

        # whats left must be the solution
        solution = ((thecopy & (Maze.NOTSOLUTION|Maze.HIDDEN)) == 0).nonzero()
        for coord in zip(*solution):
            self.event(event="solution",
                current=coord,
                cell=self.cells[coord]
            )
        self.event(event="solved",
            start=start,
            end=end
        )

    # generators:
    #   A list of tuples.   Each tuple has three entries:
    #   -- An algorithm name.
    #   -- The function to generate the maze.
    #   -- A description.
    generators = [
        (
            "Wilson's Algorithm",
            wilsons_generate,
            """
This algorithm uses loop-erased random walks:
    1. Pick a random cell and mark it as in the maze.
    2. Repeat the following random walk until all cells are part of the maze:
        1. Pick a random cell not yet part of the maze.
        2. Pick a random direction and mark the current cell with an arrow.
        3. Walk in that direction.
        4. If the new cell is part of the maze, mark the partial path
           as in the maze go perform a new walk.
        5. Else if the cell hit is already part of the random walk,
           a loop has been created.  Follow the arrows to erase the loop
           and continue the same walk.
        6. Else keep walking.
This algorithm generates an unbiased sample from the uniform distribution
over all mazes.

See Wikipedia: https://en.wikipedia.org/wiki/Maze_generation_algorithm
"""
        ),
        (
            "Recursive Backtracker",
            recursive_generate,
            """
This algorithm uses a recursive depth first approach:
    1. Given a current cell as a parameter
    2. Mark the current cell as visited
    3. While the current cell has any unvisited neighbour cells
        1. Choose one of the unvisited neighbours
        2. Remove the wall between the current cell and the chosen cell
        3. Invoke the routine recursively for the chosen cell
This algorithm is biased towards long corridors.

See Wikipedia: https://en.wikipedia.org/wiki/Maze_generation_algorithm
"""
        ),
    ]
    # solvers:
    #   A list of tuples.   Each tuple has three entries:
    #   -- An algorithm name.
    #   -- The function to solve the maze.
    #   -- A description.
    solvers = [
### **Not Yet Implemented**
###         (
###             "Random Mouse Algorithm",
###             mouse_solve,
###             """
### This is a trivial method that can be implemented by a very unintelligent
### robot or perhaps a mouse. It is simply to proceed following the current
### passage until a junction is reached, and then to make a random decision
### about the next direction to follow.
### 
### See Wikipedia: https://en.wikipedia.org/wiki/Maze-solving_algorithm
### """
###         ),
        (
            "Dead End Backfill",
            deadend_solve,
            """
Viewing from above, find all the dead ends and fill them in.  Repeat.
Anything left is a solution.  This is often how humans will solve maze
diagrams.
"""
        ),
    ]

    Orthogonal2D = (
        #                        dx  dy
        Direction(N,S,"North",  ( 0, -1)),
        Direction(E,W,"East",   ( 1,  0)),
        Direction(S,N,"South",  ( 0,  1)),
        Direction(W,E,"West",   (-1,  0)),
    )
    Orthogonal3D = (
        #                       dx  dy  dz
        Direction(N,S,"North", ( 0,  1,  0)),
        Direction(E,W,"East",  ( 1,  0,  0)),
        Direction(S,N,"South", ( 0, -1,  0)),
        Direction(W,E,"West",  (-1,  0,  0)),
        Direction(U,D,"Up",    ( 0,  0, -1)),
        Direction(D,U,"Down",  ( 0,  0,  1)),
    )
    Hexagonal2D = (
        # untested hexagonal grid
        #                       dx  dy
        Direction(NE,SW,"NE",  ( 1,  0)),
        Direction(N,S,"N",     ( 0, -1)),
        Direction(NW,SE,"NW",  (-1,  0)),
        Direction(SW,NE,"SW",  (-1,  1)),
        Direction(S,N,"S",     ( 0,  1)),
        Direction(SE,NW,"SE",  ( 1,  1)),
    )

    def clean(self):
        # clean up the cells keeping only the hidden cells
        self.cells &= Maze.HIDDEN

    def unsolve(self):
        # remove only solution data
        self.cells &= ~(Maze.SOLUTION | Maze.NOTSOLUTION)

    def clear(self,shape = None):
        # all new, empty maze.
        self.cells = np.zeros(
            shape if shape is not None else self.cells.shape,
            dtype=int)

    def inbound(self,coord):
        shape = self.cells.shape
        if type(shape) != type(coord) or len(shape) != len(coord):
            return False
        return not any(map(lambda x,y: x < 0 or x >= y, coord, shape))

    def __init__(self,
        shape,              # shape of cells array
        /, *,
        directions = None,  # tuple or list of directions
    ):
        # these can be redefined
        self.rand = np.random.default_rng()         # alternative RNG
        self.log = None                             # io for logging
        self.callback = None                        # callback on events

        self.clear(shape)
        n = len(self.cells.shape)
        if directions is None:
            if n == 2 or (n == 3 and list(self.cells.shape)[2] == 1):
                directions = self.Orthogonal2D
            elif n == 3:
                directions = self.Orthogonal3D
            else:
                raise ValueError(
                    'maze shape must be 2D or 3D to use default directions')
        self.compass = {}
        for direction in directions:
            self.compass[direction.val] = direction

    def bits(self,n):
        result = []
        while n:
            i = (n - 1) & n
            result.append(i ^ n)
            n = i
        return result

    def event(self,**kwargs):
        if self.log is not None:
            self.log.write(str(kwargs))
            self.log.write("\n")
            self.log.flush()
        if self.callback is not None:
            self.callback(**kwargs)


def show(cells):
    # we can only display 2D and the x-axis only works with small values
    #
    # though this is only used in main() for the final results,
    # this can be used during debugging to peek at the progress
    #
    # cells will look like this:
    #   +--+--+--+
    #   |  |  |  |  Closed, empty cell
    #   +--+--+--+
    #   |  |##|  |  Ignored, hidden room
    #   +--+--+--+
    #   |  |<<|  |  Walking west
    #   +--+--+--+
    #   |  |>>|  |  Walking east
    #   +--+--+--+
    #   |  |^^|  |  Walking north
    #   +--+--+--+
    #   |  |VV|  |  Walking south
    #   +--+--+--+
    #   |  |     |  Connected on the side
    #   +--+--+--+
    #   |  |  |  |  Connected below
    #   +--+  +--+
    #   |  |  |  |  Connected Above
    #   +--+--+--+

    shape = cells.shape
    if len(shape) != 2: return
    (width,height,*junk) = shape

    xaxis = [ f"{x:2}" for x in range(width) ]
    horiz = ["--"] * width
    below = horiz.copy()
    print(" " + " ".join(xaxis))
    for y in range(height):
        above = below
        below = horiz.copy()
        line = ""
        right = "|"
        for x in range(width):
            left = right
            right = "|"
            cell = "--"
            c = cells[x,y]
            if c & Maze.HIDDEN:
                # brick up hidden rooms
                cell = "##"
            elif c & Maze.INMAZE:
                cell = "  "
                # knock down walls
                if c & Maze.N: above[x] = "  "
                if c & Maze.E: right = " "
                if c & Maze.S: below[x] = "  "
                if c & Maze.W: left = " "
            else:
                # must be walking, show arrow
                if c & Maze.N: cell = "^^"
                if c & Maze.E: cell = ">>"
                if c & Maze.S: cell = "VV"
                if c & Maze.W: cell = "<<"
            line += left + cell
        line += right
        print("+" + "+".join(above) + "+")
        print(line,f"{y:2}")
    print("+" + "+".join(below) + "+")
    print(" " + " ".join(xaxis))

if __name__ == '__main__':

# this test code only generates 2D mazes and only outputs a textual
# representation of the maze.

    def main():
        import argparse

        parser = argparse.ArgumentParser(
            description='Maze generator algorithm.'
            )
        parser.add_argument('width',type=int)
        parser.add_argument('height',type=int)
        parser.add_argument('-V', '--version',
                            action='version',
                            version="%(prog)s 1.0")
        parser.add_argument('-l', '--logfile',
                            dest='logfile')
        args = parser.parse_args()

        maze = Maze((args.width,args.height))
        if args.logfile is not None:
            with open(args.logfile,"w") as logfile:
                maze.log = logfile
                maze.wilsons_generate()
        else:
            maze.wilsons_generate()
        show(maze.cells)

    main()
    exit(0)
