
import asyncio
import websockets
class Pawn:
    def __init__(self,id,position):
        self.id = id
        self.position = position

    def getPosition(self):
        return self.position

class Player:
    def __init__(self,id,username,connection,color):
        self.id = id
        self.username = username
        self.connection = connection
        self.color = color

        self.pawns = [Pawn(n,color) for n in range(4)]
         
        print("New player: " + self.username +  " in color: ",self.color)

    def getConnection(self):
        return self.connection

    async def sendMessage(self,message):
        await self.connection.send(message)

    async def reciveMessage(self):
        return await self.connection.recv()
        