# BicingBot - Telegram edition
This project brings to your phone the ultimate Telegram bot for travelling with Bicing in Barcelona.

 You can ask it many things; for example, it can show you the map of Barcelona with the geometric 
 graph (whose nodes are the Bicing stations) with edges between the nodes that are closer than the 
 certain distance you want.

 If you are impatient to know all its functionalities go directly to the 
 [Features & Usage](#features--usage-of-bicingbot) section.
 
 If instead, you're looking to run the actual server &mdash; although we don't know who would want
 to look into the server apart from the authors :wink: :wink: &mdash;, we've written some 
 information in [this section](#notes-on-running-the-server). 

## Getting started

Go to Telegram and open up a conversation with [@BCNBicingBot](https://t.me/BCNBicingBot) 
(you can click the link to do so). To ask the bot to do something, you will have to send it commands
(special keywords starting with `/`) by sending a message like you would to any other user.

No further preparation is needed to interact with the bot.

## Features & Usage of BicingBot

### Commands

[@BCNBicingBot](https://t.me/BCNBicingBot) supports the following commands:

 - /start -- initialize a conversation with the bot.
 
 - /help -- display this help message.
 
 - /graph `<distance>` --  generate a geometric graph of the Bicing stations. Takes a single argument, `<distance>`, the maximum distance between two adjacent nodes, as a non-negative real number.
    
 - /status -- display information on the session's current status (i.e. last fetch time, current graph distance, etc.)
     
 - /nodes -- display the number of nodes.
 
 - /edges -- display the number of edges.
 
 - /components -- display the number of connected components.
 
 - /plotgraph -- send an image with a plot of the current 
    graph on the map.
 
 - /route `<origin> <destination>` -- plot a route between two stations. The two stations are given as two space-separated string arguments, `<origin> <destination>`, indicating the street addresses of each station.
    
 - /reset -- clear any stored data (to start from scratch).
 
 - /authors -- display the authors of the bot.
 
 - /distribute `<bikes> <docks>` -- display the total cost (dist x num. bikes) of transferring bycicles, such that in each station there must be `<bikes>` number of bicicles and `<docks>` number of empty places.  


### Errors

The bot always responds to commands, even if there is an unexpected internal error (except if a 
fatal error occurs in the error-handling code itself).

A distinction is made between usage errors (those caused by an inadequate use of a command by the 
user) and internal (unexpected) errors.

For example, requesting a `/graph` with a non-numerical argument results in a usage error:

Finding an example of an internal error is left as a fun challenge to the user. 
(Hopefully there are none.)


### Example
Standard conversation with BicingBot:
<center><img src='images\exemple1.png' width='300' style="float: left;"></center>
<center><img src='images\exemple2.png' width='300' style="float: center;"></center>
<center><img src='images\exemple3.png' width='300' style="float: right;"></center>

## Notes on running the server

## Project structure

## Authors
