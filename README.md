# Leviathan
A simple, quick, and dirty websocket shell for PowerShell. Utilizes the WebSocket4Net csharp 
library (encoded and embedded). Supports secure web socket connections. 

WebSockets allow for a synchronous communications channel between the client and the server. This is a great side channel for
getting interactive with your target. The flexible frame payload size in the WebSockets RFC allow for passing large amounts of
data over the wire with minimal overhead. 

### Commands
- File upload
- File download
- Native PowerShell commands

TODO:
- Additional encryption
- Mutltithreaded server and multiple, simultaneous client connections
- load and execute powershell scripts from memory. 
