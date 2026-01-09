import pygame, sys
from math import *
from random import *

from PIL import Image
from noise import pnoise2
import json

class Button():
    def __init__(self, label, label_size, color, id, location, dimensions):
        self.label = label
        self.label_size = label_size
        self.color = color
        self.id = id
        self.location = location
        self.dimensions = dimensions
    def render(self, screen):
        pygame.draw.rect(screen, self.color, (self.location[0], 
                                    self.location[1], self.dimensions[0], self.dimensions[1]))
        font = pygame.font.Font(None, self.label_size)
        text = font.render(self.label, True, (0, 0, 0))
        text_rect = text.get_rect(center=(self.location[0] + self.dimensions[0] / 2,
                                          self.location[1] + self.dimensions[1] / 2))
        screen.blit(text, text_rect)
    def check_click(self, mouse_pos):
        scaled_pos = (mouse_pos[0] * 2, mouse_pos[1] * 2)
        if (self.location[0] < scaled_pos[0] < self.location[0] + 
            self.dimensions[0] and
            self.location[1] < scaled_pos[1] < self.location[1] +
            self.dimensions[1]):
            return self.id
        else:
            return None
    

class Text():
    def __init__(self, text, color, location, size):
        self.text = text
        self.color = color
        self.location = location
        self.size = size
    def render(self, screen):
        font = pygame.font.Font(None, self.size)
        text = font.render(self.text, True, self.color)
        screen.blit(text, self.location)


class Block():
    def __init__(self, structure, location, dimensions, color, displayed):
        self.structure = structure
        self.location = location
        self.dimensions = dimensions
        self.color = color
        self.displayed = displayed
    def render(self, screen):
        pygame.draw.rect(screen, self.color, (self.location[0], self.location[1],
                                              self.dimensions[0], self.dimensions[1]))
        for line in self.structure:
            for element in line:
                element.render(screen)
                
class Building():
    def __init__(self, name, location=(0,0), dimensions=(0,0), connections=[], subject=None, floors=0, rooms=[], corridors=[{"x": [], "y": []}]):
        self.name = name
        self.location = location
        self.dimensions = dimensions
        self.connections = connections
        self.subject = subject
        self.floors = floors
        self.rooms = rooms
        self.corridors = corridors
    def occupied(self, buildings):
        occupied = set()
        # Skip if building hasn't been placed yet (dimensions are 0)
        if self.dimensions[0] == 0 or self.dimensions[1] == 0:
            return occupied
        # self.location[0] is col (x), self.location[1] is row (y)
        grid_col = self.location[0]
        grid_row = self.location[1]
        grid_width = self.dimensions[0]
        grid_height = self.dimensions[1]
        for c in range(grid_col, grid_col + grid_width):
            for r in range(grid_row, grid_row + grid_height):
            
                occupied.add((c, r))  # (col, row) format
        return occupied
    def reserved(self, buildings):
        reserved = set()
        # Skip if building hasn't been placed yet (dimensions are 0)
        if self.dimensions[0] == 0 or self.dimensions[1] == 0:
            return reserved
        # self.location[0] is col (x), self.location[1] is row (y)
        grid_col = self.location[0]
        grid_row = self.location[1]
        grid_width = self.dimensions[0]
        grid_height = self.dimensions[1]
        bound_r = grid_row - 1
        bound_c = grid_col - 1
        bound_r_end = grid_row + grid_height + 1
        bound_c_end = grid_col + grid_width + 1
        for c in range(bound_c, bound_c_end):
            for r in range(bound_r, bound_r_end):
                reserved.add((c, r))  # (col, row) format
        return reserved
    def generate_building(self, board_map, buildings, overpopulated, retries=10):
        if retries <= 0:
            return self
        if overpopulated == [True, True, True, True, True]:
            return self
        zone = randint(0, 4)
        while overpopulated[zone]:
            zone = randint(0, 4)
        focus = zone
        # Establish intervals
        intervals = [0.3, 0.1, 0.075, 0.10, 0.4]
        fourth_bound = intervals[0]
        third_bound = fourth_bound + intervals[1]
        second_bound = third_bound + intervals[2]
        first_bound  = second_bound + intervals[3]
        spawn_bound  = first_bound + intervals[4]

        # Establish occupied and reserved sets
        occupied = set()
        reserved = set()
        for building in buildings:
            occupied.update(building.occupied(buildings))
            reserved.update(building.reserved(buildings))
        # Find spawn point
        cols = len(board_map)
        rows = len(board_map[0])
        spawn_col = None
        spawn_row = None
        # Using focus, find suitable spawn zone
        all_available = []
        start_row = focus * rows // 5
        end_row = min(focus + 1, 4) * rows // 5
        # Check each column-row combination in zone
        for col in range(cols):
            for row in range(start_row, end_row + 1):
                # Check if the tile is within the spawn bounds
                if first_bound < board_map[col][row] < spawn_bound:
                    # Check if the tile is not occupied or reserved (using col, row format)
                    if (col, row) not in occupied and (col, row) not in reserved:
                        all_available.append((col, row))  # (col, row) format
        if not all_available:
            overpopulated[zone] = True
            return self.generate_building(board_map, buildings, overpopulated, retries)
        spawn_col, spawn_row = choice(all_available)  # (col, row) format
        # Set spawn point and begin growth
        self.location = (spawn_col, spawn_row)  # (col, row) format
        reach_x_negative = reach_x_positive = reach_y_negative = reach_y_positive = 0

        # Define validation functions
        def in_bounds(col, row):
            return 0 <= row < rows and 0 <= col < cols
        def new_strip(direction, reach_x_negative, reach_x_positive, reach_y_negative, reach_y_positive):
            # self.location[0] is col (x), self.location[1] is row (y)
            # reach_x is for columns, reach_y is for rows
            c0 = self.location[0] - reach_x_negative
            c1 = self.location[0] + reach_x_positive
            r0 = self.location[1] - reach_y_negative
            r1 = self.location[1] + reach_y_positive
            
            if direction == 1:  # +x (right, expand columns)
                new_col = c1 + 1
                return [(new_col, r) for r in range(r0, r1 + 1)]  # (col, row) format
            elif direction == 2:  # -x (left, expand columns)
                new_col = c0 - 1
                return [(new_col, r) for r in range(r0, r1 + 1)]  # (col, row) format
            elif direction == 3:  # +y (down, expand rows)
                new_row = r1 + 1
                return [(c, new_row) for c in range(c0, c1 + 1)]  # (col, row) format
            elif direction == 4:  # -y (up, expand rows)
                new_row = r0 - 1
                return [(c, new_row) for c in range(c0, c1 + 1)]  # (col, row) format
            return []
        def strip_clear(strip):
            for col, row in strip:  # (col, row) format
                if not in_bounds(col, row) or (col, row) in occupied:
                    return False
            return True
        def in_focus(col, row):
            return row >= focus * rows // 5 and row < (focus + 1) * rows // 5
        def non_oblong(reach_x_negative, reach_x_positive, reach_y_negative, reach_y_positive):
            if max(reach_x_negative + reach_x_positive + 1, reach_y_negative + reach_y_positive + 1) > 2.5*min(reach_x_negative + reach_x_positive + 1, reach_y_negative + reach_y_positive + 1):
                return False
            return True

        # Begin growing
        viable_directions = [1, 2, 3, 4]
        while viable_directions and (reach_x_negative + reach_x_positive + 1) * (reach_y_negative + reach_y_positive + 1) < 100:
            # Choose and validate direction
            direction = choice(viable_directions)
            strip = new_strip(direction, reach_x_negative, reach_x_positive, reach_y_negative, reach_y_positive)
            if not strip:
                viable_directions.remove(direction)
                continue
            if not strip_clear(strip):
                viable_directions.remove(direction)
                continue
            
            if direction == 1:
                reach_x_positive += 1
            elif direction == 2:
                reach_x_negative += 1
            elif direction == 3:
                reach_y_positive += 1
            elif direction == 4:
                reach_y_negative += 1
            # add chances up:
            chance = 0
            for col, row in strip:  # (col, row) format
                v = board_map[col][row]  # board_map is indexed [col][row]
                if v <= fourth_bound:
                    chance += 3
                elif v <= third_bound:
                    chance += 2
                elif v <= second_bound:
                    chance += 1
                elif v <= first_bound:
                    chance += 0
                else:
                    chance += 0
                if not in_focus(col, row):
                    chance *= 2
                if chance > 100:
                    chance = 100
                if randint(1, 100) < chance:
                    viable_directions.remove(direction)
                    break
        if not non_oblong(reach_x_negative, reach_x_positive, reach_y_negative, reach_y_positive):
            self.location = (0, 0)
            self.dimensions = (0, 0)
            return self.generate_building(board_map, buildings, overpopulated, retries-1)
        # -------- finalize building + occupy tiles --------
        # self.location[0] is col (x), self.location[1] is row (y)
        # reach_x is for columns, reach_y is for rows
        self.location = ((self.location[0] - reach_x_negative), (self.location[1] - reach_y_negative))  # (col, row) format
        self.dimensions = ((reach_x_positive + reach_x_negative + 1), (reach_y_positive + reach_y_negative + 1))
        return self
    def make_connections(self, buildings):
        connections = []
        def border_exists(building1, building2):
            # Get borders of both buildings
            building1_west = building1.location[0]
            building1_east = building1.location[0] + building1.dimensions[0]
            building1_north = building1.location[1]
            building1_south = building1.location[1] + building1.dimensions[1]
            
            building2_west = building2.location[0]
            building2_east = building2.location[0] + building2.dimensions[0]
            building2_north = building2.location[1]
            building2_south = building2.location[1] + building2.dimensions[1]
            
            if building1_north == building2_south:
                if building1_west <= building2_east and building1_east >= building2_west or building2_west <= building1_east and building2_east >= building1_west:
                    return True
            elif building1_south == building2_north:
                if building1_west <= building2_east and building1_east >= building2_west or building2_west <= building1_east and building2_east >= building1_west:
                    return True
            elif building1_west == building2_east:
                if building1_north <= building2_south and building1_south >= building2_north or building2_north <= building1_south and building2_south >= building1_north:
                    return True
            elif building1_east == building2_west:
                if building1_north <= building2_south and building1_south >= building2_north or building2_north <= building1_south and building2_south >= building1_north:
                    return True
            return False
        # Make connections between THIS building and other buildings
        for i in range(len(buildings)):
            if border_exists(self, buildings[i]) and self != buildings[i]:
                connections.append((buildings[i]))
        return connections
    def assign_building(self, buildings_sorted_subject, subject, buildings):
        index = randint(0, len(buildings_sorted_subject[subject]) - 1)
        names = [building.name for building in buildings]
        while buildings_sorted_subject[subject][index]['name'] in names:
            index = randint(0, len(buildings_sorted_subject[subject]) - 1)
        self.name = buildings_sorted_subject[subject][index]['name']
        self.subjects = subject
    def generate_corridors(self, floor=0):
        relevant = []
        for building in self.connections:
            if building.corridors[floor]["x"] or building.corridors[floor]["y"]:
                relevant.append(building)
        if relevant:
            print("bordering buildings")
            for building in relevant:
                offset = (building.location[0] - self.location[0], building.location[1] - self.location[1])
                for corridor in building.corridors[floor]["x"]:
                    if corridor + offset[0] > 0 and corridor + offset[0] < self.dimensions[0]:
                        self.corridors[floor]["x"].append(corridor + offset[0])
                for corridor in building.corridors[floor]["y"]:
                    if corridor + offset[1] > 0 and corridor + offset[1] < self.dimensions[1]:
                        self.corridors[floor]["y"].append(corridor + offset[1])
            self.corridors[floor]["x"].sort()
            self.corridors[floor]["y"].sort()
        else:
            x_available = [i for i in range(1, self.dimensions[0] - 1)]
            y_available = [i for i in range(1, self.dimensions[1] - 1)]
            x_determinant = randint(1, 3)
            y_determinant = randint(1, 3)
            while x_available and len(self.corridors[floor]["x"]) < x_determinant:
                attempt_x = choice(x_available)
                self.corridors[floor]["x"].append(attempt_x)
                x_available.remove(attempt_x)
                if attempt_x + 1 in x_available:
                    x_available.remove(attempt_x + 1)
                if attempt_x - 1 in x_available:
                    x_available.remove(attempt_x - 1)
            while y_available and len(self.corridors[floor]["y"]) < y_determinant:
                attempt_y = choice(y_available)
                self.corridors[floor]["y"].append(attempt_y)
                y_available.remove(attempt_y)
                if attempt_y + 1 in y_available:
                    y_available.remove(attempt_y + 1)
                if attempt_y - 1 in y_available:
                    y_available.remove(attempt_y - 1)
            self.corridors[floor]["x"].sort()
            self.corridors[floor]["y"].sort()
    def render(self, screen):
        pygame.draw.rect(screen, (150, 75, 25), (self.location[0]*10, self.location[1]*10,
                                              self.dimensions[0]*10, self.dimensions[1]*10))
class GreenSpace():
    def __init__(self, name, location, dimensions):
        self.name = name
        self.location = location
        self.dimensions = dimensions
    def occupied(self):
        occupied = set()
        grid_col = self.location[0]
        grid_row = self.location[1]
        grid_width = self.dimensions[0]
        grid_height = self.dimensions[1]
        for c in range(grid_col, grid_col + grid_width):
            for r in range(grid_row, grid_row + grid_height):   
                occupied.add((c, r))  # (col, row) format
        return occupied
    def generate_green_space(self, board_map, green_spaces, buildings, retries=3):
        if retries <= 0:
            return self  # Give up after max retries
        cols = len(board_map)
        rows = len(board_map[0])
        total_occupied = set()
        for building in buildings:
            if building.dimensions[0] == 0 or building.dimensions[1] == 0:
                continue  # Skip unplaced buildings
            # building.location[0] is col, building.location[1] is row
            # building.dimensions[0] is width (cols), building.dimensions[1] is height (rows)
            for i in range(building.dimensions[0] + 6):  # width + 8 tile buffer
                for j in range(building.dimensions[1] + 6):  # height + 8 tile buffer
                    col = building.location[0] - 3 + i
                    row = building.location[1] - 3 + j
                    if 0 <= col < cols and 0 <= row < rows:  # Bounds check
                        total_occupied.add((col, row))  # (col, row) format
        for green_space in green_spaces:
            if green_space.dimensions[0] > 0 and green_space.dimensions[1] > 0:
                total_occupied.update(green_space.occupied())
        all_available = []
        for c in range(cols):
            for r in range(rows):
                if (c, r) not in total_occupied:  # (col, row) format
                    all_available.append((c, r))  # (col, row) format
        if not all_available:
            return self  # No space available, return with (0,0) dimensions
        self.location = choice(all_available)
        reach_x_negative = reach_x_positive = reach_y_negative = reach_y_positive = 0
        # Define validation functions
        def in_bounds(col, row):
            return 0 <= row < rows and 0 <= col < cols
        def new_strip(direction, reach_x_negative, reach_x_positive, reach_y_negative, reach_y_positive):
            # self.location[0] is col (x), self.location[1] is row (y)
            # reach_x is for columns, reach_y is for rows
            c0 = self.location[0] - reach_x_negative
            c1 = self.location[0] + reach_x_positive
            r0 = self.location[1] - reach_y_negative
            r1 = self.location[1] + reach_y_positive
            
            if direction == 1:  # +x (right, expand columns)
                new_col = c1 + 1
                return [(new_col, r) for r in range(r0, r1 + 1)]  # (col, row) format
            elif direction == 2:  # -x (left, expand columns)
                new_col = c0 - 1
                return [(new_col, r) for r in range(r0, r1 + 1)]  # (col, row) format
            elif direction == 3:  # +y (down, expand rows)
                new_row = r1 + 1
                return [(c, new_row) for c in range(c0, c1 + 1)]  # (col, row) format
            elif direction == 4:  # -y (up, expand rows)
                new_row = r0 - 1
                return [(c, new_row) for c in range(c0, c1 + 1)]  # (col, row) format
            return []
        def strip_clear(strip):
            for col, row in strip:  # (col, row) format
                if not in_bounds(col, row) or (col, row) in total_occupied:
                    return False
            return True
        # Begin growing
        viable_directions = [1, 2, 3, 4]
        max_growth_steps = 100  # Prevent infinite loop
        growth_steps = 0
        while viable_directions and growth_steps < max_growth_steps:
            growth_steps += 1
            # Choose and validate direction
            direction = choice(viable_directions)
            strip = new_strip(direction, reach_x_negative, reach_x_positive, reach_y_negative, reach_y_positive)
            if not strip:
                viable_directions.remove(direction)
                continue
            if not strip_clear(strip):
                viable_directions.remove(direction)
                continue
            
            if direction == 1:
                reach_x_positive += 1
            elif direction == 2:
                reach_x_negative += 1
            elif direction == 3:
                reach_y_positive += 1
            elif direction == 4:
                reach_y_negative += 1
        # self.location[0] is col, self.location[1] is row
        self.location = ((self.location[0] - reach_x_negative), (self.location[1] - reach_y_negative))  # (col, row) format
        self.dimensions = ((reach_x_positive + reach_x_negative + 1), (reach_y_positive + reach_y_negative + 1))
        return self
    def render(self, screen):
        pygame.draw.rect(screen, (75, 150, 75), (self.location[0]*10, self.location[1]*10,
                                              self.dimensions[0]*10, self.dimensions[1]*10))

def gen_board(grid_size, scale):
    cols, rows = grid_size
    seed = randint(0, 100)
    board_map = [[float(pnoise2(c/scale, r/scale, octaves=2, persistence=0.25,
                              lacunarity=1.5, base=seed)+1)/2 
            for r in range(rows)] for c in range(cols)]
    return board_map
         

def place_buildings(board_map):
    buildings = []
    for i in range(20):
        buildings.append(Building(name=f"Building {i}"))
    assign_buildings(buildings)
    # Find focus zone
    def get_zones(buildings, board_map):
        overpopulated = [False, False, False, False, False]
        focus = 0
        # Calculate zone heights and tile distribution for 5 equal-height bands
        rows = len(board_map)
        zone_height = rows // 5
        zone_tile_counts = [0, 0, 0, 0, 0]
        zone_building_counts = [0, 0, 0, 0, 0]
        for building in buildings:
            # Skip if building hasn't been placed yet (dimensions are 0)
            if building.dimensions[0] == 0 or building.dimensions[1] == 0:
                continue
            start_row = building.location[1]
            end_row = building.location[1] + building.dimensions[1] - 1
            for r in range(start_row, end_row + 1):
                # which zone does this row belong to?
                for r in range(start_row, end_row + 1):
                    if r >= rows:  # Safety check
                        break
                    # Calculate zone explicitly to handle uneven division
                    zone = min(r // zone_height, 4)
                    # But ensure we don't go beyond rows
                    if zone >= 5:
                        zone = 4
                    zone_tile_counts[zone] += 1
            zone = min(((building.location[1] + (building.dimensions[1] // 2)) // zone_height), 4)
            zone_building_counts[zone] += 1
        # Now, zone_tile_counts holds the total number of tiles in each horizontal zone (0 to 4)
        overpopulated = [False, False, False, False, False]
        for i in range(len(overpopulated)):
            if zone_tile_counts[i] >= 300:
                overpopulated[i] = True
            if zone_building_counts[i] >= 4:
                overpopulated[i] = True
        return overpopulated
         # no remaining spots
    to_remove = []
    for building in buildings:
        building.generate_building(board_map, buildings, get_zones(buildings, board_map))
        if building.dimensions[0] == 0 or building.dimensions[1] == 0:
            to_remove.append(building)
    for building in to_remove:
        buildings.remove(building) # remove building from list
    return buildings

def place_green_spaces(board_map, buildings):
    green_spaces = []
    for i in range(randint(10, 15)):
        green_spaces.append(GreenSpace(name=f"Green Space {i}", location=(0, 0), dimensions=(0, 0)))
    for green_space in green_spaces:
        green_space.generate_green_space(board_map, green_spaces, buildings)
    return green_spaces

def connect_buildings(buildings):
    for building in buildings:
        building.make_connections(buildings)
    return buildings

def assign_buildings(buildings):
    all_subjects = ["Math", "Science", "History", "English", "Language", "PE", "Art", "Music", 
    "Theater", "Computer Science", "Cafeteria", "Library"]
    with open('building_definitions.json', 'r') as f:
        building_definitions = json.load(f)
    buildings_sorted_subject = building_definitions['subjects']
    for i, building in enumerate(buildings):
        if i < 12:
            subject = all_subjects[i]
        else:
            subject = all_subjects[randint(0, len(all_subjects) - 1)]
        building.assign_building(buildings_sorted_subject, subject, buildings)
    return buildings

def make_building_corridors(buildings):
    for building in buildings:
        building.generate_corridors()
    return buildings
# Draw the board
def draw_board(screen, structures):
    screen.fill((70, 70, 70))
    buildings = structures[0]
    green_spaces = structures[1]
    scale = 1

    # Building set-up
    for building in buildings:
        building.render(screen)
    for green_space in green_spaces:
        green_space.render(screen)
        
    

    

pygame.font.init()
        
screen = pygame.display.set_mode((750, 750))
pygame.display.set_caption("Campus")
clock = pygame.time.Clock()

def initialize_game():
    global buildings, green_spaces, structures, heat_map
    # Place all structures
    heat_map = gen_board((75, 75), 6)
    buildings = place_buildings(heat_map)
    green_spaces = place_green_spaces(heat_map, buildings)
    structures = [buildings, green_spaces]

    # Further information about buildings
    connect_buildings(buildings)
    assign_buildings(buildings)
    make_building_corridors(buildings)

    return structures
structures = initialize_game()
running = True

while running:
    # prepare frame
    
    draw_board(screen, structures) 
    for event in pygame.event.get():
        # quit
        if event.type == pygame.QUIT:
            running = False
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                structures = initialize_game()
        # check click
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
     
    pygame.display.flip()
    clock.tick(60)  

pygame.quit()  
