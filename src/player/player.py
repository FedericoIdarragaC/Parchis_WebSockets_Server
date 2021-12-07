import asyncio
import json
import websockets
import random

class Pawn:
    def __init__(self,id,position):
        self.id = id
        self.init_position = position
        self.position = position

        self.injail = True

    def move(self,mov):
        self.position += mov

    def go_to_jail(self):
        self.position = self.init_position
        self.injail = True

class Player():
    def __init__(self,id,username,connection,color):
        self.id = id
        self.username = username
        self.connection = connection
        self.color = color
        self.start_status = False

        self.init_jail = True
        self.escape_jail_attempts = 0

        self.dice = [0,0]
        #5+17*(id-1)
        self.pawns = [Pawn(n,id+4) for n in range(4)]
         
        print("New player: " + self.username +  " in color: ",self.color)

    def move_pawns_operation(self,data):
        p1 = data["pawn_1"] 
        p2 = data["pawn_2"] 

        res1 = self.movePawn(p1,0)
        res2 = self.movePawn(p2,1)

        
        return res1,res2
        

    def movePawn(self,pawnId,movId):
        pawn = self.pawns[pawnId]
        mov = self.dice[movId]
        
        if mov == 0:
            print("mov = 0")
            return False
        if pawn.injail:
            print("pawn in jail")
            return False
        if self.dice == [0,0]:
            print("dice = 0")
            return False
        
        pawn.move(mov)
        self.pawns[pawnId] = pawn
        self.dice[movId] = 0
        return True

    def validateSendToJail(self,pawnMovedId,players):
        pwn_to_jail = None
        pwn_ply = None

        pawnMoved = self.pawns[pawnMovedId]
        for ply in players:
            for pwn in ply.pawns:
                if pawnMoved.position == pwn.position:
                    pwn.go_to_jail()

                    pwn_to_jail = pwn
                    pwn_ply = ply
                    return pwn_to_jail,pwn_ply

        return False,False

    async def rollTheDice(self, define_pos = False, pos_defined = False):
        self.dice = [random.randint(1,6),random.randint(1,6)]
        await self.sendMessage(json.dumps({"type": "dice result", "message":self.dice}))

        if self.dice[0] == self.dice[1]:
            # Exits pawns from the jail at the start
            if self.init_jail and not define_pos:
                self.init_jail = False
                for p in self.pawns:
                    p.injail = False
                await self.sendMessage(json.dumps({"type": "exit jail", "message":"Your pawns have exit jail"}))
                return False, True
            else:
                if pos_defined:
                    for p in self.pawns:
                        if p.injail:
                            await self.sendMessage(json.dumps({"type": "exit jail", "message":"pawn: "+str(p.id)}))
                            p.injail = False
                return True, False
        elif self.init_jail == True and not define_pos:
            if self.escape_jail_attempts < 2:
                self.escape_jail_attempts += 1
                return True, False        
            else:
                self.escape_jail_attempts = 0
                return False, False

        return False, False
            

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

    def allPawnsInJail(self):
        p_count = 0
        for pw in self.pawns:
            if pw.injail == True:
                p_count += 1

        if p_count == len(self.pawns):
            return True
        else:
            return False