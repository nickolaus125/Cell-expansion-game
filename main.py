import pygame
import sys
import math
import numpy as np
import json
import socket
import xml.etree.ElementTree as ET
from xml.dom.minidom import parseString
import configparser
import cv2
from tinydb import TinyDB, Query
import mediapipe as mp
import threading
import ast

from klasy import Cell, Connection, Menu, Editor, Bullet, Inter, Klient

conWidth = 10
WIDTH = 800
HEIGHT = 600

#modifiers for AI

UNDER_ATTACK = 0.5
ALLY = 1.9
IS_HEALING = 1.1

class State(enumerate):
    MENU = 0
    IN_GAME = 1
    EDITOR = 2

class Game:
    def __init__(self, width, height):
        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("My Game")

        self.config = configparser.ConfigParser()
        self.config.read('resources.rc')
        self.gameMode = 0 # 0 - single, 1 - local, 2 - multi

        self.currentLevel = 1

        self.clock = pygame.time.Clock()
        self.running = True
        self.state = State.MENU
        self.mMenu = Menu()
        self.editor = Editor(self.config)

        self.levels = []
        self.numberOfLevels = 0
        for _ in self.config['Levels']:
            self.levels.append(self.config['Levels'][_])
            self.numberOfLevels += 1

        # self.mp_hands = mp.solutions.hands
        # self.hands = self.mp_hands.Hands(min_detection_confidence=0.8, min_tracking_confidence=0.8)
        # self.cap = cv2.VideoCapture(0)

        self.tick = 0
        
        self.cells = []
        self.connections = []

        self.AIPoints = []

        self.isActive = False
        self.activeCell = 0

        self.loadLevel(self.levels[self.currentLevel - 1], self.config)

    def update(self):

        self.tick+=1
        if self.tick >= 60: self.tick = 0

        if (self.state == State.IN_GAME):

            if self.gameMode==1:
                if self.tick == 0 and self.inter.synchronized == 0:
                        self.synchroData(self.tick)
                if self.inter.untakenData:
                    data = self.inter.data
                    data = ast.literal_eval(data)
                    # print(data)
                    # print(type(data))
                    self.inter.dataTaken()
                    self.cellClicked(self.anyCellClicked(data))
                    self.checkConsClicked(data)
                    
                pass

            elif self.gameMode == 2:
                if self.tick == 0:
                    if self.klient.synchronized == 0:
                        self.loadSynchro(self.klient.data, self.config)
                        self.klient.synchronize()
                        self.klient.send("Cos")
                        self.klient.dataTaken()
                    elif self.klient.untakenData:
                        data = self.klient.data
                        data = ast.literal_eval(data)
                        self.klient.dataTaken()
                        self.cellClicked(self.anyCellClicked(data))
                        self.checkConsClicked(data)
            # else: 
            #     self.calcPoints()

            if self.checkLoseWin() == 1:
                if self.currentLevel < self.numberOfLevels:
                    self.currentLevel +=1 
                    self.loadLevel(self.levels[self.currentLevel - 1], self.config)
                else:
                    self.currentLevel = 1
                    self.state = State.MENU

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = State.MENU
                    elif event.key == pygame.K_s:
                        self.save()
                    elif event.key == pygame.K_x:
                        self.saveXML()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.cellClicked(self.anyCellClicked(event.pos))
                    self.checkConsClicked(event.pos)
                    if self.gameMode == 2 :
                        self.klient.send(str(event.pos))
                    elif self.gameMode == 1 and self.inter.synchronized:
                        self.inter.send((str(event.pos)))

            # self.aiUpdate()
            self.updateConns()
            self.updateBullets()

            if self.tick % 30 == 0:
                self.calcPoints()
                for _ in self.cells:
                    _.regenerate()
                self.newBullets()
        
        elif (self.state == State.MENU):

            if self.mMenu.showModeSelect == False:
                # gesture = self.cameraFunctions()
                # if gesture == 1:
                #     self.state = State.IN_GAME
                # elif gesture == 2:
                #     self.running = False
                # elif gesture == 3:
                #     self.state = State.EDITOR

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if self.mMenu.clicked(event.pos) == 1:
                            self.mMenu.showModeSelect = True
                        elif self.mMenu.clicked(event.pos) == 2:
                            self.running = False
                        elif self.mMenu.clicked(event.pos) == 3:
                            self.state = State.EDITOR
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.mMenu.showModeSelect = False
                        elif event.key == pygame.K_l:
                            self.loadSave("save.json", self.config)
                            self.state = State.IN_GAME
                        elif event.key == pygame.K_x:
                            self.loadSaveXML("save.xml", self.config)
                            self.state = State.IN_GAME

            else:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            self.mMenu.showModeSelect = False
                        elif event.key == pygame.K_BACKSPACE:
                            self.mMenu.minusIpString()
                        elif event.key == pygame.K_v:
                            self.mMenu.validateMask()
                        else:
                            self.mMenu.addToText(event.unicode)
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        if self.mMenu.clicked(event.pos):
                            if self.mMenu.clicked(event.pos) == 1:
                                self.gameMode = 0
                            elif self.mMenu.clicked(event.pos) == 2:
                                self.inter = Inter()
                                print("Inter initialized")
                                threading.Thread(target = self.inter.serverLoop).start()
                                self.gameMode = 1
                            elif self.mMenu.clicked(event.pos) == 3:
                                self.gameMode = 2
                                addr, port = self.getAddressMask(self.mMenu.ipText)
                                self.klient = Klient(addr, port)
                                # threading.Thread(target = self.klient.loop).start()
                                # self.loadSynchro(self.klient.data, self.config)
                            self.loadLevel(self.levels[self.currentLevel - 1], self.config)
                            self.state = State.IN_GAME
                            self.calcPoints()

        elif (self.state == State.EDITOR):

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.editor.clicked(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = State.MENU
                    else:
                        self.editor.keyPressed(event.key)
                
    def cameraFunctions(self):
        ret, frame = self.cap.read()

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(frame_rgb)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Punkty orientacyjne dla kciuka i palców
                thumb_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
                thumb_ip = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_IP]
                index_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
                middle_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
                ring_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.RING_FINGER_TIP]
                pinky_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.PINKY_TIP]

                        # Gest "kciuk w górę"
                if thumb_tip.y < index_tip.y and thumb_tip.y < thumb_ip.y:
                    return 1  # Kciuk w górę
                # Gest "zaciśniętej pięści" (wszystkie palce blisko siebie)
                elif all(landmark.y > hand_landmarks.landmark[self.mp_hands.HandLandmark.WRIST].y
                         for landmark in [index_tip, middle_tip, ring_tip, pinky_tip]):
                    return 2  # Zaciśnięta pięść
                # Gest "otwartej dłoni" (wszystkie palce wyprostowane)
                elif (
                    thumb_tip.x < pinky_tip.x and  # Kciuk po lewej (dla prawej dłoni)
                    all(landmark.y < hand_landmarks.landmark[self.mp_hands.HandLandmark.WRIST].y
                        for landmark in [index_tip, middle_tip, ring_tip, pinky_tip])  # Palce wyprostowane
                ):
                    return 3  # Otwarta dłoń
                else:
                    return 0  # Brak rozpoznanego gestu

    def display(self):
        self.screen.fill((0, 0, 0))  

        color1 = (0, 255, 0)

        if (self.state == State.IN_GAME):

            for _ in self.cells:
                _.display(self.screen)
            self.drawConnections(self.screen)

        elif (self.state == State.MENU): 
            self.mMenu.display(self.screen)
        
        elif(self.state == State.EDITOR):
            self.editor.display(self.screen)


        pygame.display.flip()

    def run(self):
        while self.running:

            self.update()
            self.display()
            self.clock.tick(60) 

        pygame.quit()
        sys.exit()

    def getAddressMask(self, x):
        addr_mask, port = x.split(":")
        address = addr_mask.split("/")[0]
        return address, int(port)

    def synchroData(self, i):
        print("Synchro")

        dicts = [_.to_dict() for _ in self.cells]

        dicts2 = [_.to_dict() for _ in self.connections]

        data = dicts, dicts2

        self.inter.dataToSend()
        self.inter.makeDataToSend(data)

    def loadSynchro(self, data, config):
        data = ast.literal_eval(data)

        self.cells.clear()
        self.connections.clear()

        i = j = 0
        for inner_list in data:
            if i == 0:
                self.cells = [Cell(item["x"],item["y"], item["power"], item["alignment"], item["subCells"], config, item["type"] ) for item in inner_list]
            else:
                self.connections = [Connection(item["firstCell"], item["secondCell"], item["x2"], item["y2"]) for item in inner_list]
                for item in inner_list:
                    for bullet in item["bullets"]:
                        self.connections[j].newBullet(bullet["hp"], bullet["dmg"], bullet["align"], bullet["origin"], bullet["target"], bullet["ox"], bullet["oy"], bullet["tx"], bullet["ty"], bullet["x"], bullet["y"], bullet["dx"], bullet["dy"])
                    j += 1

            i += 1

    def save(self):

        dicts = [_.to_dict() for _ in self.cells]

        dicts2 = [_.to_dict() for _ in self.connections]

        data = dicts, dicts2 

        with open("save.json", "w", encoding="utf-8") as file:
            json.dump(data, file, indent = 4, ensure_ascii= False)

    def saveXML(self):
        root = ET.Element("Root")

        for _ in self.cells:
            group = ET.SubElement(root, "cell")
            ET.SubElement(group, "x").text = str(_.x)
            ET.SubElement(group, "y").text = str(_.y)
            ET.SubElement(group, "power").text = str(_.power)
            ET.SubElement(group, "alignment").text = str(_.alignment)
            ET.SubElement(group, "subCells").text = str(_.subCells)
            ET.SubElement(group, "active").text = str(_.active)
            ET.SubElement(group, "maxPowe").text = str(_.maxPower)
            ET.SubElement(group, "connNumber").text = str(_.connNumber)
            ET.SubElement(group, "type").text = str(_.type)

        for _ in self.connections:
            group = ET.SubElement(root, "connection")
            ET.SubElement(group, "firstCell").text = str(_.firstCell)
            ET.SubElement(group, "secondCell").text = str(_.secondCell)
            ET.SubElement(group, "x2").text = str(_.x2)
            ET.SubElement(group, "y2").text = str(_.y2)
            ET.SubElement(group, "both").text = str(_.both)
            ET.SubElement(group, "active").text = str(_.active)
            for bul in _.bullets:
                bul1 = ET.SubElement(group, "bullet")
                ET.SubElement(bul1, "hp").text = str(bul.hp)
                ET.SubElement(bul1, "dmg").text = str(bul.dmg)
                ET.SubElement(bul1, "align").text = str(bul.align)
                ET.SubElement(bul1, "origin").text = str(bul.origin)
                ET.SubElement(bul1, "target").text = str(bul.target)
                ET.SubElement(bul1, "ox").text = str(bul.ox)
                ET.SubElement(bul1, "oy").text = str(bul.oy)
                ET.SubElement(bul1, "tx").text = str(bul.tx)
                ET.SubElement(bul1, "ty").text = str(bul.ty)
                ET.SubElement(bul1, "x").text = str(bul.x)
                ET.SubElement(bul1, "y").text = str(bul.y)
                ET.SubElement(bul1, "dx").text = str(bul.dx)
                ET.SubElement(bul1, "dy").text = str(bul.dy)
                

        raw_xml = ET.tostring(root)  
        formatted_xml = parseString(raw_xml).toprettyxml(indent="    ")
        with open("save.xml", "w", encoding="utf-8") as xml_file:
            xml_file.write(formatted_xml)

    def loadLevel(self, filename, config):

        self.cells.clear()
        self.connections.clear()
        with open(filename, "r", encoding= "utf-8") as file:
            data = json.load(file)

            self.cells = [Cell(item["x"],item["y"], item["power"], item["alignment"], item["subCells"], config, item["type"] ) for item in data]

    def loadSave(self, filename, config):
        self.cells.clear()
        self.connections.clear()
        with open(filename, "r", encoding= "utf-8") as file:
            data = json.load(file)

            i = j = 0
            for inner_list in data:
                if i == 0:
                    self.cells = [Cell(item["x"],item["y"], item["power"], item["alignment"], item["subCells"], config, item["type"] ) for item in inner_list]
                else:
                    self.connections = [Connection(item["firstCell"], item["secondCell"], item["x2"], item["y2"]) for item in inner_list]
                    for item in inner_list:
                        for bullet in item["bullets"]:
                            self.connections[j].newBullet(bullet["hp"], bullet["dmg"], bullet["align"], bullet["origin"], bullet["target"], bullet["ox"], bullet["oy"], bullet["tx"], bullet["ty"], bullet["x"], bullet["y"], bullet["dx"], bullet["dy"])
                        j += 1

                i += 1

    def loadSaveXML(self, filename, config):
        self.cells.clear()
        self.connections.clear()
        
        tree = ET.parse(filename)
        root = tree.getroot()

        for cell in root.findall("cell"):
            x = int(cell.find("x").text)
            y = int(cell.find("y").text)
            power = int(cell.find("power").text)
            alignment = int(cell.find("alignment").text)
            subCells = int(cell.find("subCells").text)
            type = int(cell.find("type").text)

            cell1 = Cell(x, y, power, alignment, subCells, config, type)
            self.cells.append(cell1)

        i = 0
        for connection in root.findall("connection"):
            firstCell = int(connection.find("firstCell").text)
            secondCell = int(connection.find("secondCell").text)
            x2 = float(connection.find("x2").text)
            y2 = float(connection.find("y2").text)
            active = bool(connection.find("active").text)
            both = bool(connection.find("both").text)

            conn1 = Connection(firstCell, secondCell, x2, y2)
            self.connections.append(conn1)

            for bullet in connection.findall("bullet"):
                hp = int(bullet.find("hp").text)
                dmg = int(bullet.find("dmg").text)
                align = int(bullet.find("align").text)
                origin = int(bullet.find("origin").text)
                target = int(bullet.find("target").text)
                ox = float(bullet.find("ox").text)
                oy = float(bullet.find("oy").text)
                tx = float(bullet.find("tx").text)
                ty = float(bullet.find("ty").text)
                x = float(bullet.find("x").text)
                y = float(bullet.find("y").text)
                dx = float(bullet.find("dx").text)
                dy = float(bullet.find("dy").text)


                self.connections[i].newBullet(hp, dmg, align, origin, target, ox, oy, tx, ty, x, y, dx, dy)
            i += 1


    def checkLoseWin(self):
        isPlayerCell = False
        isEnemyCell = False
        for _ in self.cells:
            if _.alignment == 0:
                isPlayerCell = True
            else:
                isEnemyCell = True
        if isPlayerCell and not(isEnemyCell): return 1
        elif not(isPlayerCell): return -1
        return 0


    def anyCellClicked(self, pos):
        
        for _ in range (len(self.cells)):
            if(self.cells[_].isClicked(pos)):
                str1 = "Cell "+ str(_) + "clicked"
                if self.gameMode > 0:
                    #self.inter.send(str1)
                    pass
                return _
        return -1
    
    def cellClicked(self, x):
        if x == -1 : 
            self.unactiveCells()

        else:
            if self.isActive:
                self.unactiveCells()
                self.isActive = False
                if (x != self.activeCell and self.connExists(self.activeCell, x) == 0 and self.cells[self.activeCell].connNumber < self.cells[self.activeCell].subCells):

                    if self.connExists(x, self.activeCell):
                        i = self.findConn(x, self.activeCell)
                        self.connections[i].doBoth()
                    else:
                        conn1 = Connection(self.activeCell, x, self.cells[self.activeCell].x, self.cells[self.activeCell].y)
                        self.connections.append(conn1)
                        self.cells[self.activeCell].connPlus()
            else:
                self.isActive = True
                self.cells[x].makeActive()
                self.activeCell = x

    def unactiveCells(self):
        for _ in self.cells:
                _.unActive()
        self.isActive = False

    def checkConsClicked(self, pos):
        for _ in self.connections:
            # if (isInRect(pos[0], pos[1], self.cells[_.firstCell].x, self.cells[_.firstCell].y, self.cells[_.secondCell].x, self.cells[_.secondCell].y, conWidth)):
            #     self.takeCell(0, 1)

            start = [self.cells[_.firstCell].x, self.cells[_.firstCell].y]
            stop = [self.cells[_.secondCell].x, self.cells[_.secondCell].y]
            if (is_click_within_line(start, stop, conWidth, pos)):
                self.deleteConnection(_)

    def updateConns(self):
        for _ in self.connections:
            x1 = self.cells[_.firstCell].x
            y1 = self.cells[_.firstCell].y
            x2 = self.cells[_.secondCell].x
            y2 = self.cells[_.secondCell].y

            alpha = np.arctan((y2-y1)/(x2-x1))

            dx = np.cos(alpha) 
            dy = np.sin(alpha) 

            if x2 < x1:
                dx*=-1
                dy*=-1
                
            _.updateEnd(dx, dy)

            if ( (y2-y1)**2 +(x2-x1)**2 ) < ( (_.y2 - y1)**2 + (_.x2 - x1)**2 ):
                _.setEnd(x2, y2)
                _.makeActive()

    def drawConnections(self, screen):
        
        for _ in self.connections:

            x1 = self.cells[_.firstCell].x
            y1 = self.cells[_.firstCell].y
            # x2 = self.cells[_.secondCell].x
            # y2 = self.cells[_.secondCell].y
            x2 = _.x2
            y2 = _.y2

            pygame.draw.line(screen, (255, 255, 255), (x1, y1), (x2, y2), 5)

            _.displayBullets(screen)

    def connExists(self, first, second):
        for _ in self.connections:
            if (_.firstCell == first and _.secondCell == second): return True
        return False
    
    def findConn(self, first, second):
        for i in range (len(self.connections)):
            if (self.connections[i].firstCell == first and self.connections[i].secondCell == second): return i
    
    def deleteConnection(self, connection):
        self.cells[connection.firstCell].connMinus()

        self.connections.remove(connection)

    def newBullets(self):
        for _ in self.connections:
            if self.cells[_.firstCell].type == 0:
                    hp = 1
                    dmg = 1
            elif self.cells[_.firstCell].type == 1:
                    hp = 2
                    dmg = 1

            if _.active:
                _.newBullet(hp, dmg, self.cells[_.firstCell].alignment, _.firstCell, _.secondCell, self.cells[_.firstCell].x, self.cells[_.firstCell].y, self.cells[_.secondCell].x, self.cells[_.secondCell].y)

            if _.both  and _.active:
               _.newBullet(hp, dmg, self.cells[_.secondCell].alignment, _.secondCell, _.firstCell, self.cells[_.secondCell].x, self.cells[_.secondCell].y, self.cells[_.firstCell].x, self.cells[_.firstCell].y) 

    def updateBullets(self):
        for i in self.connections:
            for j in i.bullets:
                j.update()
                if ( (j.x - j.tx)**2 + (j.y - j.ty)**2 ) ** 0.5 < 20:

                    if (j.align == self.cells[j.target].alignment):
                        self.cells[j.target].heal(j.hp)
                    else : self.cells[j.target].takeDamage(j.dmg)            
                    
                    if self.cells[j.target].power <= 0:
                        self.takeCell(j.target, j.align)

                    i.bullets.remove(j)

    def takeCell(self, cell1, align):
        self.cells[cell1].taken(align)

    def aiUpdate(self):
        distances = []
        toAttack = []
        attackers = []
        wasInside = False
        for _ in range (len(self.cells)):
            if self.cells[_].alignment == 1 and self.cells[_].connNumber < self.cells[_].subCells :
                wasInside = True
                dis, cellToAttack = self.findClosestEnemy(self.cells[_])
                distances.append(dis)
                toAttack.append(cellToAttack)
                attackers.append(_)

        if wasInside:
            best = findSmallestIndex(distances)
            conn1 = Connection(attackers[best], toAttack[best], self.cells[attackers[best]].x, self.cells[attackers[best]].y)
            self.connections.append(conn1)

            self.cells[attackers[best]].connPlus()

                
                
    def findClosestEnemy(self, cell1):
        minDist = 10000
        bestCell = 0
        for _ in range (len(self.cells)):
            if self.cells[_].alignment != cell1.alignment:
                dist = self.distance(cell1,self.cells[_])
                if dist < minDist:
                    minDist = dist
                    bestCell = _
        return minDist, bestCell
                

    def distance(self, cell1, cell2):
        return ( (cell1.x - cell2.x)**2 + (cell1.y - cell2.y)**2 ) ** 0.5

    def underAttack(self, cell1):
        for i  in range  (len(self.cells)):
            if self.cells[i].alignment == 0:
                if self.connExists(i, cell1):
                    return True
        return False
    
    def isHealing(self, cell1):
        for i  in range  (len(self.cells)):
            if self.cells[i].alignment == 1:
                if self.connExists(i, cell1):
                    return True
        return False
    
    def findMin(self, list1):
        found = 0
        min1 = 1000
        for i in range (len(list1)):
            if list1[i] < min1:
                min1 = list1[i]
                found = i
        return found
    
    def findMin2(self, list1):
        found1, found2 = 0, 1
        min1 = 1000
        for i in range (len(list1)):
            if list1[i] < min1:
                min1 = list1[i]
                found2 = found1
                found1 = i
        return found1, found2

    def calcPoints(self):
        for i in range(len(self.cells)):
            if self.cells[i].alignment > 0:
                current_list = []
                for j in range(len(self.cells)):
                    curr_points = 0
                    if j != i:
                        curr_points = self.distance(self.cells[i], self.cells[j])
                        if self.cells[j].alignment == self.cells[i].alignment: curr_points *= ALLY
                        if self.isHealing(j): curr_points *= IS_HEALING
                        if self.underAttack(j): curr_points *= UNDER_ATTACK
                        
                        current_list.append(curr_points)

                # Policzone

                if self.cells[i].subCells == 1:
                    indexMin = self.findMin(current_list)
                    if indexMin >= i: indexMin += 1
                    if not(self.cells[i].selectedContains(indexMin)):
                        if len(self.cells[i].selected) >= self.cells[i].subCells:
                            self.cells[i].connMinus()
                            self.deleteConnection(self.connections[self.findConn(i, self.cells[i].selected[0])])
                            self.cells[i].selected.clear()
                        self.cells[i].addSelected(indexMin)
                        print(self.cells[i].selected)

                        conn1 = Connection(i, indexMin, self.cells[i].x, self.cells[i].y)
                        self.connections.append(conn1)

                        self.cells[i].connPlus()
                
                elif self.cells[i].subCells == 2:
                    indexMin1, indexMin2 = self.findMin2(current_list)
                    if indexMin1 >= i: indexMin1 += 1
                    if indexMin2 >= i: indexMin2 += 1
                    if not(self.cells[i].selectedContains(indexMin1)) and not(self.cells[i].selectedContains(indexMin2)):
                        if len(self.cells[i].selected) >= self.cells[i].subCells:
                            self.cells[i].connMinus()
                            self.cells[i].connMinus()
                            # self.deleteConnection(self.connections[self.findConn(i, self.cells[i].selected[0])])
                            # self.deleteConnection(self.connections[self.findConn(i, self.cells[i].selected[1])])
                        elif len(self.cells[i].selected) == 1:
                            self.cells[i].connMinus()
                            self.deleteConnection(self.connections[self.findConn(i, self.cells[i].selected[0])])
                            self.cells[i].addSelected(indexMin1)
                            self.cells[i].addSelected(indexMin2)

                            conn1 = Connection(i, indexMin1, self.cells[i].x, self.cells[i].y)
                            self.connections.append(conn1)
                            conn1 = Connection(i, indexMin2, self.cells[i].x, self.cells[i].y)
                            self.connections.append(conn1)

                            self.cells[i].connPlus()
                            self.cells[i].connPlus()
                    elif not(self.cells[i].selectedContains(indexMin1)):
                        if len(self.cells[i].selected) >= self.cells[i].subCells:
                            pass
                        elif len(self.cells[i].selected) == 1:
                            self.cells[i].addSelected(indexMin1)
                            conn1 = Connection(i, indexMin1, self.cells[i].x, self.cells[i].y)
                            self.connections.append(conn1)

                    elif not(self.cells[i].selectedContains(indexMin2)):
                        if len(self.cells[i].selected) >= self.cells[i].subCells:
                            pass
                        elif len(self.cells[i].selected) == 1:
                            self.cells[i].addSelected(indexMin2)
                            conn1 = Connection(i, indexMin2, self.cells[i].x, self.cells[i].y)
                            self.connections.append(conn1)





                self.AIPoints.append(current_list)
        # print(self.AIPoints)

    


def isInRect(x, y, X1, Y1, X2, Y2, width):
    a = (Y2 - Y1)/(X2 - X1)
    b = Y2 - a*X2

    b1 = a*X1 + b - X1/a
    b2 = a*X2 + b - X2/a

    if ((y > 1/a * x + b1 )and (y < 1/a * x+b2) and (y < a * x + b + width/2) and (y > a * x + b - width /2) ):
        return True
    return False

def is_click_within_line(start_pos, end_pos, line_width, click_pos):
    x1, y1 = start_pos
    x2, y2 = end_pos
    cx, cy = click_pos

    line_vec = (x2 - x1, y2 - y1)
    line_len = math.hypot(line_vec[0], line_vec[1])
    
    if line_len == 0:
        return math.hypot(cx - x1, cy - y1) <= line_width / 2
    
    line_unit_vec = (line_vec[0] / line_len, line_vec[1] / line_len)
    
    point_vec = (cx - x1, cy - y1)
    
    projection_length = point_vec[0] * line_unit_vec[0] + point_vec[1] * line_unit_vec[1]
    
    if projection_length < 0 or projection_length > line_len:
        return False
    
    proj_point = (x1 + projection_length * line_unit_vec[0],
                  y1 + projection_length * line_unit_vec[1])
    
    dist_to_line = math.hypot(cx - proj_point[0], cy - proj_point[1])
    
    return dist_to_line <= line_width / 2

def findSmallestIndex(x):
    smallest = 1000
    bestIndex = 0
    for _ in range (len(x)):
        if x[_] < smallest:
            smallest = x[_]
            bestIndex = _
    return bestIndex

if __name__ == "__main__":

    game = Game(WIDTH, HEIGHT) 
    game.run()
