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
    PLAYERS = []
    PLAYERS_QUEUE = []
    DICES_START = []
    COLOR = 0
    STARTED = False
    POSITIONS_DEFINED = False
    BLOCKED = False
    TIME_BLOCKED = 0

    def __init__(self,port):
        self.port = port
        asyncio.run(self.__startServer())


    async def __startServer(self):
        async with websockets.serve(self.__manageConnections, "localhost", 8081):
            print("--------- Server running in port: "+self.port+" ---------")
            await asyncio.Future() 
     
    async def __manageConnections(self,websocket,path,new=True):
        print("----New connection----")
        try: 
            self.CONNS.add(websocket)
            if new:
                await websocket.send(json.dumps({"type": "connection state", "message":"Connected"}))
        
                init_msg = await websocket.recv()
                data = json.loads(init_msg)
                if len(data["username"]) > 0:
                    await self.createPlayer(data,websocket)
            else:
                await websocket.send(json.dumps({"type": "connection state", "message":"Re-connected"}))

            async for message in websocket: 
                if len(self.PLAYERS) < 2:
                    await websocket.send(json.dumps({"type": "alert", "message":"Not enough players"}))
                else:
                    if self.STARTED:
                        timeSinceBlocked = time.time() - self.TIME_BLOCKED
                        if timeSinceBlocked > 120:
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
            if len(self.PLAYERS) < 2:
                #TODO: Close connections
                await self.broadcastPlayers(json.dumps({"type": "server re-started"}))
                self.PLAYERS = []
        
        
        except (KeyError,JSONDecodeError):
            for ply in self.PLAYERS:
                if ply.connection == websocket:
                    self.PLAYERS.remove(ply)
                    self.PLAYERS.append(ply)
            await websocket.send(json.dumps({"type": "error", "message":"Bad request"}))
            await self.__manageConnections(websocket,path,False)            
             
    async def gameFlow(self,websocket,message):
        for ply in self.PLAYERS:
            if ply.connection == websocket:
                turn_player = self.PLAYERS[len(self.PLAYERS)-1]
                if turn_player != ply:
                    #self.PLAYERS.append(turn_player)
                    await websocket.send(json.dumps({"type": "alert", "message":"Is not your turn"}))
                else:
                    self.PLAYERS.remove(turn_player)
                    self.PLAYERS.insert(0,turn_player)
                    print("Message form player: ",ply.username," -> ",message)
                    data = json.loads(message)
                    
                    if data["operation"] == 1:

                        if self.POSITIONS_DEFINED:
                            await self.paws_movement(websocket,ply)
                        else:
                            await ply.rollTheDice(define_pos=True)
                            self.DICES_START.append({"player_id":ply.id,"dice_result":ply.dice[0]+ply.dice[1]})
                            if len(self.DICES_START) == len(self.PLAYERS):
                                await self.define_players_order()

                        turn_player = self.PLAYERS[len(self.PLAYERS)-1]
                        await self.broadcastPlayers(json.dumps({"type": "current turn", "message":turn_player.jsonInfo()}))

    async def paws_movement(self,websocket,ply):
        repeat, just_exited_jail = await ply.rollTheDice(define_pos=False,pos_defined = self.POSITIONS_DEFINED)
        #Moving pawns (Wait for player moves distribution)
        if ply.allPawnsInJail():
            await websocket.send(json.dumps({"type": "pawns", "message":"all pawns in jail"}))
        elif not just_exited_jail:
            self.BLOCKED = True
            self.TIME_BLOCKED = time.time()
            message2 = await ply.connection.recv()                        
            data = json.loads(message2)

            if data["operation"] == 2:
                result1,result2 = ply.move_pawns_operation(data)

                players_without_ply = self.PLAYERS.copy()
                players_without_ply.remove(ply)

                if not result1:
                    await websocket.send(json.dumps({"type": "error", "message":"error moving pawn1: "+str(data['pawn_1'])}))
                else:
                    pwn_to_jail,player = ply.validateSendToJail(data['pawn_1'],players_without_ply)
                    if pwn_to_jail:
                        await self.broadcastPlayers(json.dumps({"type": "pawn to jail", "pawn":pwn_to_jail.id, "player":player.jsonInfo()}))
                if not result2:
                    await websocket.send(json.dumps({"type": "error", "message":"error moving pawn2: "+str(data['pawn_2'])}))
                else:
                    pwn_to_jail,player = ply.validateSendToJail(data['pawn_2'],players_without_ply)
                    if pwn_to_jail:
                        await self.broadcastPlayers(json.dumps({"type": "pawn to jail", "pawn":pwn_to_jail.id, "player":player.jsonInfo()}))

                if result1 or result2:
                    await websocket.send(json.dumps({"type": "moved", "message":"pawns moved"}))
                    await self.PlayersStatusBroadcast()
                
            self.BLOCKED = False
        elif just_exited_jail and not repeat:
            await self.PlayersStatusBroadcast()
        if repeat:
            self.PLAYERS.remove(ply)
            self.PLAYERS.append(ply)
            

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
                            turn_player = self.PLAYERS[len(self.PLAYERS)-1]
                            await self.PlayersStatusBroadcast()
                            await self.broadcastPlayers(json.dumps({"type": "current turn", "message":turn_player.jsonInfo()}))

    def get_dice_result(self,dice_start):
        return dice_start.get('dice_result')

    def get_player_by_id(self,id):
        for ply in self.PLAYERS:
            if ply.id == id:
                return ply

    async def define_players_order(self):
        self.DICES_START.sort(key=self.get_dice_result)
        print(self.DICES_START)
        for ds in self.DICES_START:
            self.PLAYERS_QUEUE.append(self.get_player_by_id(ds['player_id']))

        self.PLAYERS = self.PLAYERS_QUEUE  
        await self.broadcastPlayers(json.dumps({"type": "order", "message":"order defined"}))
        self.POSITIONS_DEFINED = True

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



        
        


