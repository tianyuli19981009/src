import functools
import random
from copy import copy
import numpy as np
from gymnasium.spaces import Discrete, MultiDiscrete

from pettingzoo.utils.env import ParallelEnv
from pettingzoo import ParallelEnv
from utils import *



class DoubleEnvironment(ParallelEnv):
    metadata = {"render_modes": ["human"], "name": "rps_v2"}
    def __init__(self, render_mode=None):
        # goal coordinates
        self.door_x = None
        self.door_y = None
        # prisoner coordinates
        self.prisoner_x = None
        self.prisoner_y = None
        # helper coordinates
        self.helper_x = None
        self.helper_y = None
        # helper latest generated block coordinates 
        self.generated_block_x = None
        self.generated_block_y = None
        # 0 for trap, 1 for bridge
        self.path = np.zeros(8, dtype=int)
        self.timestep = None
        self.possible_agents = ["prisoner", "helper"]
        self.grid = None
        self.discount_factor = 0.99


        self.auxiliary = -1

        
    def reset(self, seed=None, return_info=False, options=None):
        # print("You are resetting")
        self.grid = np.zeros((7, 7), dtype=object)

        
        
        self.agents = copy(self.possible_agents)
        self.timestep = 0
        self.discount_factor = 0.99

        # a list contains all the moveable blocks
        self.bridges = [[0,0]]
        # prisoner coordinates
        self.prisoner_x = 0
        self.prisoner_y = 0
        # helper coordinates
        self.helper_x = 0
        self.helper_y = 0
        # helper latest generated block coordinates 
        self.generated_block_x = 0
        self.generated_block_y = 0
        # goal coordinates
        self.door_x = random.randint(2, 5) 
        self.door_y = random.randint(2, 5)

        self.grid[0][0] = 1
        self.grid[self.door_x][self.door_y] = 1
        # for render function
        self.display = np.zeros((7, 7), dtype=object)
        

        # "path" contains the condition for blocks that are 
        #  all possible for agent to move 
        self.path = np.zeros(8, dtype=int)
        # "bridges" are all indexs of the brdges in the map
        self.bridges.append([self.door_x, self.door_y])

        self.checkPath()

        observations = {
            a: (
                self.prisoner_x + 7 * self.prisoner_y,
                self.door_x + 7 * self.prisoner_y,
                self.helper_x + 7 * self.helper_y,
                self.path[0],self.path[1],  
                self.path[2],self.path[3],  
                self.path[4],self.path[5],  
                self.path[6],self.path[7],                
            )
            for a in self.agents
        }
        return observations


    def step(self, actions):
        # Initialize all variables for return
        terminations = {a: False for a in self.agents}
        truncations = {a: False for a in self.possible_agents}
        rewards = {a: 0 for a in self.agents}
        infos = {a: {} for a in self.possible_agents}

        prisoner_action = actions["prisoner"]
        helper_action = actions["helper"]
        

        # If there does not exist a path, then the heuristic value is -1, else the value is number of steps need to take

        # Manhattan Distance before the solver moves, potential function 
        potential_1 = 1 - (abs(self.prisoner_x - self.door_x) + abs(self.prisoner_y - self.door_y)) / 12 


        # 0-3 building up/down/left/right two blocks in a row
        # 4-7 building up/down/left/right one block
        generated = 0
        if helper_action == 0 and self.helper_x > 1 and (int(self.grid[self.helper_x-1][self.helper_y]) == 0 or int(self.grid[self.helper_x-2][self.helper_y]) == 0):
            generated += 1 if int(self.grid[self.helper_x-1][self.helper_y]) == 0 else 0 
            generated += 1 if int(self.grid[self.helper_x-2][self.helper_y]) == 0 else 0 
            
            self.grid[self.helper_x-1][self.helper_y] = 1
            self.grid[self.helper_x-2][self.helper_y] = 1
            self.bridges.extend(([self.helper_x-1, self.helper_y],
                                 [self.helper_x-2, self.helper_y]))
            
            self.helper_x -= 2
            
            # print("Helper builds up 2 blocks")
        elif helper_action == 1 and self.helper_x < 5 and (int(self.grid[self.helper_x+1][self.helper_y]) == 0 or int(self.grid[self.helper_x+2][self.helper_y]) == 0):
            generated += 1 if int(self.grid[self.helper_x+1][self.helper_y]) == 0 else 0 
            generated += 1 if int(self.grid[self.helper_x+2][self.helper_y]) == 0 else 0 
            
            self.grid[self.helper_x+1][self.helper_y] = 1
            self.grid[self.helper_x+2][self.helper_y] = 1
            self.bridges.extend(([self.helper_x+1, self.helper_y],
                                 [self.helper_x+2, self.helper_y]))
            self.helper_x += 2
            # print("Helper builds down 2 blocks")
        elif helper_action == 2 and self.helper_y > 1 and (int(self.grid[self.helper_x][self.helper_y-1]) == 0 or int(self.grid[self.helper_x][self.helper_y-2]) == 0):
            generated += 1 if int(self.grid[self.helper_x][self.helper_y-1]) == 0 else 0 
            generated += 1 if int(self.grid[self.helper_x][self.helper_y-2]) == 0 else 0 
            
            self.grid[self.helper_x][self.helper_y-1] = 1
            self.grid[self.helper_x][self.helper_y-2] = 1
            self.bridges.extend(([self.helper_x, self.helper_y-1],
                                 [self.helper_x, self.helper_y-2]))
            self.helper_y -= 2
            # print("Helper builds left 2 blocks")
        elif helper_action == 3 and self.helper_y < 5 and (int(self.grid[self.helper_x][self.helper_y+1]) == 0 or int(self.grid[self.helper_x][self.helper_y+2]) == 0):
            
            generated += 1 if int(self.grid[self.helper_x][self.helper_y+1]) == 0 else 0 
            generated += 1 if int(self.grid[self.helper_x][self.helper_y+2]) == 0 else 0 

            self.grid[self.helper_x][self.helper_y+1] = 1
            self.grid[self.helper_x][self.helper_y+2] = 1
            self.bridges.extend(([self.helper_x,self.helper_y+1],
                                 [self.helper_x,self.helper_y+2]))
            self.helper_y += 2
            # print("Helper builds right 2 blocks")
        elif helper_action == 4 and self.helper_x > 1 and int(self.grid[self.helper_x-2][self.helper_y]) == 0:
            self.grid[self.helper_x-2][self.helper_y] = 1
            self.bridges.append([self.helper_x-2, self.helper_y])
            self.helper_x -= 2
            generated = 1
            # print("Helper builds up 1 block")
        elif helper_action == 5 and self.helper_x < 5 and int(self.grid[self.helper_x+2][self.helper_y]) == 0:
            self.grid[self.helper_x+2][self.helper_y] = 1
            self.bridges.append([self.helper_x+2, self.helper_y])
            self.helper_x += 2
            generated = 1
            # print("Helper builds down 1 block")
        elif helper_action == 6 and self.helper_y > 1 and int(self.grid[self.helper_x][self.helper_y-2]) == 0:
            self.grid[self.helper_x][self.helper_y-2] = 1
            self.bridges.append([self.helper_x, self.helper_y-2])
            self.helper_y -= 2
            generated = 1
            # print("Helper builds left 1 block")
        elif helper_action == 7 and self.helper_y < 6 and int(self.grid[self.helper_x][self.helper_y+2]) == 0:
            self.grid[self.helper_x][self.helper_y+2] = 1
            self.bridges.append([self.helper_x, self.helper_y+2])
            self.helper_y += 2
            generated = 1
        elif helper_action == 8:
            generated = 0 
            # print("Helper builds right 1 block")




        
        
        # Execute actions   
        # 1 block move: 0 up, 1 down, 2 left, 3 right
        # 2 block move: 4 up, 5 down, 6 left, 7 right
        if prisoner_action == 0 and self.prisoner_x > 0:
            self.prisoner_x -= 1
            # print("Solver moves up")
        elif prisoner_action == 1 and self.prisoner_x < 6:
            self.prisoner_x += 1
            # print("Solver moves down")
        elif prisoner_action == 2 and self.prisoner_y > 0:
            self.prisoner_y -= 1
            # print("Solver moves left")
        elif prisoner_action == 3 and self.prisoner_y < 6:
            self.prisoner_y += 1
            # print("Solver moves right")
        
        # 2 block move: 4 up, 5 down, 6 left, 7 right
        elif prisoner_action == 4 and self.prisoner_x > 1:
            self.prisoner_x -= 2
            # print("Solver moves up")
        elif prisoner_action == 5 and self.prisoner_x < 5:
            self.prisoner_x += 2
            # print("Solver moves down")
        elif prisoner_action == 6 and self.prisoner_y > 1:
            self.prisoner_y -= 2
            # print("Solver moves left")
        elif prisoner_action == 7 and self.prisoner_y < 5:
            self.prisoner_y += 2
        elif prisoner_action == 8:
            pass


        alpha = 1
        beta = 1


        # Manhattan Distance after the solver moves, potential function after the movement
        potential_2 = 1 - (abs(self.prisoner_x - self.door_x) + abs(self.prisoner_y - self.door_y)) / 12 

        


        r_timeout = -self.timestep * 0.03

        # Solver's normal reward
        r_closer = (self.discount_factor * potential_2 - potential_1) * 2  
        rewards["prisoner"] = r_closer + r_timeout

        
        
        # Generator's normal reward's part 1, solver gets closer
        r_inc = r_closer if r_closer > 0 else 0

        # Generator's normal reward's part 2, generator created blocks
        r_internal = 0.2 * generated 
        r_penalty = -0.5 if r_internal == 0 else 0 
        # r_internal = (self.discount_factor 
        
        # print(f'r_internal is: {r_internal}')
        # Original trained well rewards
        rewards["helper"] = r_internal * self.auxiliary + r_timeout + r_inc*3 + r_penalty

        self.checkPath()



            

        # Solver touches the trap
        if [self.prisoner_x, self.prisoner_y] not in self.bridges:
            r_fail = -2
            rewards["prisoner"] += r_fail 
            # Extenal part
            rewards["helper"] += -r_fail * self.auxiliary
            # rewards["helper"] += r_fail 

            terminations = {a: True for a in self.agents}
            self.agents = []
        # Solver reach the goal
        elif self.prisoner_x == self.door_x and self.prisoner_y == self.door_y:
            r_complete = 2
            rewards["prisoner"] += r_complete 
            # Extenal part
            # rewards["helper"] += r_complete * self.auxiliary
            # rewards["helper"] += r_complete 
            infos['prisoner'] = "Completed"
            print("Reaches the Goal!")
            terminations = {a: True for a in self.agents}
            self.agents = []


        # Check truncation conditions (overwrites termination conditions)
        if self.timestep > 20:
            rewards["prisoner"] += r_timeout 
            rewards["helper"] += r_timeout
            print("Time out")
            truncations = {"prisoner": True, "helper": True}
            self.agents = []
        self.timestep += 1

        # Get observations
        observations = {
            a: (
                self.prisoner_x + 7 * self.prisoner_y,
                self.door_x + 7 * self.prisoner_y,
                self.helper_x + 7 * self.helper_y,
                self.path[0],self.path[1],  
                self.path[2],self.path[3],  
                self.path[4],self.path[5],  
                self.path[6],self.path[7],  
            )
            for a in self.possible_agents
        }

        

        return observations, rewards, terminations, truncations, infos


    def checkPath(self):
        # up one
        self.path[0] = 1 if self.prisoner_x > 0 and [self.prisoner_x-1, self.prisoner_y] in self.bridges else 0
        # up two
        self.path[1] = 1 if self.prisoner_x > 1 and [self.prisoner_x-2, self.prisoner_y] in self.bridges else 0
        # down one
        self.path[2] = 1 if self.prisoner_x < 6 and [self.prisoner_x+1, self.prisoner_y] in self.bridges else 0
        # down two
        self.path[3] = 1 if self.prisoner_x < 5 and [self.prisoner_x+2, self.prisoner_y] in self.bridges else 0
        # left one
        self.path[4] = 1 if self.prisoner_y > 0 and [self.prisoner_x, self.prisoner_y-1] in self.bridges else 0
        # left two
        self.path[5] = 1 if self.prisoner_y > 1 and [self.prisoner_x, self.prisoner_y-2] in self.bridges else 0
        # right one
        self.path[6] = 1 if self.prisoner_y < 6 and [self.prisoner_x, self.prisoner_y+1] in self.bridges else 0
        # right two
        self.path[7] = 1 if self.prisoner_y < 5 and [self.prisoner_x, self.prisoner_y+2] in self.bridges else 0



    def render(self):
        # grid = np.zeros((7, 7))

        for coord in self.bridges:
            self.display[coord[0]][coord[1]] = '1'        
        self.display[self.prisoner_x][self.prisoner_y] = 'P'
        self.display[self.door_x][self.door_y] = 'D'

        for x in range(len(self.display)):
            for y in range(len(self.display[x])):
                if self.display[x][y] == 0:
                    self.display[x][y] = '0'

        print(f"{self.display} \n")

    @functools.lru_cache(maxsize=None)
    def observation_space(self, _event=None):
        return MultiDiscrete([47,47,47,2,2,2,2,2,2,2,2])

    @functools.lru_cache(maxsize=None)
    def action_space(self, _event=None):
        return Discrete(9)


from pettingzoo.test import parallel_api_test # noqa: E402
from pettingzoo.test import render_test
if __name__ == "__main__":
    parallel_api_test(DoubleEnvironment(), num_cycles=1_000_000)
 