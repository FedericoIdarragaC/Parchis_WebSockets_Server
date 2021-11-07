# Parchis WebSockets Server 
### Federico Idarraga Cardenas
---
## Startup connection

Response:
``` 
{"type": "state", "state": "connected"}
```

## Create player
Message:
```
{
    "username":"test"
}
```
Response (Broadcast for each player connected):
```
{
    "type": "new player", "player": {
        "id": 1,
        "username": "test",
        "color": 1
    }
}
```