import asyncio
import websockets
import json
import random

from src.player.player import Player
class Server:
    CONNS = set()
    STATE = {"value":0}
    PLAYERS = []
    PLAYER_QUEUE = []
    COLOR = 0

    def __init__(self,port):
        self.port = port
        asyncio.run(self.__startServer())


    async def __startServer(self):
        async with websockets.serve(self.__manageConnections, "localhost", 8081):
            print("--------- Server running in port: "+self.port+" ---------")
            await asyncio.Future() 

    def state_event(self):
        return json.dumps({"type": "state", **self.STATE})
     
    async def __manageConnections(self,websocket,path):
        print("----New connection----")
        try: 
            self.CONNS.add(websocket)
            await websocket.send(json.dumps({"type": "state", "state":"connected"}))
    
            init_msg = await websocket.recv()
            data = json.loads(init_msg)

            await self.createPlayer(data,websocket)

            async for message in websocket: 
                for ply in self.PLAYERS:
                    if ply.connection == websocket:
                        turn_player = self.PLAYERS.pop()
                    
                        if turn_player != ply:
                            self.PLAYERS.append(turn_player)
                            await websocket.send(json.dumps({"type": "error_turn", "state":"Is not your turn"}))
                        else:
                            self.PLAYERS.insert(0,turn_player)
                            print("Message form player: ",ply.username," -> ",message)
                            await self.broadcastPlayers(json.dumps({"type": "state", "state":"message"}))

            
        except websockets.exceptions.ConnectionClosedError:
            self.CONNS.remove(websocket)
            for ply in self.PLAYERS:
                    if ply.connection == websocket:
                        self.PLAYERS.remove(ply)
            print("----Connection closed----")
        
    async def broadcastPlayers(self,message):
        for player in self.PLAYERS:
            await player.sendMessage(message)
        
    async def createPlayer(self,data,websocket):
        if len(self.PLAYERS) < 4:
                # TODO: Select color by dice
                player = Player(len(self.PLAYERS) + 1,data["username"],websocket, self.COLOR)
                self.COLOR+=1
                self.PLAYERS.append(player)
                
                for player in self.PLAYERS:
                    await self.broadcastPlayers(
                        json.dumps({"type": "new player",
                        "player":{
                        "id":player.id,
                        "username":player.username,
                        "color":player.color
                    }}))     
        else:
            await websocket.send(json.dumps({"type": "error", "error message":"No more players available"}))


        
        


