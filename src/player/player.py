import asyncio
import json
import websockets
import random

class Pawn:
    def __init__(self,id,position):
        self.id = id
        self.position = position

        self.injail = True

    def move(self,mov):
        self.position + mov

class Player():
    def __init__(self,id,username,connection,color):
        self.id = id
        self.username = username
        self.connection = connection
        self.color = color
        self.start_status = False

        self.dice = [0,0]

        self.pawns = [Pawn(n+1,5+17*(id-1)) for n in range(4)]
         
        print("New player: " + self.username +  " in color: ",self.color)


    def movePawn(self,pawnId):
        return

    async def rollTheDice(self):
        self.dice = [random.randint(1,6),random.randint(1,6)]
        await self.sendMessage(json.dumps({"type": "dice result", "message":self.dice}))

    def getConnection(self):
        return self.connection

    async def sendMessage(self,message):
        await self.connection.send(message)

    async def receiveMessage(self):
        return await self.connection.recv()

    def jsonInfo(self):
        return {"id":self.id,"username":self.username,"color":self.color}

    def pawnsStatus(self):
        pStatus = []
        for p in self.pawns:
            pStatus.append({"id":p.id,"position":p.position,"in_jail":p.injail})
        
        return {"id":self.id,"username":self.username,"color":self.color,"pawnsStatus":pStatus}

    