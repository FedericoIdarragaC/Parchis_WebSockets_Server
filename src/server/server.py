import asyncio
import websockets
import json
import random

from src.player.player import Player

class Server:
    CONNS = set()
    PLAYERS = []

    def __init__(self,port):
        self.port = port
        asyncio.run(self.__startServer())


    async def __startServer(self):
        async with websockets.serve(self.__manageConnections, "localhost", 8081):
            print("--------- Server running in port: "+self.port+" ---------")
            await asyncio.Future() 

     
    async def __manageConnections(self,websocket,path):
        print("----New connection----")
        try: 
            self.CONNS.add(websocket)

            await websocket.send(json.dumps({"type": "state", "state":"connected"}))

            init_msg = await websocket.recv()
            data = json.loads(init_msg)

            player = Player(len(self.PLAYERS) + 1,data["username"],websocket, random.randint(0,3))
            #TODO: Select color by dice
            self.PLAYERS.append(player)
            
            print("New player: "+player.username)

            await websocket.send(json.dumps({"player":{
                "id":player.id,
                "username":player.username,
                "color":player.color
            }}))

            async for message in websocket:
                data = json.loads(message)
                print(data)


        finally:
            self.CONNS.remove(websocket)
            self.PLAYERS.remove(player)
            print("----Connection closed----")
            

        
        


