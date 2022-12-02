#!/bin/bash
python3 2019MT60749_server.py $1 &
sleep 2
echo "Waiting for the server to bind the sockets"
sleep 8
echo "Ready"
python3 2019MT60749_client.py &