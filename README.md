# maze -- Maze generators and solvers.

What is here:
    **maze.py**
        This is the code that will do the maze generation and solving.
        As of this time it supports two generation algorithms and one
        solution algorithm.  See Maze.generators and Maze.solvers.

        This module supports 2D and 3D orthogonal mazes.   The 3D mazes may be less than ideal in that there is likely to be way too many openings between layers.   There are some definitions for hexagonal grid cells, but this is untested.

        If invoked such as:
            py maze.py 10 10
        the code will genrate a 2D maze and output a simple textual
        represention.

        If imported:
            from maze import Maze
        this module will do the work for the caller.  Likely
        Maze.callback() should be used to "watch" what is happening.

            
