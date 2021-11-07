import asyncio
import websockets
import json
import random
import threading

from src.player.player import Player
class Server:
    CONNS = set()
    STATE = {"value":0}
    PLAYERS = []
    PLAYERS_QUEUE = []
    COLOR = 0
    STARTED = False

    def __init__(self,port):
        self.port = port
        asyncio.run(self.__startServer())


    async def __startServer(self):
        async with websockets.serve(self.__manageConnections, "localhost", 8081):
            print("--------- Server running in port: "+self.port+" ---------")
            await asyncio.Future() 

    def state_event(self):
        return json.dumps({"type": "state", **self.STATE})
     
    async def __manageConnections(self,websocket,path,new=True):
        print("----New connection----")
        try: 
            self.CONNS.add(websocket)
            if new:
                await websocket.send(json.dumps({"type": "state", "message":"Connected"}))
        
                init_msg = await websocket.recv()
                data = json.loads(init_msg)
                await self.createPlayer(data,websocket)
            else:
                await websocket.send(json.dumps({"type": "state", "message":"Re-connected"}))

            async for message in websocket: 
                if len(self.PLAYERS) < 2:
                    await websocket.send(json.dumps({"type": "alert", "message":"Not enough players"}))
                else:
                    if self.STARTED:
                        await self.gameFlow(websocket,message)
                    else:
                        await self.startGame(websocket,message)

            
        except websockets.exceptions.ConnectionClosedError:
            self.CONNS.remove(websocket)
            for ply in self.PLAYERS:
                if ply.connection == websocket:
                    self.PLAYERS.remove(ply)
            print("----Connection closed----")
        
        except KeyError:    
            await websocket.send(json.dumps({"type": "error", "message":"Bad request"}))
            await self.__manageConnections(websocket,path,False)
        
    async def gameFlow(self,websocket,message):
        for ply in self.PLAYERS:
            if ply.connection == websocket:
                turn_player = self.PLAYERS.pop()
                if turn_player != ply:
                    self.PLAYERS.append(turn_player)
                    await websocket.send(json.dumps({"type": "alert", "message":"Is not your turn"}))
                else:
                    self.PLAYERS.insert(0,turn_player)
                    print("Message form player: ",ply.username," -> ",message)
                    await self.broadcastPlayers(json.dumps({"type": "state", "message":"message"}))

    async def startGame(self,websocket,message):
        for ply in self.PLAYERS:
            if ply.connection == websocket:
                if ply.start_status == False:
                    data = json.loads(message)
                    if data["start_status"] == "true":
                        ply.start_status = True
                        await self.broadcastPlayers(json.dumps({"type": "state", "message":'Player {} accepted to start the game'.format(ply.username)}))

                        starts_count = 0
                        for pl in self.PLAYERS:
                            if pl.start_status == True:
                                starts_count += 1
                        if starts_count == len(self.PLAYERS):
                            await self.broadcastPlayers(json.dumps({"type": "state", "message":"The game has started"}))
                            self.STARTED = True

    async def broadcastPlayers(self,message):
        for player in self.PLAYERS:
            await player.sendMessage(message)
        
    async def createPlayer(self,data,websocket):
        if len(self.PLAYERS) < 4 and not self.STARTED:
                player = Player(len(self.PLAYERS) + 1,data["username"],websocket, self.COLOR)
                self.COLOR+=1
                self.PLAYERS.append(player)
                
                players_json = []
                for player in self.PLAYERS:
                    players_json.append(player.jsonInfo())

                await self.broadcastPlayers(
                    json.dumps({"type": "new player",
                    "players":players_json
                }))     
        else:
            await websocket.send(json.dumps({"type": "error", "message":"No more players available"}))
            await websocket.close()
            self.CONNS.remove(websocket)



        
        


