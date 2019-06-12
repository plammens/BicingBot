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

A distinction is made between usage/algorithm errors (those caused by an inadequate use of a command by the user, or by a failure to execute an algorithm due to some condition on its parameters) and internal (unexpected) errors.

For example, requesting a `/graph` with a non-numerical argument results in a usage error:

<center><img src='images\error1.png' width='400' style="float: left;"></center>

Finding an example of an internal error is left as a fun challenge to the user (hoping they can't find any). 


### Example
Standard conversation with BicingBot:


| 1/3                                                          | 2/3                                                          | 3/3                                                          |
| ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |
| <center><img src='images\exemple1.png' width='300' style="float: left;"></center> | <center><img src='images\exemple2.png' width='300' style="float: left;"></center> | <center><img src='images\exemple3.png' width='300' style="float: right;"></center> |

## Notes on running the server

These are instructions to run the telegram bot's "server-side" &mdash; namely, the `bot.py` script. The server can be run with `Python 3.6` or higher.

To start, clone this git repository. We'll assume henceforth that all commands are executed in this repository's root directory. Before proceeding, we recommend installing a [`virtualenv`](<https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/#creating-a-virtual-environment>) to avoid interfering with your global Python interpreter's packages. Once you've created and activate your virtual environment, execute

```bash
pip install -r requirements.txt
```

which will install all of the required dependencies listed in the file `requirements.txt`.

### A note on dependencies

The main dependencies for this project are [`networkx`](https://github.com/networkx/networkx), [`haversine`](https://github.com/mapado/haversine), [`staticmap`](https://github.com/komoot/staticmap), [`geopy`](https://github.com/geopy/geopy) , [`pandas`](https://github.com/pandas/pandas) and [`python-telegram-bot`](https://github.com/python-telegram-bot/python-telegram-bot). Some of the other dependencies listed in `requirements.txt` are just to ensure that the combination of the versions of each package works correctly, while the rest are already indirectly included by the aforementioned packages, but we added them anyway for good measure since they're used for type annotations.

Another very important point to note is that **we are using version `12.0.0b1` of `python-telegram-bot`**, which is a beta-version that is nonetheless sufficiently stable. This is why it is important to install the dependencies through `requirements.txt` (to install this specific version, which has [major changes](<https://github.com/python-telegram-bot/python-telegram-bot/wiki/Transition-guide-to-Version-12.0>)), and in a virtual environment so your previously installed release of `python-telegram-bot` doesn't get modified!



### Token

To run the server on an actual Telegram bot, you will need one more ingredient: an API token, which you can get from the [`@BotFather`](https://t.me/botfather). Save it in a file called `token.txt` in the root directory.



### Running `bot.py`

Once you've installed all dependencies and you're ready to go, start the server by executing

```bash
python3 bot.py
```

. This will start the server and will log information and error messages to `stderr`. The first log you should see is the "bot online" message:

```text
2019-06-12 18:15:50,143 - root - INFO - bot online
```

To diagnose and debug errors, you can run the server in debug mode by passing the optional argument `--logging-level` at the command line:

```bash
python3 bot.py --logging-level debug
```

(run `python3 bot.py --help` for more information on command-line arguments).



## Project structure

There are only two python modules, which are at the root of the repository (not forming a package): `bot.py` and `data.py`. The latter handles all of the business-logic, and the former is an interface to the latter in the form of a telegram bot.

The `text` folder contains text files used by the bot, and the `images` folder contains images for this documentation file (`README.md`).

## Authors
The authors of this project are:

 - [Aleix Torres Camps](https://github.com/AlferesChronos)  \<aleix.torres.camps [at] est.fib.upc.edu\>
 - [Paolo Lammens](https://github.com/plammens)  \<paolo.matias.lammens [at] est.fib.upc.edu\>
