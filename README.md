![Logo](/Utilities/Screenshots/Logo_new.png)

A fully custom Fire Emblem fangame created entirely in Python.

Fire Emblem: The Lion Throne is a custom Fire Emblem fangame. Much of the inspiration for the game was drawn from the GBA and Tellius games. 

Because this was coded entirely from scratch, we are not bound by the limitations of the GBA. 

The Lion Throne has innovative objectives, powerful new items, custom classes, a fully functioning skill system with activated skills, a Tellius-style base menu, and much more!

Visit the Discord server for more information and help: https://discord.gg/gpjcYHe

# Downloads
release v0.9.4.4 - 64-bit Windows only

*Dropbox:* https://www.dropbox.com/s/1ikh26td9d68z5n/the_lion_throne.zip?dl=0

#### To play:
Un-zip the downloaded files, and then double-click *lion_throne.exe*

### Screenshots
![TitleScreen](/Utilities/Screenshots/TitleScreen3.png) 
![Range](/Utilities/Screenshots/AOE2.gif)
![Skill](/Utilities/Screenshots/OphieSkill.gif)
![Prep](/Utilities/Screenshots/TheoSearch.gif)
![Conversation](/Utilities/Screenshots/Conversation1.png) 
![Convoy](/Utilities/Screenshots/Convoy1.png)
![Item](/Utilities/Screenshots/Item1.png) 
![Aura](/Utilities/Screenshots/Aura2.png)
![Base](/Utilities/Screenshots/Base2.png)

# Lex Talionis

Lex Talionis is the custom Fire Emblem engine that runs The Lion Throne. If you've wanted to make your own Fire Emblem fangame but were fed up with the hackery that's required to master ROM-hacking, or you just want to work with total control over the code itself, Lex Talionis is for you. 

Not interested in coding? That's fine -- you can create a whole new game with touching any code. 

There is a simple [Tutorial](https://gitlab.com/rainlash/lex-talionis/wikis/home) here, which will teach you how to get started today, without having to learn how to code! 

But if you have Python experience or want to do something I did not expect, the code is entirely open-source and can be changed to meet your needs.

Both the engine and the game are still in Alpha, so there may (and probably are) bugs in the code. Tread carefully.

### More Screenshots
![InfoMenu](/Utilities/Screenshots/InfoMenu2.png)
![Level5](/Utilities/Screenshots/Level5_2.png)
![TransitionScreen](/Utilities/Screenshots/TransitionScreen2.png)
![Combat](/Utilities/Screenshots/Combat1.png)
![Trade](/Utilities/Screenshots/Trade1.png)
![AOE](/Utilities/Screenshots/Range1.png)

## Default Controls:

 - Arrow keys move the cursor.  
 - {X} is the 'A' button. Go forward.  
 - {Z} is the 'B' button. Go backward.  
 - {C} is the 'R' button. It gives the player additional info.  
 - {S} is the 'Start' button.  
 - {A} is the 'L' button.  

These defaults can be changed within the game.

## Getting Started

If you don't want to go through the hassle of running this with Python + Pygame, download the executable above instead.

However, if you are familiar with Python, Pygame, and Git, read on to find out how to get a fully customizable version of this on your machine.

### Prerequisites

You can always run the engine without downloading any addiitonal tools using the executable above instead. However, if you are **SURE** you want to run the Python version of the engine (maybe in order to do modifications of your own?), you will need to download and install the following:

* [Python 3.7.x+](https://www.python.org/downloads/release/python-378/) - As of August 2019, Python 2.x will no longer work. If you want to build the engine into an executable using Pyinstaller, use Python 3.7, not Python 3.8+, since they are not supported by Pyinstaller.
* [Pygame 1.9.6](http://www.pygame.org/download.shtml) - The framework used to handle rendering and sound. If you have pip (which makes things a lot easier for the future), you should try installing it with pip first: `pip install pygame==1.9.6`. Check this link out for more information: https://www.pygame.org/wiki/GettingStarted.

### Installing

You can find more detailed instructions on installing Git, Python, Pygame, and other tools here: https://gitlab.com/rainlash/lex-talionis/-/wikis/102.-Installations. If this is your first time installing any of these tools, I highly recommend you follow the instruction in the _102.-Installations_ link above.

Otherwse, to get the Lex Talionis engine code on your machine easily, in the command line or a terminal, type:

```
git clone https://gitlab.com/rainlash/lex-talionis
```

You will also need to download the audio files, which are not stored on Git because of their size. 

On Dropbox here: https://www.dropbox.com/sh/slbz2t7v1fc6uao/AACiznGLm442qcdOAGbQtnmwa?dl=1.

Once the audio files are downloaded, extract the zip file and move or copy the Audio folder to the lex-talionis directory (the directory that contains main.py).

Once Lex Talionis has been cloned to your machine, from that same directory, you can run The Lion Throne by typing:

```
python main.py
```

A small screen should pop up on your computer, displaying the logo. Don't worry if it takes a couple of minutes the first time it is run. It is just taking the time to turn the code text into compiled bytecode.

## Building/Freezing the Code

In order to build the engine, you will require Python 3.7 (not Python 3.8) and PyInstaller. Python 3.8 can't be used because PyInstaller does not support it yet.

```
pyinstaller main.spec
```

to build. The folder `dist/the_lion_throne` will contain the built executable and its supporting files. Visit https://gitlab.com/rainlash/lex-talionis/-/wikis/100.-Miscellaneous-Stuff#changing-the-name-of-the-executable to see what names can and can't be changed.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
