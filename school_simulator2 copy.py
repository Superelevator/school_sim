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
    def __init__(self, name, location=(0,0), dimensions=(0,0), connections=None, subject=None, floors=1, rooms=None, corridors=None, corridor_connections=None):
        self.name = name
        self.location = location
        self.dimensions = dimensions
        self.connections = connections if connections is not None else []
        self.subject = subject
        self.floors = floors
        self.rooms = rooms if rooms is not None else [[] for _ in range(floors)]
        if corridors is None:
            # Create separate list objects for each floor
            self.corridors = [{"x": [], "y": []} for _ in range(floors)]
        else:
            self.corridors = corridors
        self.corridor_connections = corridor_connections if corridor_connections is not None else []
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
                self.connections.append(buildings[i])
    def assign_building(self, buildings_sorted_subject, subject, buildings):
        index = randint(0, len(buildings_sorted_subject[subject]) - 1)
        names = [building.name for building in buildings]
        while buildings_sorted_subject[subject][index]['name'] in names:
            index = randint(0, len(buildings_sorted_subject[subject]) - 1)
        self.name = buildings_sorted_subject[subject][index]['name']
        self.subject = subject
        self.floors = randint(1, 3)
        # Reinitialize to match new floor count
        self.rooms = [[] for _ in range(self.floors)]
        self.corridors = [{"x": [], "y": []} for _ in range(self.floors)]
        return self
    def generate_corridors(self, floor=0):
        while len(self.corridors) <= floor:
            self.corridors.append({"x": [], "y": []})

        # Copy from floor 0 if this is an upper floor
        if floor > 0 and len(self.corridors) > 0:
            self.corridors[floor]["x"] = self.corridors[0]["x"].copy()
            self.corridors[floor]["y"] = self.corridors[0]["y"].copy()
            return self  # Skip rest of generation
        if self.subject in ["Cafeteria", "Library", "PE", "Theater"]:
            return self
        self.corridors[floor]["x"] = []
        self.corridors[floor]["y"] = []


        # Define border direction
        def border_direction(building1, building2):
            if building1.location[0] + building1.dimensions[0] == building2.location[0] or building1.location[0] == building2.location[0] + building2.dimensions[0]:
                # Left or right border
                return "leftright"
            elif building1.location[1] + building1.dimensions[1] == building2.location[1] or building1.location[1] == building2.location[1] + building2.dimensions[1]:
                # Top or bottom border
                return "topbottom"
            else:
                # No border
                return None
        
        def surroundings_clear(corridor, direction, floor):
            if direction == "topbottom":  # X corridors
                corridor_list = self.corridors[floor]["x"]
            elif direction == "leftright":  # Y corridors
                corridor_list = self.corridors[floor]["y"]
            
            if corridor in corridor_list:
                return False
            if corridor + 1 in corridor_list:
                return False
            if corridor - 1 in corridor_list:
                return False
            return True
        
        def in_bounds(corridor, direction):
            if direction == "vertical":
                return corridor >= 0 and corridor <= self.dimensions[0] - 1
            elif direction == "horizontal":
                return corridor >= 0 and corridor <= self.dimensions[1] - 1
            else:
                return True
        
        for building in self.connections:
            if len(building.corridors) - 1 < floor:
                continue
            direction = border_direction(self, building)
            if direction == "topbottom":
                for corridor in building.corridors[floor]["x"]:
                    offset = self.location[0] - building.location[0]
                    proposition = corridor - offset
                    if proposition > 0 and proposition < self.dimensions[0] - 1 and surroundings_clear(proposition, "topbottom", floor):
                        self.corridors[floor]["x"].append(proposition)
                        if building not in self.corridor_connections:
                            self.corridor_connections.append(building)
            elif direction == "leftright":
                for corridor in building.corridors[floor]["y"]:
                    offset = self.location[1] - building.location[1]
                    proposition = corridor - offset
                    if proposition > 0 and proposition < self.dimensions[1] - 1 and surroundings_clear(proposition, "leftright", floor):
                        self.corridors[floor]["y"].append(proposition)
                        if building not in self.corridor_connections:
                            self.corridor_connections.append(building)
        self.corridors[floor]["x"].sort()
        self.corridors[floor]["y"].sort()
        if (not self.corridors[floor]["x"]) or (not self.corridors[floor]["y"]):
            if not self.corridors[floor]["x"]:
                possible_corridors = []
                for i in range(1, self.dimensions[0] - 1):
                    if surroundings_clear(i, "leftright", floor):
                        possible_corridors.append(i)
                if possible_corridors:
                    proposition = choice(possible_corridors)
                    self.corridors[floor]["x"].append(proposition)
                else:
                    return self
            if not self.corridors[floor]["y"]:
                possible_corridors = []
                for i in range(1, self.dimensions[1] - 1):
                    if surroundings_clear(i, "topbottom", floor):
                        possible_corridors.append(i)
                if possible_corridors:
                    proposition = choice(possible_corridors)
                    self.corridors[floor]["y"].append(proposition)
                else:
                    return self
    def generate_rooms(self, floor):
        def classify_by_area(area, rooms):
            types = []
            for room in rooms:
                types.append(room.identity)
            if "Bathroom" not in types and area >= 3:
                return "Bathroom"
            if "Office" not in types and area >= 4:
                return "Office"
            if "Classroom" not in types and area >= 8:
                return "Classroom"
            # Start classification for room types by area.
            # Guarantee a few necessary room types by size thresholds.
            bathrooms = 0
            for room in rooms:
                if room.identity == "Bathroom":
                    bathrooms += 1
            if area >= 8:
                return "Classroom"
            elif area >= 4:
                return "Office"
            elif area >= 3 and bathrooms < 1:
                return "Bathroom"
            else:
                return "Storage"
        while len(self.rooms) <= floor:
            self.rooms.append([])
        if self.subject in ["Cafeteria", "Library", "PE", "Theater"]:
            self.rooms[floor].append(Room(name=f"{self.name[0:3].upper()}-{self.subject.upper()}-{floor}", location=(0, 0), dimensions=(self.dimensions[0], self.dimensions[1]), parent_building=self, subject=self.subject, identity=self.subject))
            return self
        corridors = self.corridors[floor]
        zones = []
        # Create boundaries that split zones AROUND corridors, not through them
        boundaries_x = [0, self.dimensions[0]]
        for x in corridors["x"]:
            boundaries_x.append(x)      # Before corridor
            boundaries_x.append(x + 1)  # After corridor
        xs = sorted(set(boundaries_x))  # Remove duplicates and sort

        boundaries_y = [0, self.dimensions[1]]
        for y in corridors["y"]:
            boundaries_y.append(y)      # Before corridor
            boundaries_y.append(y + 1)  # After corridor
        ys = sorted(set(boundaries_y))  # Remove duplicates and sort
        for i in range(len(xs)-1):
            for j in range(len(ys)-1):
                zone_x = xs[i]
                zone_y = ys[j]
                zone_w = xs[i+1] - xs[i]
                zone_h = ys[j+1] - ys[j]
                
                # Skip zones that are exactly on corridor positions
                if zone_w == 1 and zone_x in corridors["x"]:
                    continue
                if zone_h == 1 and zone_y in corridors["y"]:
                    continue
                
                zones.append({"location": (zone_x, zone_y), "dimensions": (zone_w, zone_h)})
        
        for zone in zones:
            if min(zone["dimensions"][0], zone["dimensions"][1]) == zone["dimensions"][0]:
                direction = "horizontal"
            else:
                direction = "vertical"
            if direction == "horizontal":
                divisions = zone["dimensions"][1] // 3
                if divisions == 0:
                    divisions = 1
                total_difference = 0
                heights = []
                while divisions > 0:
                    if zone["dimensions"][1] - total_difference < 2:
                        remaining = zone["dimensions"][1] - total_difference
                        if len(heights) == 0:
                            heights.append(max(1, remaining))  # At least 1
                        elif remaining > 0:
                            heights[-1] += remaining  # Add exact remaining amount
                        break
                    else:
                        if divisions == 1:
                            new_height = zone["dimensions"][1] - total_difference
                        else:
                            new_height = min(4+randint(-1, 1), zone["dimensions"][1] - total_difference)
                        heights.append(new_height)
                    total_difference += heights[-1]
                    divisions -= 1
                total_height = 0
                for height in heights:
                    self.rooms[floor].append(Room(name=f"{self.name[0:3].upper()}-{floor}{len(self.rooms[floor])}", location=(zone["location"][0], zone["location"][1] + total_height), dimensions=(zone["dimensions"][0], height), parent_building=self, subject=self.subject))
                    total_height += height
            elif direction == "vertical":  
                divisions = zone["dimensions"][0] // 3
                if divisions == 0:
                    divisions = 1
                total_difference = 0
                widths = []
                while divisions > 0:
                    if zone["dimensions"][0] - total_difference < 2:
                        remaining = zone["dimensions"][0] - total_difference
                        if len(widths) == 0:
                            widths.append(max(1, remaining))  # At least 1
                        elif remaining > 0:
                            widths[-1] += remaining  # Add exact remaining amount
                        break
                    else:
                        if divisions == 1:
                            new_width = zone["dimensions"][0] - total_difference
                        else:
                            new_width = min(4+randint(-1, 1), zone["dimensions"][0] - total_difference)
                        widths.append(new_width)
                    total_difference += widths[-1]
                    divisions -= 1
                total_width = 0
                for width in widths:
                    self.rooms[floor].append(Room(name=f"{self.name[0:3].upper()}-{floor}{len(self.rooms[floor])}", location=(zone["location"][0] + total_width, zone["location"][1]), dimensions=(width, zone["dimensions"][1]), parent_building=self, subject=self.subject))
                    total_width += width
                # Iterate through rooms in area order without modifying list
        for room in sorted(self.rooms[floor], key=lambda r: r.dimensions[0] * r.dimensions[1], reverse=False):
            area = room.dimensions[0] * room.dimensions[1]
            room.identity = classify_by_area(area, self.rooms[floor])
        return self
    def render(self, screen, floor):
        tile_size = 10
        building_x = self.location[0] * tile_size
        building_y = self.location[1] * tile_size
        building_width = self.dimensions[0] * tile_size
        building_height = self.dimensions[1] * tile_size
        
        # Draw building outline
        pygame.draw.rect(screen, (150, 75, 25), (building_x, building_y, building_width, building_height))
        # Draw corridors (if they exist)
        if self.corridors and len(self.corridors) > floor:  # Draw floor 0 corridors
            corridor_color = (200, 200, 200)  # Light gray for corridors            
            # Draw X corridors (vertical corridors - run horizontally through the building)
            for corridor_x in self.corridors[floor]["x"]:
                corridor_pixel_x = building_x + corridor_x * tile_size
                pygame.draw.rect(screen, corridor_color, 
                               (corridor_pixel_x, building_y, tile_size, building_height))
            
            # Draw Y corridors (horizontal corridors - run vertically through the building)
            for corridor_y in self.corridors[floor]["y"]:
                corridor_pixel_y = building_y + corridor_y * tile_size
                pygame.draw.rect(screen, corridor_color, 
                               (building_x, corridor_pixel_y, building_width, tile_size))
        # Draw rooms relative to building
        if self.rooms and len(self.rooms) > floor:
            for room in self.rooms[floor]:
                room_x = room.location[0] * tile_size + building_x
                room_y = room.location[1] * tile_size + building_y 
                room_width = room.dimensions[0] * tile_size
                room_height = room.dimensions[1] * tile_size
                if room.identity == "Classroom":
                    pygame.draw.rect(screen, (0, 0, 255), (room_x, room_y, room_width, room_height))
                elif room.identity == "Office":
                    pygame.draw.rect(screen, (0, 255, 0), (room_x, room_y, room_width, room_height))
                elif room.identity == "Bathroom":
                    pygame.draw.rect(screen, (0, 255, 255), (room_x, room_y, room_width, room_height))
                elif room.identity == "Storage":
                    pygame.draw.rect(screen, (255, 0, 0), (room_x, room_y, room_width, room_height))
                elif room.identity == "Cafeteria":
                    pygame.draw.rect(screen, (50, 200, 50), (room_x, room_y, room_width, room_height))
                elif room.identity == "Library":
                    pygame.draw.rect(screen, (150, 125, 50), (room_x, room_y, room_width, room_height))
                elif room.identity == "PE":
                    pygame.draw.rect(screen, (150, 150, 150), (room_x, room_y, room_width, room_height))
                elif room.identity == "Theater":
                    pygame.draw.rect(screen, (255, 50, 255), (room_x, room_y, room_width, room_height))
                # Draw outline around room (width=1 for thin, 2 for thicker)
                pygame.draw.rect(screen, (50, 50, 50), (room_x, room_y, room_width, room_height), 1)

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
class Room():
    def __init__(self, name, location, dimensions, parent_building, subject, identity=None):
        self.name = name
        self.location = location
        self.dimensions = dimensions
        self.parent_building = parent_building
        self.identity = identity
    
    

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
        for floor in range(building.floors):
            building.generate_corridors(floor)
    for building in buildings:
        for floor in range(building.floors):
            building.generate_corridors(floor)
    return buildings

def make_rooms(buildings):
    for building in buildings:
        for floor in range(building.floors):
            building.generate_rooms(floor)
    return buildings


# Draw the board
def draw_board(screen, structures, floor):
    screen.fill((70, 70, 70))
    buildings = structures[0]
    green_spaces = structures[1]
    scale = 1

    # Building set-up
    for building in buildings:
        building.render(screen, floor)
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
    make_rooms(buildings)

    return structures
structures = initialize_game()
running = True

floor = 0

while running:
    # prepare frame
    draw_board(screen, structures, floor) 
    for event in pygame.event.get():
        # quit
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                floor += 1
                if floor >= 2:
                    floor = 2
            if event.key == pygame.K_DOWN:
                floor -= 1
                if floor < 0:
                    floor = 0
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                structures = initialize_game()
        # check click
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
        
     
    pygame.display.flip()
    clock.tick(60)  

pygame.quit()   