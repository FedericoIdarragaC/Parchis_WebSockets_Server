import asyncio
from json.decoder import JSONDecodeError
import websockets
import json
import random
import threading
import time


from src.player.player import Player
class Server:
    CONNS = set()
    STATE = {"value":0}
    PLAYERS = []
    PLAYERS_QUEUE = []
    COLOR = 0
    STARTED = False
    BLOCKED = False
    TIME_BLOCKED = 0

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
                await websocket.send(json.dumps({"type": "connection state", "message":"Connected"}))
        
                init_msg = await websocket.recv()
                data = json.loads(init_msg)
                await self.createPlayer(data,websocket)
            else:
                await websocket.send(json.dumps({"type": "connection state", "message":"Re-connected"}))

            async for message in websocket: 
                if len(self.PLAYERS) < 2:
                    await websocket.send(json.dumps({"type": "alert", "message":"Not enough players"}))
                else:
                    if self.STARTED:
                        timeSinceBlocked = time.time() - self.TIME_BLOCKED
                        if timeSinceBlocked > 30:
                            self.BLOCKED = False

                        if not self.BLOCKED:
                            await self.gameFlow(websocket,message)
                        else:
                            await websocket.send(json.dumps({"type": "waiting", "message":"Waiting for antoher player message"}))
                    else:
                        await self.startGame(websocket,message)

            
        except (websockets.exceptions.ConnectionClosedError,websockets.exceptions.ConnectionClosedOK):
            self.CONNS.remove(websocket)
            print("----Connection closed----")
            for ply in self.PLAYERS:
                if ply.connection == websocket:
                    self.PLAYERS.remove(ply)
                    print("----Connection closed----")
                    print("Player disconnected: " + ply.username +  " id: ",ply.id)
                    await self.broadcastPlayers(json.dumps({"type": "player disconnected","player":ply.jsonInfo()}))
        
        
        except (KeyError,JSONDecodeError):
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
                    data = json.loads(message)

                    if data["operation"] == 1:
                        await ply.rollTheDice()
                        # Exits pawns from the jail at the start

                        #Moving pawns (Wait for player moves distribution)
                        self.BLOCKED = True
                        self.TIME_BLOCKED = time.time()
                        message2 = await ply.connection.recv()                        
                        data = json.loads(message2)

                        if data["operation"] == 2:
                            result = ply.move_pawns_operation(data)
                            if result:
                                await websocket.send(json.dumps({"type": "moved", "message":"pawns moved"}))
                                await self.PlayersStatusBroadcast()
                            else:
                                await websocket.send(json.dumps({"type": "error", "message":"error moving pawns"}))
                        self.BLOCKED = False
                        
                    #await self.broadcastPlayers(json.dumps({"type": "state", "message":"message"}))

    async def startGame(self,websocket,message):
        for ply in self.PLAYERS:
            if ply.connection == websocket:
                if ply.start_status == False:
                    data = json.loads(message)
                    if data["start_status"] == "true":
                        ply.start_status = True
                        await self.broadcastPlayers(json.dumps({"type": "start accepted", "message":ply.jsonInfo()}))

                        starts_count = 0
                        for pl in self.PLAYERS:
                            if pl.start_status == True:
                                starts_count += 1
                        if starts_count == len(self.PLAYERS):
                            await self.broadcastPlayers(json.dumps({"type": "state", "message":"The game has started"}))
                            print("----Game started----")
                            self.STARTED = True
                            await self.PlayersStatusBroadcast()

    async def PlayersStatusBroadcast(self):
        players_status = []
        for player in self.PLAYERS:
            players_status.append(player.pawnsStatus())
        
        await self.broadcastPlayers(
            json.dumps({"type": "players status",
            "status":players_status
        }))   

    async def broadcastPlayers(self,message):
        for player in self.PLAYERS:
            await player.sendMessage(message)
        
    async def createPlayer(self,data,websocket):
        if len(self.PLAYERS) < 4 and not self.STARTED:
                player = Player(len(self.PLAYERS) + 1,data["username"],websocket, self.COLOR)
                self.COLOR+=1
                self.PLAYERS.insert(0,player)
                
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



        
        


