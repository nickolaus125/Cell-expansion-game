
import pygame
import numpy as np
import json
import re
import socket
import threading
from _thread import *

WIDTH = 800
HEIGHT = 600

RADIUS = 20

class Menu:
    def __init__(self):
        self.showModeSelect = False

        self.play = pygame.Rect(WIDTH/2 - 150, HEIGHT/2 - 250, 300, 100)
        self.editor = pygame.Rect(WIDTH/2 - 150, HEIGHT/2 - 100, 300, 100)
        self.quit = pygame.Rect(WIDTH/2 - 150, HEIGHT/2 + 50, 300, 100)

        self.single = pygame.Rect(WIDTH/2 - 250, HEIGHT/2 - 50, 100, 100)
        self.local = pygame.Rect(WIDTH/2 - 50 , HEIGHT/2 - 50, 100, 100)
        self.multi = pygame.Rect(WIDTH/2 + 150, HEIGHT/2 - 50, 100, 100)
        self.IpAddress = pygame.Rect(WIDTH/2 - 150, HEIGHT/2 - 200, 300, 100)

        self.ipText = ""

        self.font = pygame.font.Font(None, 50)
        self.font2 = pygame.font.Font(None, 30)  

    def clicked(self, pos):
        if self.showModeSelect:
            if self.single.collidepoint(pos):
                return 1
            elif self.local.collidepoint(pos):
                return 2
            elif self.multi.collidepoint(pos):
                return 3
        else:
            if self.play.collidepoint(pos):
                return 1
            elif self.quit.collidepoint(pos):
                return 2
            elif self.editor.collidepoint(pos):
                return 3
        return 0

    def display(self, screen):
        pygame.draw.rect(screen, (255, 0, 0), self.play)
        pygame.draw.rect(screen, (255, 0, 0), self.editor)
        pygame.draw.rect(screen, (255, 0, 0), self.quit)


        text = self.font.render("Play", True, (255, 255, 255))  
        text_rect = text.get_rect(center=self.play.center)

        text2 = self.font.render("Editor", True, (255, 255, 255))  
        text_rect2 = text2.get_rect(center=self.editor.center)

        text3 = self.font.render("Quit", True, (255, 255, 255))  
        text_rect3 = text2.get_rect(center=self.quit.center)

        screen.blit(text, text_rect)
        screen.blit(text2, text_rect2)
        screen.blit(text3, text_rect3)


        if self.showModeSelect:
            pygame.draw.rect(screen, (0, 255, 0), self.single)
            pygame.draw.rect(screen, (0, 255, 0), self.local)
            pygame.draw.rect(screen, (0, 255, 0), self.multi)
            pygame.draw.rect(screen, (255, 255, 255), self.IpAddress)

            text4 = self.font2.render("Single", True, (255, 255, 255))  
            text_rect4 = text4.get_rect(center=self.single.center)

            text5 = self.font2.render("Local", True, (255, 255, 255))  
            text_rect5 = text5.get_rect(center=self.local.center)

            text6 = self.font2.render("Multi", True, (255, 255, 255))  
            text_rect6 = text6.get_rect(center=self.multi.center)

            textIP = self.font2.render(self.ipText, True, (0, 0, 0))  
            text_rectIP = textIP.get_rect(center=self.IpAddress.center)

            screen.blit(text5, text_rect5)
            screen.blit(text6, text_rect6)
            screen.blit(text4, text_rect4)
            screen.blit(textIP, text_rectIP)


    def addToText(self, x):
        self.ipText += x

    def minusIpString(self):
        self.ipText = self.ipText[:-1]

    def validateMask(self):
        pattern = r"^(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}:\d+$"

        if re.match(pattern, self.ipText):
            try:
                ip_part, port_part = self.ipText.split(":")
                ip, mask = ip_part.split("/")
                port = int(port_part)
                
                octets = list(map(int, ip.split(".")))
                if len(octets) == 4 and all(0 <= octet <= 255 for octet in octets):
                    mask = int(mask)
                    if 0 <= mask <= 32:
                        if 0 <= port <= 65535:
                            self.ipText = "Poprawny adres"
            except ValueError:
                pass
        else:
            self.ipText = "Bledny adres"
        

class Cell:
    def __init__(self, x, y, power, alignment, subCells, config, type = 0):
        self.x = x
        self.y = y
        self.power = power
        self.alignment = alignment
        self.subCells = subCells
        self.config = config
        self.radius = 20
        self.active = False
        self.maxPower = 50
        self.connNumber = 0
        self.type = type
        self.selected = []

    def to_dict(self):
        return {
            "x": self.x,
            "y": self.y ,
            "power": self.power, 
            "alignment": self.alignment, 
            "subCells": self.subCells,  
            "active":self.active,
            "maxPower":self.maxPower, 
            "connNumber": self.connNumber, 
            "type": self.type
        }

    def display(self, screen, radius = 20):

        colorYellow = (0, 255, 255)
        colorGreen = (0, 255, 0)
        colorBlue = (0, 0, 255)
        colorRed = (255, 0, 0)

        finalSize = (40,40)

        if self.type == 0:
            textureGreenPath = self.config['Textures']['cell1']
            textureRedPath = self.config['Textures']['cell2']

        elif self.type == 1:
            textureGreenPath = self.config['Textures']['cell12']
            textureRedPath = self.config['Textures']['cell22']

        textureGreen = pygame.image.load(textureGreenPath)
        textureGreen = pygame.transform.scale(textureGreen, finalSize)

        textureRed = pygame.image.load(textureRedPath)
        textureRed = pygame.transform.scale(textureRed, finalSize)

        if (self.active):
            pygame.draw.circle(screen, colorYellow, (self.x, self.y), radius+2)

        if (self.alignment == 0):
            # pygame.draw.circle(screen, colorGreen, (self.x, self.y), radius)
            screen.blit(textureGreen, (self.x - RADIUS, self.y - RADIUS))
            self.dispMiniCircles(screen, colorGreen)
        else:
            # pygame.draw.circle(screen, colorRed, (self.x, self.y), radius)
            screen.blit(textureRed, (self.x - RADIUS, self.y - RADIUS))
            self.dispMiniCircles(screen, colorRed)

        font = pygame.font.Font(None, radius * 2) 
        text = font.render(str(self.power), True, (255, 255, 255))  
        text_rect = text.get_rect(center=(self.x, self.y))

        screen.blit(text, text_rect)

    def dispMiniCircles(self, screen, color):
        if self.subCells == 1:
           pygame.draw.circle(screen, color, (self.x, self.y- self.radius- 2), 2)
        elif self.subCells == 2:
            pygame.draw.circle(screen, color, (self.x - 10, self.y + self.radius + 2), 2)
            pygame.draw.circle(screen, color, (self.x + 10, self.y + self.radius + 2), 2)

    def addSelected(self, x):
        self.selected.append(x)

    def removeFromSelected(self, x):
        self.selected.remove(x)

    def selectedContains(self, x):
        for _ in self.selected:
            if _ == x: return True
        return False

    def regenerate(self):
        self.power += 1
        if self.power > self.maxPower:
            self.power = self.maxPower
            if self.subCells == 1:
                self.subCells = 2

    def isClicked(self, pos):
        distance = ((self.x - pos[0]) ** 2 + (self.y - pos[1]) ** 2) ** 0.5
        if distance < self.radius: return True
        return False
    
    def unActive(self):
        self.active = False

    def makeActive(self):
        self.active = True

    def takeDamage(self, x):
        self.power -= x

    def heal(self, x):
        self.power += x

    def taken(self, x):
        self.power = 10
        self.alignment = x

    def connPlus(self):
        self.connNumber += 1
    def connMinus(self):
        self.connNumber -= 1

class Level:
    def __init__(self, number):
        pass

class Connection:
    def __init__(self, firstCell, secondCell, x2, y2):
        self.firstCell = firstCell
        self.secondCell = secondCell

        self.x2 = x2
        self.y2 = y2

        self.both = False
        self.active = False

        self.bullets = []

    def to_dict(self):
        return {
            "firstCell": self.firstCell,
            "secondCell": self.secondCell ,
            "x2": self.x2, 
            "y2": self.y2, 
            "both": self.both,  
            "active":self.active,
            "bullets": self.bulletsToDict()
        }
    
    def bulletsToDict(self):
        list1 = []
        for _ in self.bullets:
            bul1 = _.__dict__
            list1.append(bul1)
        return list1

    def updateEnd(self, x, y):
        self.x2 += x
        self.y2 += y

    def setEnd(self, x, y):
        self.x2 = x
        self.y2 = y

    def newBullet(self, hp, dmg, align , origin, target, ox, oy, tx, ty, x = None, y = None, dx = None, dy = None):
        bullet1 = Bullet(hp, dmg, align, origin, target, ox, oy, tx, ty, x , y , dx , dy )
        self.bullets.append(bullet1)

    def displayBullets(self, screen):
        for _ in self.bullets:
            _.display(screen)

    def doBoth(self):
        self.both = True
    def undoBoth(self):
        self.both = False

    def makeActive(self):
        self.active = True

    def unActive(self):
        self.active = False


class Bullet:
    def __init__(self, hp, dmg, align,  origin, target, ox, oy, tx, ty, x = None, y = None, dx = None, dy = None):
        self.hp = hp
        self.dmg = dmg
        self.align = align
        self.origin = origin
        self.target = target
        self.ox = ox
        self.oy = oy
        self.tx = tx
        self.ty = ty

        if x is not None and y is not None:
            self.x = x
            self.y = y
        else:
            self.x = ox
            self.y = oy

        if dx is not None and dy is not None:
            self.dx = dx
            self.dy = dy
        else:

            alpha = np.arctan((ty - oy)/(tx - ox))

            self.dx = np.cos(alpha)
            self.dy = np.sin(alpha)

            if self.tx < self.ox:
                self.dx *= -1
                self.dy *= -1

    # def __init__(self, hp, dmg, align,  origin, target, ox, oy, tx, ty, x, y, dx, dy):
    #     self.hp = hp
    #     self.dmg = dmg
    #     self.align = align
    #     self.origin = origin
    #     self.target = target
    #     self.ox = ox
    #     self.oy = oy
    #     self.tx = tx
    #     self.ty = ty

    #     self.x = x
    #     self.y = y
    #     self.dx = dx
    #     self.dy = dy

    def display(self, screen, radius = 4):

        color1 = (255, 0, 0)
        pygame.draw.circle(screen, color1, (self.x, self.y), radius)

    def update(self):
        self.x += self.dx
        self.y += self.dy

class Editor:
    def __init__(self, config):

        self.anySelected = False
        self.selected = 0
        self.config = config

        self.cells = []
        self.typeOfCells = 0

        self.ally1 = pygame.Rect(WIDTH/2 + 200, HEIGHT/2 + 150, 40, 40)
        self.enemy1 = pygame.Rect(WIDTH/2 + 250, HEIGHT/2 + 150, 40, 40)
        self.delete = pygame.Rect(WIDTH/2 + 300, HEIGHT/2 + 150, 40, 40)
        self.change = pygame.Rect(WIDTH/2 + 150, HEIGHT/2 + 150, 40, 40)

        self.ally1Power = 1
        self.enemy1Power = 1

    def display(self, screen):

        if self.anySelected:
            if self.selected == 0:
                pygame.draw.rect(screen, (255, 255, 255), pygame.Rect(WIDTH/2 + 195, HEIGHT/2 + 145, 50, 50))
            elif self.selected == 1:
                pygame.draw.rect(screen, (255, 255, 255), pygame.Rect(WIDTH/2 + 245, HEIGHT/2 + 145, 50, 50))
            else:
                pygame.draw.rect(screen, (255, 255, 255), pygame.Rect(WIDTH/2 + 295, HEIGHT/2 + 145, 50, 50))

        
        finalSize = (40, 40)


        if self.typeOfCells == 0:
            textureRedPath = self.config['Textures']['cell2']
            textureGreenPath = self.config['Textures']['cell1']
        elif self.typeOfCells == 1:
            textureRedPath = self.config['Textures']['cell22']
            textureGreenPath = self.config['Textures']['cell12']      

        
        textureRed = pygame.image.load(textureRedPath)
        textureRed = pygame.transform.scale(textureRed, finalSize)

        textureGreen = pygame.image.load(textureGreenPath)
        textureGreen = pygame.transform.scale(textureGreen, finalSize)

        textureCanPath = self.config['Textures']['can']
        textureCan = pygame.image.load(textureCanPath)
        textureCan = pygame.transform.scale(textureCan, finalSize)

        pygame.draw.rect(screen, (0, 255, 0), self.ally1)
        pygame.draw.rect(screen, (255, 0, 0), self.enemy1)
        pygame.draw.rect(screen, (0, 0, 255), self.delete)
        pygame.draw.rect(screen, (120, 120, 0), self.change)

        screen.blit(textureRed, self.enemy1)
        screen.blit(textureGreen, self.ally1)
        screen.blit(textureCan, self.delete)

        font = pygame.font.Font(None, 40) 
        text1 = font.render(str(self.ally1Power), True, (255, 255, 255))  
        text_rect1 = text1.get_rect(center = self.ally1.center)

        text2 = font.render(str(self.enemy1Power), True, (255, 255, 255))  
        text_rect2 = text2.get_rect(center = self.enemy1.center)

        screen.blit(text1, text_rect1)
        screen.blit(text2, text_rect2)

        for _ in self.cells:
            _.display(screen)

    def clicked(self, pos):
        if self.ally1.collidepoint(pos):
            self.selected = 0
            self.anySelected = True
        elif self.enemy1.collidepoint(pos):
            self.selected = 1
            self.anySelected = True
        elif self.delete.collidepoint(pos):
            self.selected = 2
            self.anySelected = True
        elif self.change.collidepoint(pos):
            self.changeType()

        else:
            if self.anySelected == True:
                if self.selected != 2:
                    self.newCell(pos, self.typeOfCells)
                else:
                    self.remove(pos)

    def keyPressed(self, key):
        if key == pygame.K_UP:
            if self.selected == 0:
                self.ally1Power += 1
            else:
                self.enemy1Power += 1
        elif key == pygame.K_DOWN:
            if self.selected == 0:
                self.ally1Power -= 1
            else:
                self.enemy1Power -= 1
        elif key == pygame.K_s:
            self.save()

    def changeType(self):
        if self.typeOfCells == 1:
            self.typeOfCells = 0
        else:
            self.typeOfCells += 1

    def newCell(self, pos, type):

        if self.selected == 0:
            cell1 = Cell(pos[0], pos[1], self.ally1Power, 0, 1, self.config, type)
        else:
            cell1 = Cell(pos[0], pos[1], self.enemy1Power, 1, 1, self.config, type)

        self.cells.append(cell1)

    def remove(self, pos):
        for _ in self.cells:
            if ((pos[0] - _.x)**2 + (pos[1] - _.y)**2 )**0.5 < RADIUS:
                self.cells.remove(_)

    def save(self):

        dicts = [_.to_dict() for _ in self.cells]

        with open("level.json", "w", encoding="utf-8") as file:
            json.dump(dicts, file, indent = 4, ensure_ascii= False)

class Inter:

    def __init__(self):
        self.server = "192.168.8.1"
        self.port = 5555
        self.untakenData = False
        self.unsendData = False
        self.x = 0
        self.synchronized = False

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.s.bind((self.server, self.port))
        except socket.error as e:
            str(e)
        self.s.listen(1)
        # print("Waiting for a con")

    def threaded_client(self, conn, x):
        conn.settimeout(0.1)
        while True:
            try:
                if self.synchronized == 0:
                    self.conn.send(str.encode(self.data2))
                    print(self.data2)
                try:
                    data = conn.recv(4096).decode()
                    if data == "Cos":
                        self.synchronize()
                    else:
                        self.data = data
                        self.untakenData = True
                except socket.timeout:
                    pass
                self.x += 1
            except:
                pass

    def serverLoop(self):
        while True:
            self.conn, addr = self.s.accept()
            print("Connected to:", addr)
            x = 0
            start_new_thread(self.threaded_client, (self.conn, x))

    def dataTaken(self):
        self.untakenData = False
    def dataToSend(self):
        self.unsendData = True
    def makeDataToSend(self, data):
        self.data2 = str(data)

    def synchronize(self):
        self.synchronized = True

    def send(self, data):
        try:
            self.conn.send(str.encode(data))
        except socket.error as e:
            print(e)

class Klient:
    def __init__(self, address, port):
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server = address
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.port = port
        self.addr = (self.server, self.port)
        self.data = self.connect()
        self.newData = False
        self.synchronized = False
        self.untakenData = False

        receive_thread = threading.Thread(target=self.receive_data, daemon=True)
        receive_thread.start()
    
    def connect(self):
        try:
            self.client.connect(self.addr)
            return self.client.recv(4096).decode()
        except:
            pass

    def receive_data(self):
        while True:
            try:
                # Blokujące odbieranie danych
                data = self.client.recv(4096).decode()
                self.newData = True
                self.untakenData = True
                if not data:
                    # Serwer mógł zakończyć połączenie
                    break
                self.data = data
            except Exception as e:
                break

    def loop(self):
        while True:
            try:
                data = self.client.recv(4096).decode()
                self.data = data
            except:
                self.data = 0

    def printData(self):
        print(self.data)

    def send(self, data):
        try:
            self.client.send(str.encode(data))
        except socket.error as e:
            print(e)

    def synchronize(self):
        self.synchronized = True

    def dataTaken(self):
        self.untakenData = False