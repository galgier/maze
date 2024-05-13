# maze -- Maze generators and solvers.

**Warning:** This is a work in progress.  The python/Tkinter application works, with limitations, but this is not intended to be ready to support all features.

What is here...

## maze.py

This is the code that will do the maze generation and solving.
As of this time it supports two generation algorithms and one
solution algorithm.  See Maze.generators and Maze.solvers.

This module supports 2D and 3D orthogonal mazes. There are some
definitions for hexagonal grid cells, but this is untested.

The 3D mazes may be less than ideal in that there is likely to be way
too many openings between layers.  Perhaps a better mechanism can be
created for choosing random directions when traveling.

If run as `py maze.py 10 10` the code will genrate a 2D 10 x 10 maze and output a simple textual represention.

If imported via `from maze import Maze` this module will do the work for the caller.  Likely Maze.callback() should be used to "watch" what is happening.

## mazer.py

This should be run by python.   It will use Tkinter to interact with a
user allowing choice of algorithms, size of mazes, single stepping, etc.

## maze.html

This will some day support running the mazes in a browser by using
pyscript.
