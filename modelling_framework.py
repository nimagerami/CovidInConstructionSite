__author__ = "Nima Gerami Seresht"
__copyright__ = "Copyright 2021"
__license__ = "MIT"
__version__ = "0.0.1"
__maintainer__ = "Nima Gerami Seresht"
__email__ = "nima.geramiseresht@gmail.com"
__status__ = "Prototype"

from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
import numpy as np


class CovidModel(Model):
    """An agent-based model with a specific number of agents "N", the dimensions of the site "width" and "height"; and
       the ratio of crew with Covid infection.
    """
    def __init__(self, N, n_crew, width, height, infection_rate = 0, x_warehouse = 0, \
                 y_warehouse = 0, workhours = 8, task_randomizer = [0.60, 0.05, 0.35], \
                     mortality_rate = 0.02, transmission_chance = 0.25, reinfection_chance = 0.01):
        self.num_agents = N
        self.grid = MultiGrid(width, height, True)
        self.schedule = RandomActivation(self)
        self.infection_rate = infection_rate
        self.warehouse_pos = (int(x_warehouse), int(y_warehouse))
        self.infection_log = [[], [], []]
        self.active_agents = N
        self.workhours = workhours
        self.n_crew = n_crew
        self.crew_loc = []
        self.task_randomizer = task_randomizer
        self.mortality = []
        self.mortality_rate = mortality_rate
        self.transmission_chance = transmission_chance
        self.reinfection_chance = reinfection_chance
        # Create agents
        
        for i in range(self.n_crew):
            x = self.random.randrange(self.grid.width)
            y = self.random.randrange(self.grid.height)
            self.crew_loc.append((x, y))
        
        for i in range(self.num_agents):
            work_location = self.random.choice(self.crew_loc)
            a = CovidAgent(i, self, work_location)
            self.schedule.add(a)
            self.grid.place_agent(a, work_location)
        
            
    def step(self):
        #if self.schedule.time % (60 * self.workhours) == 0:
        if self.schedule.time == 0:
            for agent in self.random.sample(self.schedule.agents,int(self.num_agents * self.infection_rate)):
                if agent.state == 1:
                    agent.state = 2
                    agent.infection_time.append(self.schedule.time)
                
        self.schedule.step()

#-------------------------------------------------------------
class CovidAgent(Agent):
    '''
        self.task indicates the state of agent at work, 1 is handling material or equipment;
        2 is working directly on task; 3 is traverling on the site or doing personal tasks.
    '''
    def __init__(self, unique_id, model, work_location):
        super().__init__(unique_id, model)
        self.state = 1
        self.infection_time = []
        self.task = 2
        self.work_location = work_location
        self.immunity = False

#-------------------------------------------------------------
    def step(self):
        
        if self.state > 1:
            infection_duration = self.model.schedule.time - self.infection_time[-1]
            self.HealthCheck(infection_duration)

        if self.task == 1:
            self.WarehouseTravel()
        else:
            self.TaskDecider()
            if self.task == 2:
                self.model.grid.move_agent (self, self.work_location)
            elif self.task == 3:
                self.RandomWalk()

        self.InfectionTransmission()
#-------------------------------------------------------------        
    def RandomWalk(self):
        possible_position = self.model.grid.get_neighborhood(self.pos, moore = True, include_center = True)
        new_postion = self.random.choice(possible_position)
        self.model.grid.move_agent (self, new_postion)
#-------------------------------------------------------------        
    def InfectionTransmission(self):
        if self.state > 2:
            cell_mates = self.model.grid.get_cell_list_contents([self.pos])
#            infected_agents = []
            for agent in cell_mates:
                if agent.state == 1 and not agent.immunity and self.Random_Decider(self.model.transmission_chance):
                    agent.state = 2
                    agent.infection_time.append(self.model.schedule.time)
#                    infected_agents.append(agent.unique_id)
                elif agent.state == 1 and agent.immunity and self.Random_Decider(self.model.transmission_chance):
                    if self.Random_Decider(self.model.reinfection_chance):
                        agent.state = 2
                        agent.infection_time.append(self.model.schedule.time)
#                        infected_agents.append(agent.unique_id)

                    
# =============================================================================
#             if len(infected_agents) > 0:
#                 self.model.infection_log[0].append(self.pos)
#                 self.model.infection_log[1].append(self.unique_id)
#                 self.model.infection_log[2].append(infected_agents)
# =============================================================================
#------------------------------------------------------------
    def TaskDecider(self):
        random_decider = self.model.random.uniform(0, 1)
        if random_decider <= self.model.task_randomizer[0]:
            self.task = 2
        elif self.model.task_randomizer[0] < random_decider <= (self.model.task_randomizer[0] + self.model.task_randomizer[1]):
            self.task = 1
        else:
            self.task = 3
#-------------------------------------------------------------    
    def WarehouseTravel(self):
        distance = np.subtract(self.model.warehouse_pos, self.pos)
        
        if distance [0] == 0 and distance [1] == 0:
            self.task = 2
            self.model.grid.move_agent(self, self.work_location)
        else:
            if distance [0] != 0:
                new_postion = (int(self.pos[0] + distance[0]/abs(distance[0])), int(self.pos[1]))
            else:
                new_postion = (int(self.pos[0]), int(self.pos[1] + distance[1]/abs(distance[1])))

            self.model.grid.move_agent (self, new_postion)
#-------------------------------------------------------------
    def HealthCheck(self, infection_duration):

        if infection_duration <= 4 * 60 * self.model.workhours:
            self.state = 2
            
        elif 4 * 60 * self.model.workhours < infection_duration <= 6 * 60 * self.model.workhours:
            self.state = 3
            
        elif 6 * 60 * self.model.workhours < infection_duration <= 14 * 60 * self.model.workhours:
            self.state = 4

        else:
            if self.Random_Decider(self.model.mortality_rate): self.Agent_Death()
            else:
                self.state = 1
                self.immunity = True

            
#-------------------------------------------------------------

    def Agent_Death(self):
        self.model.mortality.append([self.unique_id, self.model.schedule.time])
        self.model.schedule.remove(self)

#-------------------------------------------------------------
        
    def Random_Decider(self, rand):
        
        random_decider = self.model.random.uniform(0, 1)
        
        return True if random_decider <= rand else False
